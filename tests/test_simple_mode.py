import os, tempfile, unittest
from unittest import mock
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["CUSTOMLAB_SYNC"] = "1"
from PySide6.QtWidgets import QApplication
from customlab.gui import MainWindow
from customlab.paths import get_setting
app = QApplication.instance() or QApplication([])


class SimpleModeTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": self.d.name}); self.p.start()

    def tearDown(self): self.p.stop(); self.d.cleanup()

    def test_simple_by_default_and_toggle(self):
        w = MainWindow(); c = w.custom
        self.assertFalse(w.advanced)
        c.kind.setCurrentIndex(0)
        for k in ("axis", "qual", "prot", "thr"): self.assertTrue(c.rows[k].isHidden(), k)
        for k in ("mode", "depth", "u", "v", "pad", "size", "rot"): self.assertFalse(c.rows[k].isHidden(), k)
        self.assertTrue(c.log.isHidden() and c.b_zone.isHidden())
        self.assertFalse(c.rows["size"].isHidden())
        w.a_adv.setChecked(True)
        self.assertTrue(get_setting("advanced_mode"))
        for k in ("axis", "qual", "prot"): self.assertFalse(c.rows[k].isHidden(), k)
        self.assertFalse(c.b_zone.isHidden())
        w.a_adv.setChecked(False)
        self.assertFalse(get_setting("advanced_mode", True))

    def test_direct_percent_stays_in_simple_mode(self):
        w = MainWindow(); w.select("phoenix_hand"); self.assertFalse(w.advanced); self.assertFalse(w.direct_row.isHidden())

    def test_arrows_move_the_motif(self):
        w = MainWindow(); c = w.custom; u0, v0 = c.u.value(), c.v.value(); c.pad_step.setValue(2.0)
        c.pad.findChildren(type(c.b_all))[1].click()
        self.assertEqual((c.u.value(), c.v.value()), (u0, v0 + 2.0))


if __name__ == "__main__": unittest.main()


class ViewOrientation(unittest.TestCase):
    def test_front_view_uses_the_placement_axes(self):
        import numpy as np
        from customlab import deco
        from customlab.viewer import MeshView
        v = MeshView(); v.set_basis(deco.AXES["+x"]); v.face_front()
        self.assertEqual((v.yaw, v.pitch), (0.0, 0.0)); self.assertTrue(np.allclose(v.basis @ np.array([0, 0, 1.0]), [0, 1, 0]))     # part +z (3rd col) -> view up


class TurnView(unittest.TestCase):
    def test_quarter_turn_keeps_2d_mapping_and_3d_basis_consistent(self):
        import numpy as np
        from PySide6.QtCore import QPointF
        from customlab.placement import PlacementView
        v = PlacementView(); v.resize(300, 200)
        for r in range(4):
            v.rot = r; p = QPointF(120, 40); q = v._loc(p)
            self.assertTrue(0 <= q.x() <= v._vw() and 0 <= q.y() <= v._vh())
        os.environ["CUSTOMLAB_HOME"] = tempfile.mkdtemp()
        w = MainWindow(); c = w.custom; b0 = np.array(c.view_basis()); c.set_view_rot(1); b1 = np.array(c.view_basis())
        self.assertTrue(np.allclose(b1[1], b0[0]) and np.allclose(b1[0], -b0[1]))                  # up = old right (u), right = -old up (v)
        c.set_view_rot(4); self.assertEqual(c.view_rot, 0)


class TurnedControls(unittest.TestCase):
    def test_arrows_spots_and_motif_angle_follow_the_displayed_view(self):
        os.environ["CUSTOMLAB_HOME"] = tempfile.mkdtemp()
        w = MainWindow(); c = w.custom; c.set_view_rot(1)
        c.place(10.0, 10.0); c.nudge(2.0, 0.0)                       # displayed right = part -v when turned once
        self.assertEqual((c.u.value(), c.v.value()), (10.0, 8.0))
        c.nudge(0.0, 3.0); self.assertEqual((c.u.value(), c.v.value()), (13.0, 8.0))      # displayed up = part +u
        c.rot.setValue(0); self.assertEqual(c.spec().rotation_deg, -90.0)                  # upright on screen = -90 in the part frame
        c.rot.setValue(30); c.set_view_rot(0); self.assertEqual(c.spec().rotation_deg, 30.0)
