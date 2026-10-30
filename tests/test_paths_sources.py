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

    def test_scad_is_found_wherever_the_archive_put_it(self):
        from customlab import armgen
        from customlab.profiles import load_profile
        prof = load_profile("unlimbited_arm"); self.assertIsNone(armgen.scad_path(prof))
        f = Path(self.d.name) / "src" / "unlimbited_arm" / "unzipped" / "files" / "unlimbited_arm_v2.1.SCAD"; f.parent.mkdir(parents=True); f.write_text("// x")
        self.assertEqual(armgen.scad_path(prof), f); self.assertIs(sources_dialog.status("unlimbited_arm")[0], True)

    def test_add_zip_puts_files_in_the_device_folder_and_refuses_escaping_entries(self):
        import zipfile
        z = Path(self.d.name) / "kin.zip"
        with zipfile.ZipFile(z, "w") as zf: zf.writestr("Kinetic Hand/Palm.stl", "solid x\nendsolid x\n"); zf.writestr("__MACOSX/._Palm.stl", "junk")
        self.assertEqual(sources_dialog.add_zip("kinetic_hand", z), 1)
        self.assertTrue((Path(self.d.name) / "src" / "kinetic_hand" / "Kinetic Hand" / "Palm.stl").is_file()); self.assertIs(sources_dialog.status("kinetic_hand")[0], True)
        bad = Path(self.d.name) / "bad.zip"
        with zipfile.ZipFile(bad, "w") as zf: zf.writestr("../evil.stl", "x")
        with self.assertRaises(ValueError): sources_dialog.add_zip("kinetic_arm", bad)
        self.assertFalse((Path(self.d.name) / "src" / "evil.stl").exists())

    def test_add_folder_copies_and_refuses_the_sources_folder_itself(self):
        s = Path(self.d.name) / "dl"; (s / "a").mkdir(parents=True); (s / "a" / "P.stl").write_text("x"); (s / ".DS_Store").write_text("x")
        self.assertEqual(sources_dialog.add_folder("kinetic_arm", s), 1); self.assertTrue((Path(self.d.name) / "src" / "kinetic_arm" / "a" / "P.stl").is_file())
        with self.assertRaises(ValueError): sources_dialog.add_folder("kinetic_arm", Path(self.d.name) / "src" / "kinetic_arm")

    def test_dialog_opens_and_lists_every_device(self):
        dlg = sources_dialog.SourcesDialog(None, "fr"); self.assertEqual(dlg.grid.count(), 3 * len(sources_dialog.DEVICES)); self.assertIn("✗", " ".join(w.widget().text() for w in map(dlg.grid.itemAt, range(dlg.grid.count())) if hasattr(w.widget(), "text")))


if __name__ == "__main__": unittest.main()
