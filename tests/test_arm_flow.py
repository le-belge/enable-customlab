import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from customlab import armgen, openscad
    from customlab.gui import MainWindow
    from customlab.profiles import load_profile
    HAVE = armgen.scad_path(load_profile("unlimbited_arm")) is not None and openscad.find_openscad() is not None
except Exception:
    HAVE = False
from tests.test_deco import STAR


@unittest.skipUnless(HAVE, "official arm SCAD / OpenSCAD / PySide6 not available locally")
class ArmFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")

    def tearDown(self): self.d.cleanup()

    def arm(self, part="Palm", a=220, b=200, c=150, side="left"):
        w = MainWindow(); w.select("unlimbited_arm")
        w.side.setCurrentIndex(w.side.findData(side)); w.part.setCurrentIndex(w.part.findText(part))
        w.fields["BicepCircum"].setValue(a); w.fields["ForearmLen"].setValue(b); w.fields["HandLen"].setValue(c); w.recompute(); return w

    def test_letters_and_derived_scale_shown(self):
        from PySide6.QtWidgets import QFormLayout
        w = self.arm(); self.assertIn("111 %", w.live.toPlainText())                       # HandPerc = round(150 / 135 * 100)
        labels = []
        for i in range(w.form.rowCount()):
            it = w.form.itemAt(i, QFormLayout.LabelRole)
            if it is not None and it.widget() is not None: labels.append(it.widget().text())
        self.assertTrue(any(l.startswith("A — ") for l in labels) and any(l.startswith("B — ") for l in labels) and any(l.startswith("C — ") for l in labels), labels)

    def test_out_of_range_measure_is_refused_with_plain_message(self):
        w = self.arm(c=130); self.assertIsNone(w.sizing); self.assertIn("hors de la plage", w.live.toPlainText())

    def test_full_arm_flow_generate_decorate_export(self):
        w = self.arm("Palm"); w.go(2); c = w.custom
        self.assertTrue(c.gen_btn.isEnabled()); self.assertIn("à générer", c.gen_label.text())
        w.generate_arm_part(); self.assertIsNotNone(c.part_path); self.assertTrue(Path(c.part_path).is_file()); self.assertIn("générée", c.gen_label.text())
        self.assertIn("Non-Commercial", c.prov.text())                                    # licence of the SCAD travels with the generated part
        c.kind.setCurrentIndex(c.kind.findData("svg")); c.svg_path = str(STAR); c.size.setValue(24); c.depth.setValue(1.0)
        c.mode.setCurrentIndex(c.mode.findData("inlay")); c.qual.setCurrentIndex(c.qual.findData(0.25))
        ii = c.hm.shape; c.place(c.hm.u0 + ii[0] * c.hm.res / 2, c.hm.v0 + ii[1] * c.hm.res / 2); self.assertEqual(c.errors, [], c.errors)
        w.go(3); self.assertIsNotNone(w.out_tris); self.assertFalse(w.scale_cb.isVisibleTo(w))            # the arm is scaled by the SCAD itself, never by CustomLab
        out = w.export_to(Path(self.d.name) / "out"); meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertTrue(meta["source_license"]["share_alike"]); self.assertTrue(meta["source_license"]["non_commercial"]); self.assertIsNone(meta["scale_percent_applied"])
        self.assertEqual(meta["arm_generation"]["defines"]["HandLen"], 150); self.assertEqual(meta["device"], "unlimbited_arm")
        self.assertIn("PARTAGE DANS LES MÊMES CONDITIONS", next(out.parent.glob("*_ATTRIBUTION.txt")).read_text(encoding="utf-8")); self.assertTrue(next(out.parent.glob("*_Bambu_pret.3mf")).is_file())

    def test_changed_measures_invalidate_the_generated_part(self):
        w = self.arm("Palm"); w.go(2); w.generate_arm_part(); w.custom.text.setText("Léo"); w.go(1)
        w.fields["HandLen"].setValue(160); w.go(3)                                         # measures changed after generation
        self.assertIn("ne correspond pas", w.res.toPlainText()); self.assertFalse(w.b_exp.isEnabled()); self.assertIsNone(w.out_tris)

    def test_missing_measure_disables_generation(self):
        w = MainWindow(); w.select("unlimbited_arm"); w.go(2); self.assertFalse(w.custom.gen_btn.isEnabled()); self.assertIn("mesures valides", w.custom.gen_label.text())

    def test_switching_device_clears_the_part(self):
        w = self.arm("Palm"); w.go(2); w.generate_arm_part(); self.assertIsNotNone(w.custom.part_path)
        w.select("phoenix_hand"); self.assertIsNone(w.custom.part_path); self.assertIsNone(w.arm_gen)

    def test_project_roundtrip_keeps_the_generated_part(self):
        w = self.arm("Palm"); w.go(2); w.generate_arm_part(); w.custom.text.setText("Léo"); path = w.save_project(Path(self.d.name) / "bras")
        w2 = MainWindow(); self.assertEqual(w2.open_project(path), []); self.assertEqual(w2.dev, "unlimbited_arm")
        self.assertFalse(w2._arm_stale()); self.assertEqual(w2.fields["HandLen"].value(), 150); self.assertEqual(w2.custom.part_path, w.custom.part_path)

    def test_generation_runs_in_a_worker_thread(self):
        w = self.arm("Pins"); w.go(2); w.custom.sync = False; w.generate_arm_part()
        self.assertIn("Génération", w.custom.gen_label.text()); self.assertFalse(w.custom.gen_btn.isEnabled())       # busy state while OpenSCAD runs
        w.wait_generation(); self.assertTrue(w.custom.gen_btn.isEnabled()); self.assertIsNotNone(w.custom.part_path); self.assertIn("générée", w.custom.gen_label.text())

    def test_command_line_preset_for_the_arm(self):
        import argparse
        from customlab.gui import preset_arm
        w = MainWindow(); a = argparse.Namespace(side="left", arm_part="Palm", a=220.0, b=200.0, c=150.0, logo=str(STAR), size=24.0, depth=1.0, colors=1, mode="inlay", res=0.25, u=0.0, v=0.0)
        preset_arm(w, a); self.assertEqual(w.dev, "unlimbited_arm"); self.assertEqual(w.stack.currentIndex(), 2)
        self.assertIsNotNone(w.custom.part_path); self.assertEqual(w.custom.spec().mode, "inlay"); self.assertEqual(w.custom.errors, [], w.custom.errors)


if __name__ == "__main__":
    unittest.main()
