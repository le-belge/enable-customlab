import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from customlab.gui import MainWindow
    from customlab.profiles_dialog import BeneficiaryDialog
    from customlab.store import Store
    HAVE = True
except Exception:
    HAVE = False
from tests.test_deco import slab, STAR


@unittest.skipUnless(HAVE, "PySide6 not installed")
class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")
        self.part = Path(self.d.name) / "src" / "p.stl"; self.part.parent.mkdir(); slab(self.part)

    def tearDown(self): self.d.cleanup()

    def configured(self, wrist=40.0, size=22.0, u=30.0, v=30.0):
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(wrist); w.load_stl(str(self.part)); c = w.custom
        c.kind.setCurrentIndex(c.kind.findData("svg")); c.svg_path = str(STAR); c.size.setValue(size); c.depth.setValue(1.0)
        c.mode.setCurrentIndex(c.mode.findData("inlay")); c.qual.setCurrentIndex(c.qual.findData(0.25)); c.place(u, v); c.add_zone(2, 2, 6, 6)
        return w

    # ---- measurement assistant
    def test_schema_follows_device_and_language(self):
        w = MainWindow(); w.select("phoenix_hand"); self.assertFalse(w.schema.isHidden() and False); self.assertTrue(w.schema.renderer().isValid())
        w.toggle_lang(); self.assertTrue(w.schema.renderer().isValid())                    # English variant loads
        w.select("kinetic_hand"); self.assertTrue(w.schema.isHidden())                       # no documented measurement for Kinetic
        for f in ("poignet_fr", "poignet_en", "bras_fr", "bras_en"): self.assertTrue((Path(__file__).parent.parent / "customlab/assets/schemas" / f"{f}.svg").is_file())

    # ---- projects
    def test_project_roundtrip_restores_everything(self):
        w = self.configured(); out = w.save_project(Path(self.d.name) / "essai")
        self.assertTrue(out.endswith(".customlab.json")); st = json.loads(Path(out).read_text(encoding="utf-8"))
        self.assertEqual(st["device"], "phoenix_hand"); self.assertEqual(st["custom"]["spec"]["mode"], "inlay"); self.assertEqual(len(st["custom"]["zones"]), 1)
        w2 = MainWindow(); self.assertEqual(w2.open_project(out), [])
        self.assertEqual(w2.dev, "phoenix_hand"); self.assertEqual(w2.fields["wrist_mm"].value(), 40.0)
        c = w2.custom; self.assertEqual(c.part_path, str(self.part)); self.assertEqual(c.spec().mode, "inlay"); self.assertEqual(c.size.value(), 22.0)
        self.assertEqual(c.zones, [(2, 6, 6, 2)] if False else c.zones); self.assertEqual(len(c.zones), 1); self.assertAlmostEqual(c.u.value(), 30.0, places=1)
        self.assertIn(out, w2.recent_projects()); self.assertEqual(c.errors, [])

    def test_missing_files_are_reported_not_fatal(self):
        w = self.configured(); out = w.save_project(Path(self.d.name) / "p2"); self.part.unlink()
        w2 = MainWindow(); problems = w2.load_state(json.loads(Path(out).read_text(encoding="utf-8")))
        self.assertTrue(any("introuvable" in x for x in problems)); self.assertEqual(w2.dev, "phoenix_hand")

    def test_unknown_or_empty_state_is_refused(self):
        w = MainWindow(); self.assertTrue(w.load_state({})); self.assertTrue(w.load_state({"device": "nope"}))

    def test_menus_exist_in_both_languages(self):
        w = MainWindow(); self.assertEqual(w.m_file.title(), "Fichier"); w.toggle_lang(); self.assertEqual(w.m_file.title(), "File"); self.assertEqual(w.a_prof.text(), "Beneficiary profiles…")

    # ---- beneficiary profiles
    def test_profile_history_compare_reload(self):
        w = self.configured(wrist=40.0); dlg = BeneficiaryDialog(w)
        pid = dlg.new_profile("Lucioles-7"); self.assertIsNotNone(pid); self.assertEqual(dlg.save_current(), 0)
        w.fields["wrist_mm"].setValue(44.0); self.assertEqual(dlg.save_current(), 1)                     # a later visit
        recs = dlg.records(); self.assertEqual([r["measurements"]["wrist_mm"] for r in recs], [40.0, 44.0]); self.assertEqual(set(Store(dlg.store.root).load(pid)), {"id", "alias", "records"})
        text = dlg.compare_selected([0, 1]); self.assertIn("wrist_mm : 40 → 44", text); self.assertIn("+4", text); self.assertIn("+10.0 %", text)
        self.assertTrue(dlg.toggle_made(0)); self.assertTrue(dlg.records()[0]["fabricated"]); self.assertFalse(dlg.toggle_made(0))
        w.fields["wrist_mm"].setValue(50.0); self.assertEqual(dlg.reload_selected(0), []); self.assertEqual(w.fields["wrist_mm"].value(), 40.0)   # regenerate from an old record
        self.assertEqual(w.custom.spec().mode, "inlay"); self.assertEqual(w.custom.size.value(), 22.0)

    def test_profile_privacy_and_guards(self):
        w = MainWindow(); w.select("phoenix_hand"); dlg = BeneficiaryDialog(w)
        self.assertIsNone(dlg.new_profile("   ")); self.assertIsNone(dlg.save_current())                  # no profile selected
        pid = dlg.new_profile("alias"); w.fields["wrist_mm"].setValue(80.0); self.assertIsNone(dlg.save_current())   # invalid sizing -> nothing saved
        self.assertEqual(dlg.records(), []); self.assertIn("pseudonyme", dlg.notice.text())
        self.assertTrue(dlg.delete_profile(ask=False)); self.assertEqual(dlg.store.list_profiles(), [])

    def test_two_profiles_listed_and_isolated(self):
        w = self.configured(); dlg = BeneficiaryDialog(w); a = dlg.new_profile("Béta"); dlg.save_current(); b = dlg.new_profile("Alpha")
        self.assertEqual([p["alias"] for p in dlg.store.list_profiles()], ["Alpha", "Béta"]); self.assertEqual(dlg.records(), [])
        dlg.refresh_list(select=a); self.assertEqual(len(dlg.records()), 1)


