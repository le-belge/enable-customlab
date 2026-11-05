"""Face to decorate (buttons, turn over) and the warning for a motif on the face that lies on the print bed."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from customlab import deco, messages
from customlab.meshio import read_stl
from tests.test_deco import slab


class BedFace(unittest.TestCase):
    def test_relief_on_the_bottom_face_is_flagged_not_on_the_top(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.stl"; slab(p)
            for axis, flagged in (("+z", False), ("-z", True)):
                hm = deco.build_heightmap(read_stl(p), axis, 0.5); ok = ~__import__("numpy").isnan(hm.H)
                c = __import__("numpy").argwhere(ok).mean(0); u, v = hm.u0 + c[0] * hm.res, hm.v0 + c[1] * hm.res
                r = deco.apply_decoration(p, deco.DecoSpec(kind="text", text="A", size_mm=15, u=u, v=v, axis=axis, protect_margin_mm=0), hm=hm)
                self.assertEqual(r.errors, []); self.assertEqual(any("plateau" in w for w in r.warnings), flagged, axis)
            self.assertEqual(messages.localize("Motif sur la face posée sur le plateau d'impression (x)", "en")[0], messages.CHECK)


class Buttons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_face_buttons_flip_and_simple_mode(self):
        from customlab.gui import MainWindow
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": d, "CUSTOMLAB_SYNC": "1"}):
            p = Path(d) / "s.stl"; slab(p); w = MainWindow(); w.select("phoenix_hand"); w.load_stl(str(p)); c = w.custom
            self.assertFalse(w.advanced); self.assertFalse(c.face_box.isHidden()); self.assertTrue(c.axis.isHidden())          # buttons in simple mode, raw axis hidden
            c.text.setText("A"); c.face_btns["-z"].click(); self.assertEqual(c.axis.currentData(), "-z"); self.assertTrue(c.face_btns["-z"].isChecked())
            self.assertFalse(c.face_btns["+z"].isChecked()); self.assertTrue(any("plateau" in x for x in c.warns))
            c.flip_face(); self.assertEqual(c.axis.currentData(), "+z"); self.assertFalse(any("plateau" in x for x in c.warns))
            c.face_btns["-y"].click(); self.assertEqual(c.spec().axis, "-y")
            c.axis.setCurrentIndex(c.axis.findData("+x")); self.assertTrue(c.face_btns["+x"].isChecked())                       # advanced combo and buttons stay in sync


if __name__ == "__main__":
    unittest.main()
