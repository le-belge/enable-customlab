import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CUSTOMLAB_SYNC"] = "1"; os.environ["CUSTOMLAB_CACHE"] = "1"
from PySide6.QtWidgets import QApplication
from customlab import cache, deco
from customlab.gui import MainWindow

ARM = Path(__file__).parent.parent / "sources/kinetic_arm/stl"
BOX = [((0, 0, 0), (10, 0, 0), (0, 10, 0)), ((10, 0, 0), (10, 10, 0), (0, 10, 0)), ((0, 0, 5), (0, 10, 5), (10, 0, 5)), ((10, 0, 5), (0, 10, 5), (10, 10, 5))]


class DiskCache(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home"); self.f = Path(self.d.name) / "p.stl"; self.f.write_bytes(b"x" * 100)

    def tearDown(self): self.d.cleanup()

    def test_heightmap_and_axis_round_trip(self):
        hm = deco.build_heightmap(BOX, "+z", 0.5); self.assertIsNone(cache.get_hm(self.f, False, "+z", 0.5))
        cache.put_hm(self.f, False, "+z", 0.5, hm); back = cache.get_hm(self.f, False, "+z", 0.5)
        self.assertTrue(np.array_equal(np.isnan(back.H), np.isnan(hm.H)) and np.allclose(back.H[~np.isnan(back.H)], hm.H[~np.isnan(hm.H)]))
        self.assertEqual((back.axis, back.res, back.u0, back.v0), (hm.axis, hm.res, hm.u0, hm.v0))
        self.assertIsNone(cache.get_hm(self.f, True, "+z", 0.5)); self.assertIsNone(cache.get_hm(self.f, False, "+y", 0.5))      # mirroring / axis are part of the key
        cache.put_axis(self.f, False, "-y", {"-y": 3}); self.assertEqual(cache.get_axis(self.f, False)["axis"], "-y")

    def test_a_modified_file_never_hits_an_old_entry(self):
        cache.put_axis(self.f, False, "+x", {}); self.assertIsNotNone(cache.get_axis(self.f, False))
        self.f.write_bytes(b"y" * 101); self.assertIsNone(cache.get_axis(self.f, False))

    def test_disabled_in_synchronous_mode_unless_forced(self):
        old = os.environ.pop("CUSTOMLAB_CACHE")
        try: self.assertFalse(cache.enabled()); os.environ["CUSTOMLAB_CACHE"] = "1"; self.assertTrue(cache.enabled())
        finally: os.environ["CUSTOMLAB_CACHE"] = old


@unittest.skipUnless((ARM / "UpArmCov100.STL").is_file(), "Kinetic Arm STL files not available locally")
class FinalScale(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")

    def tearDown(self): self.d.cleanup()

    def window(self):
        w = MainWindow(); w.select("kinetic_arm")
        for k, x in (("hand_mm", 168.7), ("elbow_mm", 70.66), ("resid_mm", 83.32)): w.fields[k].setValue(x)
        w.go(2); c = w.custom; c.pick_library(next(i for i in range(1, c.lib.count()) if c.lib.itemText(i).startswith("UpArmCov100"))); return w

    def test_override_is_used_and_out_of_range_is_refused_not_corrected(self):
        w = self.window(); self.assertEqual(w.scale_percent(), 70.0); self.assertFalse(w.scale_out_of_range())
        w.scale_override = 60.0; self.assertEqual(w.scale_percent(), 60.0); self.assertFalse(w.scale_out_of_range())
        w.scale_override = 120.0; self.assertEqual(w.scale_percent(), 120.0); self.assertTrue(w.scale_out_of_range())          # not clamped to 100
        w.scale_override = 40.0; self.assertTrue(w.scale_out_of_range())
        w.scale_cb.setChecked(False); self.assertFalse(w.scale_out_of_range())                                            # nothing applied -> nothing to refuse

    def test_custom_page_shows_standard_size_and_final_size(self):
        w = self.window(); w.scale_override = 80.0; w.custom.update_model(); t = w.custom.dims.text()
        self.assertIn("Taille standard (100 %)", t); self.assertIn("taille finale à 80 %", t)
        w.scale_override = None; w.scale_cb.setChecked(False); w.custom.update_model(); self.assertNotIn("finale", w.custom.dims.text())

    def test_scale_row_and_state_round_trip(self):
        w = self.window(); w.scale_override = 85.0; w.refresh_scale_row(); self.assertFalse(w.scale_row.isHidden()); self.assertEqual(w.scale_spin.value(), 85.0)
        self.assertEqual(w.state_dict()["scale_override"], 85.0)
        w.new_project() if hasattr(w, "new_project") else None


if __name__ == "__main__":
    unittest.main()


class DirectScale(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")

    def tearDown(self): self.d.cleanup()

    def test_kinetic_hand_scale_can_be_chosen_without_any_measure(self):
        w = MainWindow(); w.select("kinetic_hand"); self.assertIsNone(w.sizing); self.assertIsNone(w.scale_percent()); self.assertFalse(w.direct_row.isHidden())
        w.direct_spin.setValue(80.0); w._direct_edited(); self.assertEqual(w.scale_percent(), 80.0); self.assertFalse(w.scale_out_of_range()); self.assertEqual(w.scale_for_part("x.stl"), (80.0, None))
        w.direct_spin.setValue(40.0); w._direct_edited(); self.assertTrue(w.scale_out_of_range()); self.assertIn("refusée", w.direct_info.text())     # 50-100 % documented: refused, not clamped
        self.assertEqual(w.scale_percent(), 40.0)
        w.direct_spin.setValue(0.0); w._direct_edited(); self.assertIsNone(w.scale_override); self.assertIsNone(w.scale_percent())

    def test_phoenix_direct_scale_and_arm_has_no_direct_row(self):
        w = MainWindow(); w.select("phoenix_hand"); w.direct_spin.setValue(120.0); w._direct_edited(); self.assertEqual(w.scale_percent(), 120.0); self.assertFalse(w.scale_out_of_range())
        w.direct_spin.setValue(170.0); w._direct_edited(); self.assertTrue(w.scale_out_of_range())
        w.select("kinetic_arm"); self.assertTrue(w.direct_row.isHidden()); self.assertIsNone(w.scale_override)                        # switching device drops the value
        self.assertEqual(w.scale_for_part("PalmRH70.STL")[0], None)

    def test_measures_still_give_the_computed_scale_and_the_direct_value_wins(self):
        w = MainWindow(); w.select("kinetic_hand"); w.recompute()
        w.scale_override = 75.0; w.sync_direct(); self.assertEqual(w.direct_spin.value(), 75.0); self.assertEqual(w.scale_percent(), 75.0)
        w.scale_override = None; w.sync_direct(); self.assertEqual(w.direct_spin.value(), 0.0)
