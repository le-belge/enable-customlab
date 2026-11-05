"""Advised (green) and forbidden (red) zones: refusal that the user can override, advised-zone warning and auto placement, reference zones."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from customlab import deco
from customlab.meshio import read_stl
from tests.test_deco import slab


class Engine(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.part = Path(self.d.name) / "p.stl"; slab(self.part)
        self.hm = deco.build_heightmap(read_stl(self.part), "+z", 0.25)

    def tearDown(self): self.d.cleanup()

    def spec(self, **k): return deco.DecoSpec(**{**dict(kind="text", text="L", size_mm=10, u=30, v=30, depth_mm=0.6, protect_margin_mm=0), **k})

    def test_old_tuples_are_forbidden_zones_and_kinds_are_separated(self):
        z = [(0, 0, 1, 1), {"kind": "advised", "rect": [2, 2, 3, 3]}, {"kind": "forbidden", "rect": [4, 4, 5, 5]}]
        self.assertEqual(deco.zone_rects(z), [(0, 0, 1, 1), (4, 4, 5, 5)]); self.assertEqual(deco.zone_rects(z, "advised"), [(2, 2, 3, 3)])

    def test_forbidden_zone_refuses_unless_confirmed_and_the_override_is_recorded(self):
        zones = [{"kind": "forbidden", "rect": [25, 25, 35, 35]}]
        r = deco.apply_decoration(self.part, self.spec(), zones, hm=self.hm)
        self.assertTrue(any("zone interdite n°1" in e and "Valider malgré" in e for e in r.errors)); self.assertEqual(r.deco_triangles, [])
        s = self.spec(allow_forbidden_zones=True); r = deco.apply_decoration(self.part, s, zones, hm=self.hm)
        self.assertEqual(r.errors, []); self.assertTrue(any("ZONE INTERDITE n°1" in w and "validé" in w for w in r.warnings)); self.assertTrue(r.deco_triangles)
        out = deco.export_result(r, self.part, s, Path(self.d.name) / "out", zones)
        meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(meta["forbidden_zones_overridden"], [1]); self.assertTrue(meta["spec"]["allow_forbidden_zones"]); self.assertEqual(meta["exclusion_zones_mm"], [[25, 25, 35, 35]])

    def test_override_does_not_lift_the_automatic_protection(self):
        mask = deco.render_mask(self.spec(), self.hm); prot = mask.copy()          # holes/slots protection, simulated under the whole motif
        errors, _, _ = deco.check_placement(self.hm, mask, [], 0.6, "relief", prot, allow_forbidden=True)
        self.assertTrue(any("zone protégée automatiquement" in e for e in errors))

    def test_advised_zone_warning_only_when_the_motif_leaves_it(self):
        inside = [{"kind": "advised", "rect": [10, 10, 50, 50]}]; outside = [{"kind": "advised", "rect": [0, 0, 5, 5]}]
        r = deco.apply_decoration(self.part, self.spec(), inside, hm=self.hm)
        self.assertEqual(r.errors, []); self.assertFalse(any("zones conseillées" in w for w in r.warnings))
        r = deco.apply_decoration(self.part, self.spec(), outside, hm=self.hm)
        self.assertEqual(r.errors, []); self.assertTrue(any("100 % du motif est hors des zones conseillées" in w for w in r.warnings))


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_draw_override_reference_zones_and_auto_placement(self):
        from customlab import placement
        from customlab.gui import MainWindow
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": home}), \
                mock.patch.object(placement, "REF_ZONES", Path(d) / "refs"):
            part = Path(d) / "s" / "p.stl"; part.parent.mkdir(); slab(part)
            w = MainWindow(); w.select("phoenix_hand"); w.set_advanced(True) if hasattr(w, "set_advanced") else None
            w.load_stl(str(part)); c = w.custom; c.text.setText("Léo"); c.place(30, 30)
            c.b_zone_ok.setChecked(True); self.assertEqual(c.view.zone_mode, "advised"); c.b_zone.setChecked(True)
            self.assertEqual(c.view.zone_mode, "forbidden"); self.assertFalse(c.b_zone_ok.isChecked())                   # exclusive buttons
            c.add_zone(20, 20, 40, 40); self.assertTrue(any("zone interdite" in e for e in c.errors))
            c.force.setChecked(True); self.assertEqual(c.errors, []); self.assertTrue(c.spec().allow_forbidden_zones)
            c.force.setChecked(False); c.clear_zones(); c.add_zone(5, 5, 20, 20, kind="advised"); c.add_zone(40, 40, 55, 55, kind="forbidden")
            f = c.save_ref_zones(); self.assertTrue(f and f.is_file()); self.assertEqual(len(json.loads(f.read_text(encoding="utf-8"))["zones"]), 2)
            for g in (Path(home) / "zones").glob("*.json"): g.unlink()                                                      # another computer: no user zones
            w2 = MainWindow(); w2.select("phoenix_hand"); w2.load_stl(str(part)); c2 = w2.custom
            self.assertEqual(c2.zone_source, "ref"); self.assertEqual([z["kind"] for z in c2.zones], ["advised", "forbidden"])
            self.assertAlmostEqual(c2.u.value(), 12.5, delta=0.3); self.assertAlmostEqual(c2.v.value(), 12.5, delta=0.3)      # motif centred in the green zone
            self.assertEqual(placement.zones_for(part, c2.axis.currentData(), False), c2.zones)
            c2.view.grab()


if __name__ == "__main__":
    unittest.main()


class EditZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_resize_by_corner_and_edge_undo_and_margin_in_simple_mode(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from customlab.gui import MainWindow
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": d, "CUSTOMLAB_SYNC": "1"}):
            part = Path(d) / "p.stl"; slab(part); w = MainWindow(); w.select("phoenix_hand"); w.load_stl(str(part)); c = w.custom
            self.assertFalse(c.rows["prot"].isHidden()); self.assertFalse(c.prot.isHidden())                                  # auto margin reachable in simple mode
            w.a_adv.setChecked(True); c.text.setText("A"); c.view.resize(500, 500); c.view.show(); self.app.processEvents()
            c.add_zone(10, 10, 30, 30); c.add_zone(40, 40, 50, 50, kind="advised")
            c.b_zone.setChecked(True); self.assertIn("redimensionner", c.view.hint)
            px = lambda u, v: QPoint(round(c.view._to_px(u, v).x()), round(c.view._to_px(u, v).y()))
            self.assertEqual(c.view.zone_grip(c.view._to_px(30, 30))[0], 0)                                                  # corner of zone 1
            QTest.mousePress(c.view, Qt.LeftButton, Qt.NoModifier, px(30, 30)); QTest.mouseMove(c.view, px(35, 36))
            QTest.mouseRelease(c.view, Qt.LeftButton, Qt.NoModifier, px(35, 36))
            r = c.zones[0]["rect"]; self.assertAlmostEqual(r[2], 35, delta=0.6); self.assertAlmostEqual(r[3], 36, delta=0.6); self.assertAlmostEqual(r[0], 10, delta=0.01)
            self.assertEqual(len(c.zones), 2)                                                                                  # resized, not a new zone
            QTest.mousePress(c.view, Qt.LeftButton, Qt.NoModifier, px(10, 20)); QTest.mouseMove(c.view, px(5, 20))  # left edge: only u min moves
            QTest.mouseRelease(c.view, Qt.LeftButton, Qt.NoModifier, px(5, 20))
            r = c.zones[0]["rect"]; self.assertAlmostEqual(r[0], 5, delta=0.6); self.assertAlmostEqual(r[1], 10, delta=0.01); self.assertEqual(c.zones[1]["kind"], "advised")
            from customlab import placement
            self.assertEqual(placement.zones_for(part, c.axis.currentData(), False)[0]["rect"], r)                             # saved
            c.undo_zone(); self.assertEqual([z["kind"] for z in c.zones], ["forbidden"]); c.undo_zone(); c.undo_zone(); self.assertEqual(c.zones, [])