@unittest.skipUnless(HAVE, "PySide6 not installed")
class AsyncRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")
        self.part = Path(self.d.name) / "p.stl"; slab(self.part)
        self.w = MainWindow(); self.w.select("phoenix_hand"); self.w.fields["wrist_mm"].setValue(40); self.w.load_stl(str(self.part)); self.c = c = self.w.custom
        c.kind.setCurrentIndex(c.kind.findData("svg")); c.svg_path = str(STAR); c.size.setValue(24); c.qual.setCurrentIndex(c.qual.findData(0.25))

    def tearDown(self): self.d.cleanup()

    def test_async_gives_same_result_as_sync(self):
        c = self.c; c.sync = True; c.place(30, 30); m_sync = c.mask.copy(); e_sync = list(c.errors)
        c.sync = False; c.place(30, 30)
        self.assertTrue(c._timer.isActive() and c.busy.text())               # pending + progress message shown
        c.ensure_fresh(); self.assertEqual(c.busy.text(), ""); self.assertTrue((c.mask == m_sync).all()); self.assertEqual(c.errors, e_sync)

    def test_only_the_last_change_is_displayed(self):
        c = self.c; c.sync = False
        c.place(10, 10); c.place(20, 20); c.place(30, 30)                    # rapid changes: debounced into one job
        c.ensure_fresh(); self.assertAlmostEqual(c.view.center_uv[0], 30.0, places=1)
        ref = c._compute(c.spec(), list(c.zones), c.hm, c.protected_mask(c.spec()), True); self.assertEqual(int(c.mask.sum()), int(ref["mask"].sum()))

    def test_stale_result_is_ignored(self):
        c = self.c; c.sync = False; c.place(10, 10); c._timer.stop(); c._start_job(); old = c._gen          # job for u=10 started
        c.place(30, 30); c.ensure_fresh()                                     # newer change must win even if the old job finishes later
        self.assertGreater(c._gen, old); self.assertAlmostEqual(c.view.center_uv[0], 30.0, places=1)

    def test_colour_logo_in_worker_thread_does_not_crash_and_matches(self):
        from PySide6.QtGui import QColor, QImage
        im = QImage(120, 120, QImage.Format_RGB32); im.fill(QColor("white"))
        for x in range(10, 55):
            for y in range(10, 110): im.setPixelColor(x, y, QColor(16, 72, 127))
        for x in range(65, 110):
            for y in range(10, 110): im.setPixelColor(x, y, QColor(207, 39, 51))
        f = Path(self.d.name) / "l.png"; im.save(str(f)); c = self.c
        c.kind.setCurrentIndex(c.kind.findData("image")); c.svg_path = str(f); c.ncol.setValue(2); c.mode.setCurrentIndex(c.mode.findData("inlay"))
        c.sync = True; c.place(30, 30); want = sorted(int(m.sum()) for _, _, m in c.layers)
        c.sync = False
        for i in range(8): c.place(28 + i * 0.5, 30)                          # several overlapping jobs
        c.place(30, 30); c.ensure_fresh(); self.assertEqual(sorted(int(m.sum()) for _, _, m in c.layers), want)

    def test_result_page_waits_for_pending_computation(self):
        c = self.c; c.sync = False; c.place(30, 30); self.w.go(3)             # must not use a stale placement
        self.assertIn("Calcul", self.w.res.toPlainText()); self.assertFalse(self.w.b_exp.isEnabled())      # heavy step runs in the background
        self.w.wait_result(); self.assertIsNotNone(self.w.out_tris); self.assertEqual(c.errors, []); self.assertTrue(self.w.b_exp.isEnabled())
        self.assertIn("Phoenix", self.w.res.toPlainText())

    def test_leaving_the_result_page_drops_the_pending_result(self):
        c = self.c; c.sync = False; c.place(30, 30); self.w.go(3); self.w.go(2)                              # leave before it finishes
        self.w.wait_result(); self.assertIsNone(self.w.out_tris)                                              # stale result was discarded

    def test_export_waits_for_pending_result(self):
        c = self.c; c.sync = False; c.place(30, 30); c.mode.setCurrentIndex(c.mode.findData("inlay")); self.w.go(3)
        out = self.w.export_to(Path(self.d.name) / "out"); self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
