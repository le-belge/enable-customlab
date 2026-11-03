"""Constat 9 (audit 2026-11-03): errors are logged to a file, shown to the user, never leave the export dialog stuck,
and settings / beneficiary profiles are written atomically and survive a damaged file."""
import io
import json
import logging
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QMessageBox

from customlab import errlog, paths
from customlab import batch_dialog as bd
from customlab import deco
from customlab import export_all_dialog as ed
from customlab.store import Store
from tests.test_deco import slab

app = QApplication.instance() or QApplication([])


class _Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.home = Path(self.tmp.name) / "données é"
        self.env = mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": str(self.home)}); self.env.start()

    def tearDown(self):
        lg = logging.getLogger("customlab")
        for h in list(lg.handlers):
            if getattr(h, "_customlab", False): lg.removeHandler(h); h.close()
        self.env.stop(); self.tmp.cleanup()

    def log_text(self):
        return "".join(f.read_text(encoding="utf-8") for f in sorted((self.home / "logs").glob("customlab.log*")))


class ErrorLog(_Home):
    def test_log_file_in_user_folder_with_rotation(self):
        with mock.patch.object(errlog, "MAX_BYTES", 2000):
            for i in range(200): errlog.warning(f"message {i} é")
        files = sorted(p.name for p in (self.home / "logs").glob("customlab.log*"))
        self.assertIn("customlab.log", files); self.assertIn("customlab.log.1", files); self.assertLessEqual(len(files), errlog.BACKUPS + 1)
        self.assertIn("message 199 é", (self.home / "logs" / "customlab.log").read_text(encoding="utf-8"))

    def test_excepthook_logs_and_shows_the_report(self):
        shown = []
        with mock.patch.object(errlog, "show", side_effect=shown.append), mock.patch.object(sys, "stderr", io.StringIO()):
            try: raise ValueError("boum é")
            except ValueError: errlog.excepthook(*sys.exc_info())
        self.assertIn("ValueError: boum é", self.log_text()); self.assertIn("Traceback", self.log_text())
        self.assertEqual(len(shown), 1); self.assertIn("boum é", shown[0])

    def test_worker_thread_error_is_logged_without_dialog(self):
        shown = []
        with mock.patch.object(errlog, "show", side_effect=shown.append), mock.patch.object(sys, "stderr", io.StringIO()), mock.patch.object(threading, "excepthook", errlog._thread_hook):
            t = threading.Thread(target=lambda: 1 / 0); t.start(); t.join()
        self.assertIn("ZeroDivisionError", self.log_text()); self.assertEqual(shown, [])

    def test_install_sets_hooks(self):
        old = sys.excepthook, threading.excepthook
        try: errlog.install(); self.assertIs(sys.excepthook, errlog.excepthook); self.assertIn("Démarrage de CustomLab", self.log_text())
        finally: sys.excepthook, threading.excepthook = old

    def test_dialog_copy_button_puts_report_in_clipboard(self):
        def click_copy(box): next(b for b in box.buttons() if b.text() == "Copier le rapport").click()
        with mock.patch.object(QMessageBox, "exec", click_copy): errlog.show("rapport é 123")
        self.assertEqual(QApplication.clipboard().text(), "rapport é 123")


