import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np

try:
    from PySide6.QtWidgets import QApplication
    from customlab import deco, library
    from customlab.gui import MainWindow
    from customlab.meshio import bbox, is_watertight, read_stl, volume
    ROOT = Path(__file__).parent.parent / "sources/kinetic_hand/stl/Kinetic Hand/Individual stls"
    PART = ROOT / "Gauntlet cover (RH100%).stl"
    HAVE = PART.is_file()
except Exception:
    HAVE = False
from tests.test_deco import STAR


class Mirror(unittest.TestCase):
    def test_mirror_keeps_volume_sign_and_closedness(self):
        from tests.test_deco import slab
        from customlab.meshio import write_stl
        d = tempfile.mkdtemp(); f = Path(d) / "s.stl"; slab(f, w=60, l=40, t=5)
        t = read_stl(f); m = deco.mirror_tris(t)
        self.assertAlmostEqual(volume(m), volume(t), places=6); self.assertGreater(volume(m), 0); self.assertTrue(is_watertight(m))
        (lo, hi), (lo2, hi2) = bbox(t), bbox(m); self.assertAlmostEqual(lo2[0], -hi[0]); self.assertAlmostEqual(hi2[0], -lo[0]); self.assertEqual((lo2[1], hi2[1]), (lo[1], hi[1]))


