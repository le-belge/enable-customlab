"""Opening a 3MF as a part (converted to STL, original untouched) and the two export choices of the simple mode."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np

from customlab import bambu3mf
from customlab.meshio import read_3mf, read_stl, stl_from_3mf, write_3mf
from tests.test_multimatiere import cube


def box(tris):
    a = np.asarray(tris, float).reshape(-1, 3); return a.min(0).round(4).tolist(), a.max(0).round(4).tolist()


class Read3mf(unittest.TestCase):
    def test_plain_3mf_objects(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.3mf"; write_3mf(f, [("A", cube(0, 0, 10), 0), ("B", cube(20, 0, 5), 1)], ["#FFFFFF", "#FF0000"])
            objs = read_3mf(f); self.assertEqual(len(objs), 2); self.assertEqual(len(objs[0][1]), 2)
            self.assertEqual(box(objs[1][1]), ([20, 0, 0], [25, 5, 5]))

    def test_bambu_3mf_components_in_other_files_and_build_transform(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "b.3mf"
            bambu3mf.write_bambu_3mf(f, [{"name": "Base", "triangles": cube(-5, -5, 10), "extruder": 1}, {"name": "Motif", "triangles": cube(0, 0, 2), "extruder": 2}], bed=(200.0, 200.0))
            (name, tris), = read_3mf(f); lo, hi = box(tris)
            self.assertEqual(len(tris), 4); self.assertEqual(lo[2], 0.0); self.assertAlmostEqual((lo[0] + hi[0]) / 2, 100.0, places=3)   # centred on the 200 mm bed by the build transform
            plates, _ = bambu3mf.pack([{"name": "P", "parts": [{"name": "p", "triangles": cube(0, 0, 30), "extruder": 1}]},
                                       {"name": "Q", "parts": [{"name": "q", "triangles": cube(0, 0, 20), "extruder": 2}]}], (256.0, 256.0))
            g = Path(d) / "plate.3mf"; bambu3mf.write_bambu_plate(g, plates[0], [("PLA", "#FFFFFF"), ("TPU", "#161616")])
            self.assertEqual([n for n, _ in read_3mf(g)], ["P", "Q"])

    def test_conversion_keeps_the_original_picks_an_object_and_copies_the_licence(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); src = d / "dl" / "sub"; src.mkdir(parents=True); f = src / "hand.3mf"
            write_3mf(f, [("Palm", cube(0, 0, 10), 0), ("Cover", cube(20, 0, 5), 0)], ["#FFFFFF"])
            (d / "dl" / "README.txt").write_text("Kinetic Hand by MatBowtell\n"); (d / "dl" / "LICENSE.txt").write_text("CC BY-NC-SA 4.0\n")
            before = hashlib.sha256(f.read_bytes()).hexdigest()
            out, n = stl_from_3mf(f, d / "imported"); self.assertEqual(n, 2); self.assertEqual(len(read_stl(out)), 4)
            one, _ = stl_from_3mf(f, d / "imported", pick=1); self.assertEqual(box(read_stl(one)), ([20, 0, 0], [25, 5, 5])); self.assertIn("Cover", one.name)
            self.assertTrue((one.parent / "LICENSE.txt").is_file()); self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), before)
            self.assertEqual(stl_from_3mf(f, d / "imported")[0], out)                                                          # same file -> same STL (zones stay attached)

    def test_not_a_3mf_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.3mf"; f.write_bytes(b"not a zip")
            with self.assertRaises(Exception): read_3mf(f)


class Gui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_open_3mf_part_and_simple_mode_export_choices(self):
        from customlab.gui import MainWindow
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": d, "CUSTOMLAB_SYNC": "1"}):
            f = Path(d) / "two.3mf"; write_3mf(f, [("A", cube(0, 0, 10), 0), ("B", cube(20, 0, 5), 0)], ["#FFFFFF"])
            w = MainWindow(); w.select("phoenix_hand"); c = w.custom
            stl = c.part_from_3mf(str(f), ask=False); self.assertTrue(stl and stl.endswith(".stl")); self.assertIn("3MF converti", c.log.toPlainText())
            with mock.patch("PySide6.QtWidgets.QInputDialog.getItem", return_value=("2. B (2 triangles)", True)):
                self.assertEqual(box(read_stl(c.part_from_3mf(str(f)))), ([20, 0, 0], [25, 5, 5]))
            with mock.patch("PySide6.QtWidgets.QInputDialog.getItem", return_value=("", False)): self.assertIsNone(c.part_from_3mf(str(f)))
            with mock.patch.object(c, "load_part") as lp, mock.patch("customlab.placement.QFileDialog.getOpenFileName", return_value=(str(f), "")), \
                    mock.patch("PySide6.QtWidgets.QInputDialog.getItem", return_value=("Tous (fusionnés en une pièce)", True)):
                c.choose_part(); self.assertTrue(str(lp.call_args[0][0]).endswith(".stl"))
            with mock.patch("customlab.placement.QMessageBox.warning") as warn:
                bad = Path(d) / "bad.3mf"; bad.write_bytes(b"x"); self.assertIsNone(c.part_from_3mf(str(bad))); warn.assert_called_once()
            w.go(3); self.assertFalse(w.advanced)
            self.assertFalse(w.b_expall.isHidden()); self.assertFalse(w.b_exp.isHidden())                                        # both choices in simple mode
            self.assertIn("tout", w.b_expall.text()); self.assertIn("seulement", w.b_exp.text())


if __name__ == "__main__":
    unittest.main()