class ExportDialogNeverStuck(_Home):
    def test_unwritable_destination_ends_with_an_error(self):
        d = self.home; d.mkdir(parents=True); a = d / "a.stl"; slab(a); blocker = d / "pas un dossier"; blocker.write_text("x", encoding="utf-8")
        ctx = {"mirror_for": lambda p: False, "extra": lambda: {}, "scale_for": lambda p: (100.0, None)}
        with mock.patch.object(ed.QFileDialog, "getExistingDirectory", return_value=str(blocker)):   # mkdir inside a file fails
            dlg = ed.ExportAllDialog(None, "fr", [{"label": "A", "path": a}], None, ctx, "", None)
            dlg.start(); t0 = time.time()
            while not hasattr(dlg, "results") and time.time() - t0 < 30: app.processEvents(); time.sleep(0.05)
        self.assertTrue(hasattr(dlg, "results"), "finished never emitted: dialog stuck")
        self.assertEqual([r["status"] for r in dlg.results], ["failed"]); self.assertTrue(dlg.b_go.isEnabled()); self.assertFalse(dlg.b_cancel.isEnabled())
        self.assertIn("Export interrompu", dlg.log.toPlainText()); self.assertIn("Traceback", self.log_text())


    def test_camo_batch_unwritable_destination_ends_with_an_error(self):
        d = self.home; d.mkdir(parents=True); a = d / "a.stl"; slab(a); blocker = d / "pas un dossier"; blocker.write_text("x", encoding="utf-8")
        ctx = {"mirror_for": lambda p: False, "extra": lambda: {}, "scale_for": lambda p: (100.0, None)}
        spec = deco.DecoSpec()
        with mock.patch.object(bd.QFileDialog, "getExistingDirectory", return_value=str(blocker)):
            dlg = bd.BatchDialog(None, "fr", [{"label": "A", "path": a}], spec, ctx, current=a)
            dlg.start(); t0 = time.time()
            while not hasattr(dlg, "results") and time.time() - t0 < 30: app.processEvents(); time.sleep(0.05)
        self.assertTrue(hasattr(dlg, "results"), "finished never emitted: dialog stuck")
        self.assertEqual([r["status"] for r in dlg.results], ["failed"]); self.assertTrue(dlg.b_go.isEnabled())
        self.assertIn("Export interrompu", dlg.log.toPlainText()); self.assertIn("Traceback", self.log_text())


class NestedError(_Home):
    def test_error_while_report_is_shown_is_logged_not_lost(self):
        shown = []
        def show(text):
            shown.append(text)
            try: raise KeyError("pendant la fenêtre é")              # e.g. a timer slot failing in the dialog's event loop
            except KeyError: errlog.excepthook(*sys.exc_info())
        with mock.patch.object(errlog, "show", side_effect=show), mock.patch.object(sys, "stderr", io.StringIO()):
            try: raise ValueError("premier")
            except ValueError: errlog.excepthook(*sys.exc_info())
        self.assertEqual(len(shown), 1); self.assertIn("pendant la fenêtre é", self.log_text()); self.assertIn("premier", self.log_text())


class DamagedFiles(_Home):
    def test_store_skips_a_damaged_profile(self):
        s = Store(self.home / "beneficiaries"); s.create("Léo"); s.create("Zoé"); (self.home / "beneficiaries" / "abime.json").write_text("{pas du json", encoding="utf-8")
        self.assertEqual([p["alias"] for p in s.list_profiles()], ["Léo", "Zoé"]); self.assertEqual([f.name for f in s.unreadable], ["abime.json"])
        self.assertIn("abime.json", self.log_text())

    def test_store_write_is_atomic(self):
        s = Store(self.home / "b"); pid = s.create("Léo"); before = s._path(pid).read_text(encoding="utf-8")
        with mock.patch.object(paths.os, "replace", side_effect=OSError("disque plein")):
            with self.assertRaises(OSError): s._save({"id": pid, "alias": "X", "records": []})
        self.assertEqual(s._path(pid).read_text(encoding="utf-8"), before); self.assertEqual(list((self.home / "b").glob("*.tmp")), [])

    def test_unreadable_settings_kept_as_bak(self):
        self.home.mkdir(parents=True); f = self.home / "settings.json"; f.write_text('{"sources_dir": "C:/Données", ', encoding="utf-8")
        paths.save_setting("advanced_mode", True)
        self.assertEqual(json.loads(f.read_text(encoding="utf-8")), {"advanced_mode": True})
        self.assertEqual((self.home / "settings.json.bak").read_text(encoding="utf-8"), '{"sources_dir": "C:/Données", ')
        paths.save_setting("x", 1); self.assertEqual(paths.get_setting("advanced_mode"), True)      # readable file: keys kept

    def test_damaged_project_does_not_crash(self):
        from customlab.gui import MainWindow
        w = MainWindow(); bad = self.home / "projet abîmé.customlab.json"; self.home.mkdir(parents=True, exist_ok=True)
        for content in ("{tronqué", "[1, 2]"):
            bad.write_text(content, encoding="utf-8")
            with mock.patch.object(QMessageBox, "warning") as warn: problems = w.open_project(bad)
            warn.assert_called_once(); self.assertEqual(len(problems), 1); self.assertIn("Impossible d'ouvrir ce projet", problems[0])


if __name__ == "__main__": unittest.main()
