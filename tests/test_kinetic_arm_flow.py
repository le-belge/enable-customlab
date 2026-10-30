import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from customlab import kinetic_arm as K
    from customlab.gui import MainWindow
    from customlab.meshio import bbox, read_stl
    ROOT = Path(__file__).parent.parent / "sources/kinetic_arm/stl"
    HAVE = (ROOT / "UpArmCov100.STL").is_file() and (ROOT / "PalmRH70.STL").is_file()
except Exception:
    HAVE = False


class PartRules(unittest.TestCase):
    D = {"lower_scale": 70.0, "upper_scale": 77.0, "palm_scale": 70.0, "tensioner_scale": 77.5}

    def test_groups_scales_and_prescaled_files(self):
        i = K.part_info("UpArmCov100.STL", self.D); self.assertEqual((i["group"], i["prescaled"], i["scale_percent"], i["mirror_left"]), ("upper", False, 77.0, False))
        i = K.part_info("TypeB-Forearm100.STL", self.D); self.assertEqual((i["group"], i["scale_percent"]), ("lower", 70.0))
        i = K.part_info("PalmRH70.STL", self.D); self.assertTrue(i["prescaled"] and i["mirror_left"] and "matches" in i["note"])
        i = K.part_info("PalmRH75.STL", self.D); self.assertIn("choose the palm file at 70 %", i["note"])
        i = K.part_info("Tensioners77-5.STL", self.D); self.assertTrue(i["prescaled"] and "matches" in i["note"] and not i["mirror_left"])
        self.assertEqual(K.part_info("FingerPlateRH100.STL", self.D)["mirror_left"], True)
        self.assertEqual(K.part_info("ElbowHinges100.STL", self.D)["group"], "upper")


@unittest.skipUnless(HAVE, "Kinetic Arm STL files not available locally")
class ArmFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")

    def tearDown(self): self.d.cleanup()

    def window(self, side="left"):
        w = MainWindow(); w.select("kinetic_arm"); w.side.setCurrentIndex(w.side.findData(side))
        for k, x in (("hand_mm", 168.7), ("elbow_mm", 70.66), ("resid_mm", 83.32)): w.fields[k].setValue(x)
        return w

    def pick(self, w, name):
        c = w.custom; c.pick_library(next(i for i in range(1, c.lib.count()) if c.lib.itemText(i).startswith(name))); return c

    def test_library_lists_the_arm_parts_with_their_licence(self):
        w = self.window(); w.go(2); c = w.custom; labels = [c.lib.itemData(i, 3) for i in range(1, c.lib.count())]      # Qt.ToolTipRole = 3: the full label with the licence (the visible text is the short name)
        self.assertEqual(len(labels), 111); self.assertTrue(all("CC BY-NC-SA" in l for l in labels)); self.assertTrue(any(l.startswith("UpArmCov100") for l in labels))

    def test_upper_part_scale_and_no_mirror_for_generic_part(self):
        w = self.window("left"); w.go(2); c = self.pick(w, "UpArmCov100")
        self.assertFalse(c.mirror_x); self.assertEqual(bbox(c.tris), bbox(read_stl(ROOT / "UpArmCov100.STL")))
        self.assertEqual(w.scale_percent(), 70.0)                      # Jake: upper scale 70 % (Type B)
        w.fields["hand_mm"].setValue(190); w.fields["elbow_mm"].setValue(98); self.assertEqual(w.sizing.derived["upper_scale"], 96.0); self.assertEqual(w.scale_percent(), 96.0)   # 190 mm -> 80 %, type F

    def test_rh_part_is_mirrored_for_a_left_arm_and_prescaled_is_not_rescaled(self):
        w = self.window("left"); w.go(2); c = self.pick(w, "PalmRH70"); self.assertTrue(c.mirror_x)
        lo, hi = bbox(read_stl(ROOT / "PalmRH70.STL")); mlo, mhi = bbox(c.tris); self.assertAlmostEqual(mlo[0], -hi[0], places=3)
        self.assertIsNone(w.scale_percent()); self.assertIn("matches", w.result_html([]))
        w.go(1); w.side.setCurrentIndex(w.side.findData("right")); w.go(2); self.assertFalse(c.mirror_x)


if __name__ == "__main__":
    unittest.main()
