import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("CUSTOMLAB_SYNC", "1")
from PySide6.QtWidgets import QApplication
from customlab import library, paths, sources_dialog

_app = QApplication.instance() or QApplication([])


class Sources(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.old = {k: os.environ.get(k) for k in ("CUSTOMLAB_SOURCES", "CUSTOMLAB_HOME")}
        os.environ["CUSTOMLAB_SOURCES"] = str(Path(self.d.name) / "src"); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")

    def tearDown(self):
        for k, v in self.old.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        self.d.cleanup()

    def test_sources_prefix_resolves_in_the_users_folder_and_other_paths_next_to_the_code(self):
        self.assertEqual(paths.resolve("sources/unlimbited_arm/x.scad"), Path(self.d.name) / "src" / "unlimbited_arm" / "x.scad")
        self.assertEqual(paths.resolve("docs/TUTO_ECHELLES.md"), paths.resource_dir() / "docs" / "TUTO_ECHELLES.md")

    def test_setting_is_remembered_and_env_wins(self):
        paths.save_setting("sources_dir", "/x/y"); self.assertEqual(paths.get_setting("sources_dir"), "/x/y")
        self.assertEqual(paths.sources_dir(), Path(self.d.name) / "src")                      # env variable has priority
        del os.environ["CUSTOMLAB_SOURCES"]; self.assertEqual(paths.sources_dir(), Path("/x/y"))

    def test_status_and_library_follow_the_folder(self):
        self.assertIs(sources_dialog.status("kinetic_hand")[0], False); self.assertIs(sources_dialog.status("unlimbited_arm")[0], False)
        f = Path(self.d.name) / "src" / "kinetic_hand" / "stl" / "Palm (RH 100%).stl"; f.parent.mkdir(parents=True)
        from tests.test_deco import slab
        slab(f, w=20, l=20, t=3)
        self.assertEqual(sources_dialog.status("kinetic_hand")[:2], (True, 1))
        self.assertTrue(any(i["device"] == "kinetic_hand" for i in library.scan_all()))
        self.assertTrue(any(i["bundled"] and i["device"] == "phoenix_hand" for i in library.scan_all()))      # bundled Phoenix parts always there

    def test_dialog_opens_and_lists_every_device(self):
        dlg = sources_dialog.SourcesDialog(None, "fr"); self.assertEqual(dlg.grid.count(), 3 * len(sources_dialog.DEVICES)); self.assertIn("✗", " ".join(w.widget().text() for w in map(dlg.grid.itemAt, range(dlg.grid.count())) if hasattr(w.widget(), "text")))


if __name__ == "__main__": unittest.main()