@unittest.skipUnless(HAVE, "official Kinetic Hand STL not available locally")
class KineticFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")

    def tearDown(self): self.d.cleanup()

    def window(self, side="left", wrist=48.0, palm=40.0):
        w = MainWindow(); w.select("kinetic_hand"); w.side.setCurrentIndex(w.side.findData(side))
        w.fields["wrist_mm"].setValue(wrist); w.fields["palm_mm"].setValue(palm); w.recompute(); return w

    def test_measures_page_shows_the_manual_result(self):
        w = self.window(); txt = w.live.toPlainText()
        self.assertIn("72.5 %", txt); self.assertIn("Insert souple : D (30 mm)", txt); self.assertIn("symétrie en X", txt); self.assertIn("paume d'essai", txt)
        self.assertIsNotNone(w.sizing); self.assertEqual(w.sizing.derived["insert"], "D"); self.assertFalse(w.part.isVisibleTo(w) and w.part.count() > 0)

    def test_out_of_chart_wrist_is_refused(self):
        w = self.window(wrist=90.0); self.assertIsNone(w.sizing); self.assertIn("hors du tableau", w.live.toPlainText())

    def test_library_lists_only_kinetic_parts_for_this_device(self):
        w = self.window(); w.go(2); c = w.custom; labels = [c.lib.itemData(i, 3) for i in range(1, c.lib.count())]      # Qt.ToolTipRole = 3: the full label with the licence (the visible text is the short name)
        self.assertGreater(len(labels), 30); self.assertTrue(all("RH" in l or "LH" in l for l in labels)); self.assertTrue(any(l.startswith("Gauntlet cover") for l in labels))
        self.assertFalse(any("Grouped" in l or "fitment" in l.lower() for l in labels)); self.assertTrue(all("Share Alike" in l for l in labels))
        w.select("phoenix_hand"); self.assertEqual(w.custom.lib.count(), 17)                      # the Phoenix list is unchanged

    def pick(self, w, name="Gauntlet cover"):
        c = w.custom; c.pick_library(next(i for i in range(1, c.lib.count()) if c.lib.itemText(i).startswith(name))); return c

    def test_left_hand_part_is_mirrored_scaled_and_licensed(self):
        w = self.window("left"); w.go(2); c = self.pick(w); self.assertTrue(c.mirror_x); self.assertIn("Share Alike", c.prov.text())
        orig = read_stl(PART); lo, hi = bbox(orig); mlo, mhi = bbox(c.tris); self.assertAlmostEqual(mlo[0], -hi[0], places=3); self.assertAlmostEqual(mhi[0], -lo[0], places=3)
        self.assertIn(c.axis.currentData(), ("+y", "-y"))                  # the flat faces of this part are along y: chosen automatically
        c.kind.setCurrentIndex(c.kind.findData("svg")); c.svg_path = str(STAR); c.size.setValue(14); c.depth.setValue(1.0); c.mode.setCurrentIndex(c.mode.findData("inlay")); c.qual.setCurrentIndex(c.qual.findData(0.25))
        ok = np.argwhere(~np.isnan(c.hm.H)); mid = ok.mean(0); c.place(c.hm.u0 + mid[0] * c.hm.res, c.hm.v0 + mid[1] * c.hm.res)
        placed = None
        for iu in range(0, c.hm.shape[0], 12):                       # the real part has holes and steep rims: scan for a free spot
            for jv in range(0, c.hm.shape[1], 12):
                if np.isnan(c.hm.H[iu, jv]): continue
                c.place(c.hm.u0 + iu * c.hm.res, c.hm.v0 + jv * c.hm.res)
                if not c.errors: placed = (iu, jv); break
            if placed: break
        self.assertIsNotNone(placed, c.errors)
        w.go(3); self.assertIsNotNone(w.out_tris); self.assertTrue(w.scale_cb.isVisibleTo(w))
        out = w.export_to(Path(self.d.name) / "out"); meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(meta["scale_percent_applied"], 72.5); self.assertTrue(meta["spec"]["mirror_x"]); self.assertEqual(meta["device"], "kinetic_hand")
        self.assertTrue(meta["source_license"]["share_alike"]); self.assertTrue(meta["source_license"]["non_commercial"]); self.assertEqual(meta["source_license"]["author"], "MatBowtell")
        import zipfile, re
        z = zipfile.ZipFile(next(out.parent.glob("*_Bambu_pret.3mf"))); xs = [float(x) for x in re.findall(r' x="([-\d.]+)"', z.read("3D/Objects/object_1.model").decode())]
        self.assertAlmostEqual(max(xs), -lo[0] * 0.725, delta=0.05); self.assertAlmostEqual(min(xs), -hi[0] * 0.725, delta=0.05)          # mirrored THEN scaled, base part in the 3MF
        self.assertIn("PARTAGE DANS LES MÊMES CONDITIONS", next(out.parent.glob("*_ATTRIBUTION.txt")).read_text(encoding="utf-8"))

    def test_right_hand_part_is_not_mirrored(self):
        w = self.window("right"); w.go(2); c = self.pick(w); self.assertFalse(c.mirror_x)
        self.assertEqual(bbox(c.tris), bbox(read_stl(PART)))

    def test_switching_side_reloads_the_part_mirrored(self):
        w = self.window("right"); w.go(2); c = self.pick(w); x_right = bbox(c.tris)[1][0]
        w.go(1); w.side.setCurrentIndex(w.side.findData("left")); w.go(2); self.assertTrue(c.mirror_x); self.assertAlmostEqual(bbox(c.tris)[0][0], -x_right, places=3)

    def test_project_roundtrip_keeps_mirror_and_measures(self):
        w = self.window("left"); w.go(2); self.pick(w); out = w.save_project(Path(self.d.name) / "kin")
        w2 = MainWindow(); self.assertEqual(w2.open_project(out), []); self.assertEqual(w2.dev, "kinetic_hand"); self.assertTrue(w2.custom.mirror_x)
        self.assertEqual(w2.fields["wrist_mm"].value(), 48.0); self.assertEqual(w2.sizing.derived["insert"], "D")

    def test_command_line_preset_opens_the_kinetic_hand_ready_to_export(self):
        import argparse
        from customlab.gui import preset_kinetic
        w = MainWindow(); a = argparse.Namespace(side="left", wrist=48.0, palm=40.0, kin_part="Gauntlet cover", logo=str(STAR), size=14.0, depth=1.0, colors=1, mode="inlay", res=0.25, u=0.0, v=0.0)
        preset_kinetic(w, a); self.assertEqual((w.dev, w.stack.currentIndex()), ("kinetic_hand", 2)); self.assertTrue(w.custom.mirror_x); self.assertEqual(w.custom.errors, [])
        self.assertEqual(w.sizing.derived["scale_percent"], 72.5)


if __name__ == "__main__":
    unittest.main()
