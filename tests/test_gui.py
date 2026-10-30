import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from customlab.gui import MainWindow
    HAVE = True
except Exception:  # PySide6 missing
    HAVE = False
from tests.test_sprint2 import _cube_stl


@unittest.skipUnless(HAVE, "PySide6 not installed")
class GuiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_catalog_has_four_devices_with_honest_status(self):
        w = MainWindow(); self.assertEqual(set(w.cards), {"phoenix_hand", "unlimbited_arm", "kinetic_hand", "kinetic_arm"})
        self.assertIn("EXPÉRIMENTAL", w.cards["kinetic_arm"][0].text()); self.assertIn("EXPÉRIMENTAL", w.cards["kinetic_hand"][0].text()); self.assertIn("EXPÉRIMENTAL", w.cards["phoenix_hand"][0].text())

    def test_phoenix_flow_and_out_of_range_not_forced(self):
        w = MainWindow(); w.select("phoenix_hand")
        w.fields["wrist_mm"].setValue(40)
        self.assertEqual(w.sizing.scad_defines["HandPerc"], 104.65)
        w.fields["wrist_mm"].setValue(80)
        self.assertIsNone(w.sizing); self.assertIn("Rien n'a été modifié", w.live.toPlainText())

    def test_generate_from_local_stl_and_view(self):
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(40)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.stl"; _cube_stl(p); w.load_stl(str(p))
        self.assertEqual(len(w.out_tris), 12); self.assertIsNotNone(w.view.tris)
        w.view.resize(400, 400); self.assertFalse(w.view.grab().isNull())

    def test_kinetic_sizing_flows(self):
        w = MainWindow(); w.select("kinetic_hand"); self.assertIsNone(w.sizing)
        w.select("kinetic_arm"); self.assertIsNone(w.sizing)
        for k, x in (("hand_mm", 168.7), ("elbow_mm", 70.66), ("resid_mm", 83.32)): w.fields[k].setValue(x)
        self.assertEqual((w.sizing.derived["lower_scale"], w.sizing.derived["forearm_type"], w.sizing.derived["insert"]), (70.0, "B", "D"))
        self.assertIn("Insert D", w.live.toPlainText()); w.fields["hand_mm"].setValue(100); self.assertIsNone(w.sizing)

    def test_language_toggle(self):
        w = MainWindow("fr"); w.toggle_lang(); self.assertEqual(w.langbtn.text(), "Français")

    def test_phoenix_custom_flow_exports_original_size(self):
        import hashlib, json
        from customlab.meshio import bbox, read_stl
        from tests.test_deco import slab
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(40)
        self.assertIn("SCAD", w.profiles["phoenix_hand"]["notice"])               # the confirmed rule and its limit stay visible
        with tempfile.TemporaryDirectory() as d:
            part = Path(d) / "src" / "p.stl"; part.parent.mkdir(); slab(part); h0 = hashlib.sha256(part.read_bytes()).hexdigest()
            w.load_stl(str(part)); w.custom.text.setText("Léo"); w.custom.size.setValue(25); w.custom.place(30, 30)
            w.go(3); self.assertIsNotNone(w.out_tris); self.assertIn("EXPÉRIMENTALE", w.res.toPlainText())
            out = w.export_to(Path(d) / "out")                                    # default now: documented scale applied
            self.assertAlmostEqual(bbox(read_stl(out))[1][0], 60.0 * 1.0465, places=2)
            w.scale_cb.setChecked(False); out0 = w.export_to(Path(d) / "out0")    # untick -> original size
            self.assertAlmostEqual(bbox(read_stl(out0))[1][0], 60.0, places=3)
            w.scale_cb.setChecked(True); out2 = w.export_to(Path(d) / "out2")
            self.assertAlmostEqual(bbox(read_stl(out2))[1][0], 60.0 * 1.0465, places=2)
            self.assertEqual(json.loads(out2.with_suffix(".json").read_text(encoding="utf-8"))["scale_percent_applied"], 104.65)
            self.assertEqual(hashlib.sha256(part.read_bytes()).hexdigest(), h0)
            w.custom.place(58, 30); w.go(3)                                       # off the part -> refused, nothing to export
            self.assertIsNone(w.out_tris)
            with self.assertRaises(Exception): w.export_to(Path(d) / "out3")

    def test_scale_opt_in_blocked_when_sizing_invalid(self):
        from tests.test_deco import slab
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(80)       # out of documented range
        with tempfile.TemporaryDirectory() as d:
            part = Path(d) / "s" / "p.stl"; part.parent.mkdir(); slab(part); w.load_stl(str(part)); w.custom.place(30, 30); w.go(3)
            w.scale_cb.setChecked(True)
            with self.assertRaises(Exception): w.export_to(Path(d) / "o")

    def test_zone_drawn_blocks_and_four_steps(self):
        from tests.test_deco import slab
        w = MainWindow(); w.select("phoenix_hand"); self.assertEqual(w.stack.count(), 4)
        with tempfile.TemporaryDirectory() as d:
            part = Path(d) / "s" / "p.stl"; part.parent.mkdir(); slab(part); w.load_stl(str(part)); w.custom.text.setText("Léo"); w.custom.place(30, 30)
            w.custom.add_zone(20, 20, 40, 40); self.assertTrue(any("zone interdite" in e for e in w.custom.errors))
            w.custom.clear_zones(); self.assertEqual(w.custom.errors, [])
            w.custom.grab(); w.custom.view.grab()

    def test_library_pick_loads_part(self):
        w = MainWindow(); w.select("phoenix_hand")
        self.assertEqual(w.custom.lib.count(), 17)                    # placeholder + 16 bundled parts
        w.custom.pick_library(1); self.assertIsNotNone(w.custom.part_path); self.assertTrue(w.custom.lic["known"])

    def test_export_after_library_pick_with_svg(self):
        import json
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(40); c = w.custom
        c.pick_library(next(i for i in range(1, c.lib.count()) if c.lib.itemText(i).startswith("Palm · left")))
        c.kind.setCurrentIndex(c.kind.findData("svg")); c.svg_path = str(Path(__file__).parent.parent / "examples/star.svg")
        c.size.setValue(26); c.place(54.3, -116.5); w.go(3); self.assertIsNotNone(w.out_tris)
        with tempfile.TemporaryDirectory() as d:
            out = w.export_to(d); meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(meta["spec"]["kind"], "svg"); self.assertTrue(meta["source_license"]["non_commercial"])

    def test_colour_layers_paint_without_crash_and_export(self):
        import json
        from PySide6.QtGui import QColor, QImage
        w = MainWindow(); w.resize(900, 700); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(40); c = w.custom
        with tempfile.TemporaryDirectory() as d:
            im = QImage(120, 120, QImage.Format_RGB32); im.fill(QColor("white"))
            for x in range(10, 55):
                for y in range(10, 110): im.setPixelColor(x, y, QColor(16, 72, 127))
            for x in range(65, 110):
                for y in range(10, 110): im.setPixelColor(x, y, QColor(207, 39, 51))
            f = Path(d) / "l.png"; im.save(str(f))
            c.pick_library(next(i for i in range(1, c.lib.count()) if c.lib.itemText(i).startswith("Palm · left")))
            c.kind.setCurrentIndex(c.kind.findData("image")); c.svg_path = str(f); c.size.setValue(30); c.depth.setValue(1.0)
            c.mode.setCurrentIndex(c.mode.findData("inlay")); c.place(54.3, -116.5); c.ncol.setValue(2)
            self.assertEqual(len(c.layers), 2); c.view.grab(); w.go(3); self.assertEqual(len(w.deco_result.layers), 2); w.grab()
            out = w.export_to(Path(d) / "o"); self.assertEqual(len(list(out.parent.glob("*.stl"))), 3)
            self.assertEqual(len(json.loads(next(out.parent.glob("*.json")).read_text(encoding="utf-8"))["color_pieces"]), 2)

    def test_preset_preloads_logo(self):
        import argparse
        from customlab.gui import preset
        w = MainWindow(); a = argparse.Namespace(logo=str(Path(__file__).parent.parent / "examples/robot_complexe.svg"), part="Palm · left", wrist=40.0,
                                                 size=28.0, depth=1.0, u=54.3, v=-116.5, colors=1, mode="inlay", res=0.25)
        preset(w, a); self.assertEqual(w.stack.currentIndex(), 2); self.assertEqual(w.custom.kind.currentData(), "svg")
        self.assertEqual(w.custom.errors, []); self.assertIsNotNone(w.custom.mask)

    def _loaded_page(self):
        from PySide6.QtCore import QPointF
        from tests.test_deco import slab
        w = MainWindow(); w.resize(1000, 700); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(40); self._d = tempfile.TemporaryDirectory()
        part = Path(self._d.name) / "p" / "p.stl"; part.parent.mkdir(); slab(part)
        w.load_stl(str(part)); c = w.custom; c.text.setText("Léo"); c.size.setValue(20); c.place(30, 30); w.go(2); c.view.resize(600, 500)
        return w, c, part

    def test_wheel_keys_and_drag_edit_the_motif(self):
        from PySide6.QtCore import QPointF, Qt
        w, c, part = self._loaded_page(); v = c.view
        centre = v._to_px(30, 30)
        s0 = c.size.value(); self.assertEqual(v.wheel_action(120, Qt.NoModifier, centre), "scale"); self.assertGreater(c.size.value(), s0)       # over the motif
        r0 = c.rot.value(); self.assertEqual(v.wheel_action(120, Qt.ShiftModifier, centre), "rotate"); self.assertNotEqual(c.rot.value(), r0)
        z0 = v.zoom; self.assertEqual(v.wheel_action(120, Qt.ControlModifier, centre), "zoom"); self.assertGreater(v.zoom, z0)
        v.zoom = 1.0; v.pan = QPointF(0, 0)
        far = v._to_px(3, 3); self.assertEqual(v.wheel_action(120, Qt.NoModifier, far), "zoom")                                                # away from the motif -> zooms the view
        v.zoom = 1.0; v.pan = QPointF(0, 0)
        u0 = c.u.value(); v.nudged.emit(5.0, 0); self.assertAlmostEqual(c.u.value(), u0 + 5.0, places=1)
        v.moved.emit(20.0, 25.0); self.assertAlmostEqual(c.u.value(), 20.0, places=1); self.assertAlmostEqual(c.v.value(), 25.0, places=1)
        self._d.cleanup()

    def test_zoom_keeps_point_under_cursor(self):
        from PySide6.QtCore import QPointF
        w, c, part = self._loaded_page(); v = c.view; p = QPointF(200, 150); before = v._to_uv(p)
        v.zoom_at(p, 2.0); after = v._to_uv(p); self.assertAlmostEqual(before[0], after[0], places=3); self.assertAlmostEqual(before[1], after[1], places=3)
        self._d.cleanup()

    def test_zones_are_remembered_for_the_same_part(self):
        w, c, part = self._loaded_page(); c.add_zone(2, 2, 8, 8); self.assertEqual(len(c.zones), 1)
        w2 = MainWindow(); w2.select("phoenix_hand"); w2.load_stl(str(part)); self.assertEqual(len(w2.custom.zones), 1)     # reloaded from disk
        c.clear_zones(); w3 = MainWindow(); w3.select("phoenix_hand"); w3.load_stl(str(part)); self.assertEqual(w3.custom.zones, [])
        self._d.cleanup()

    def test_protected_margin_is_a_page_setting(self):
        w, c, part = self._loaded_page(); self.assertEqual(c.spec().protect_margin_mm, 2.0)
        c.prot.setValue(0.0); self.assertEqual(c.spec().protect_margin_mm, 0.0); c.view.grab(); self._d.cleanup()

    def test_open_button_needs_an_export_with_3mf(self):
        w, c, part = self._loaded_page(); c.mode.setCurrentIndex(c.mode.findData("inlay")); w.go(3)
        self.assertFalse(w.b_open.isEnabled()); out = w.export_to(Path(self._d.name) / "o"); self.assertTrue(w.b_open.isEnabled())
        self.assertTrue(str(w.last_3mf).endswith("_Bambu_pret.3mf")); self._d.cleanup()

    def test_scale_requested_without_measure_blocks_export_with_a_clear_message(self):
        from tests.test_deco import slab
        w = MainWindow(); w.select("phoenix_hand")                                  # no wrist entered: sizing is None, scale option is ON by default
        with tempfile.TemporaryDirectory() as d:
            part = Path(d) / "s" / "p.stl"; part.parent.mkdir(); slab(part); w.load_stl(str(part)); w.custom.text.setText("Léo"); w.custom.place(30, 30); w.go(3)
            self.assertIn("non calculable", w.res.toPlainText()); self.assertFalse(w.b_exp.isEnabled())
            with self.assertRaises(Exception) as cm: w.export_to(Path(d) / "o")
            self.assertIn("saisissez les mesures", str(cm.exception)); self.assertIn("directement", str(cm.exception))
            w.scale_cb.setChecked(False); w.go(2); w.go(3); self.assertTrue(w.b_exp.isEnabled()); self.assertTrue(w.export_to(Path(d) / "o2").is_file())

    def test_3mf_parts_follow_the_scale(self):
        import re, zipfile
        from tests.test_deco import slab
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(40)
        with tempfile.TemporaryDirectory() as d:
            part = Path(d) / "s" / "p.stl"; part.parent.mkdir(); slab(part); w.load_stl(str(part)); c = w.custom
            c.mode.setCurrentIndex(c.mode.findData("inlay")); c.text.setText("Léo"); c.size.setValue(20); c.place(30, 30); w.go(3)
            out = w.export_to(Path(d) / "o"); z = zipfile.ZipFile(next(out.parent.glob("*_Bambu_pret.3mf")))
            xs = [float(x) for x in re.findall(r' x="([-\d.]+)"', z.read("3D/Objects/object_1.model").decode())]
            self.assertAlmostEqual(max(xs), 60.0 * 1.0465, places=2)                  # base part scaled like the STL export


if __name__ == "__main__":
    unittest.main()
