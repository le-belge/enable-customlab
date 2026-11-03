"""Constat 6 de l'audit : sources Unlimbited (SCAD sous un nom approchant, archive Thingiverse en deux parties). Arborescences factices."""
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("CUSTOMLAB_SYNC", "1")
from PySide6.QtWidgets import QApplication
from customlab import armgen, paths, placement, sources_dialog
from customlab.profiles import load_profile

_app = QApplication.instance() or QApplication([])
PART1 = "The UnLimbited Arm v2.1 - Alfie Edition - 1672381 - part 1 of 2.zip"


def _zip(path, entries):
    with zipfile.ZipFile(path, "w") as z:
        for n, data in entries.items(): z.writestr(n, data)
    return path


def _part1(d): return _zip(Path(d) / PART1, {"README.txt": "UnLimbited Arm", "LICENSE.txt": "CC BY-NC-SA", "images/arm.jpg": "jpg", "files/": ""})


def _part2_bytes():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z: z.writestr("files/UnLimbited_Arm_v2.1.scad", "// v2.1"); z.writestr("files/UnLimbited_Arm_V2.2.scad", "// v2.2")
    return b.getvalue()


class UnlimbitedSources(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.old = {k: os.environ.get(k) for k in ("CUSTOMLAB_SOURCES", "CUSTOMLAB_HOME")}
        self.src = Path(self.d.name) / "src"; os.environ["CUSTOMLAB_SOURCES"] = str(self.src); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")
        self.prof = load_profile("unlimbited_arm"); self.arm = self.src / "unlimbited_arm"

    def tearDown(self):
        for k, v in self.old.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        self.d.cleanup()

    def _put(self, rel, text="// scad"):
        f = self.arm / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text); return f

    def _status_text(self, lang="fr"):
        dlg = sources_dialog.SourcesDialog(None, lang); row = list(sources_dialog.DEVICES).index("unlimbited_arm")
        return dlg.grid.itemAtPosition(row, 1).widget().text()

    # cas A : partie 1 seule -> pas prêt, message « il manque la partie 2 sur 2 »
    def test_part1_only_says_part2_is_missing(self):
        sources_dialog.add_zip("unlimbited_arm", _part1(self.d.name))
        self.assertIsNone(armgen.scad_path(self.prof)); self.assertIs(sources_dialog.status("unlimbited_arm")[0], False)
        self.assertEqual(sources_dialog.scad_missing_reason("unlimbited_arm"), ("part2", None))
        fr, en = self._status_text("fr"), self._status_text("en")
        self.assertIn("il manque la partie 2 sur 2 de l'archive", fr); self.assertIn("UnLimbited_Arm_v2.1.scad", fr)
        self.assertIn("part 2 of 2 of the archive is missing", en)

    def test_empty_folder_keeps_the_plain_message(self):
        self.assertIsNone(sources_dialog.scad_missing_reason("unlimbited_arm")); self.assertEqual(self._status_text(), sources_dialog.TX["fr"]["ko_scad"])

    # cas C : .scad renommé par le navigateur, autre casse / séparateurs, sous-dossier quelconque
    def test_renamed_scad_is_found(self):
        for rel in ("Téléchargements/UnLimbited_Arm_v2.1 (1).scad", "x/y/unlimbited-arm-V2-1.SCAD", "UNLIMBITED ARM v2.1 copie.scad"):
            with self.subTest(rel=rel):
                f = self._put(rel); self.assertEqual(armgen.scad_path(self.prof), f); self.assertIs(sources_dialog.status("unlimbited_arm")[0], True); f.unlink()

    def test_exact_name_is_preferred_over_a_renamed_copy(self):
        self._put("a/UnLimbited_Arm_v2.1 (1).scad"); f = self._put("part2/files/UnLimbited_Arm_v2.1.scad")
        self.assertEqual(armgen.scad_path(self.prof), f)

    def test_found_elsewhere_in_the_sources_folder(self):
        f = self.src / "divers" / "UnLimbited_Arm_v2.1(2).scad"; f.parent.mkdir(parents=True); f.write_text("//")
        self.assertEqual(armgen.scad_path(self.prof), f)

    # cas D : seule la v2.2 (paramètres numériques, incompatibles avec le profil v2.1) -> refusée, message explicite
    def test_other_version_is_not_used_but_reported(self):
        self._put("files/UnLimbited_Arm_V2.2.scad"); self._put("._UnLimbited_Arm_v2.1.scad", "junk"); self._put("__MACOSX/files/UnLimbited_Arm_v2.1.scad", "junk")
        self.assertIsNone(armgen.scad_path(self.prof)); self.assertIs(sources_dialog.status("unlimbited_arm")[0], False)
        why = sources_dialog.scad_missing_reason("unlimbited_arm"); self.assertEqual((why[0], why[1].name), ("version", "UnLimbited_Arm_V2.2.scad"))
        self.assertIn("UnLimbited_Arm_V2.2.scad", self._status_text())

    # cas E : partie 2 restée sous un nom temporaire du navigateur, sans extension .zip
    def test_part2_without_zip_extension_is_unpacked(self):
        sources_dialog.add_zip("unlimbited_arm", _part1(self.d.name)); self.assertIsNone(armgen.scad_path(self.prof))
        for tmp in (".Q6L2SF6YDW", "part2.crdownload"):
            with self.subTest(tmp=tmp):
                (self.arm / tmp).write_bytes(_part2_bytes())
                found, _, p = sources_dialog.status("unlimbited_arm")
                self.assertIs(found, True); self.assertEqual(p.name, "UnLimbited_Arm_v2.1.scad"); self.assertFalse((self.arm / tmp).exists())
                for f in self.arm.rglob("*.scad"): f.unlink()

    def test_part2_under_its_thingiverse_name_without_zip_is_unpacked(self):
        # nom réel sans « .zip » : Path.suffix vaudrait « .1 - Alfie Edition - … », ce n'est pas une extension
        dl = Path(self.d.name) / "dl"; dl.mkdir(); name = PART1.replace("part 1 of 2.zip", "part 2 of 2"); (dl / name).write_bytes(_part2_bytes())
        sources_dialog.add_folder("unlimbited_arm", dl)
        p = armgen.scad_path(self.prof); self.assertIsNotNone(p); self.assertEqual(p.parent.parent.name, name); self.assertFalse((self.arm / name).is_file())

    def test_add_zip_accepts_an_archive_without_zip_extension(self):
        dl = Path(self.d.name) / "download_sans_extension"; dl.write_bytes(_part2_bytes())
        sources_dialog.add_zip("unlimbited_arm", dl); self.assertIsNotNone(armgen.scad_path(self.prof))

    def test_other_zip_based_files_are_not_unpacked(self):
        f = self.src / "kinetic_hand" / "Palm.3mf"; f.parent.mkdir(parents=True); _zip(f, {"3D/3dmodel.model": "x"})
        sources_dialog.unpack_nested("kinetic_hand"); self.assertTrue(f.is_file())

    # cas F : partie 1 puis partie 2 -> prêt
    def test_part1_then_part2_is_ready(self):
        sources_dialog.add_zip("unlimbited_arm", _part1(self.d.name))
        p2 = _zip(Path(self.d.name) / "part 2 of 2.zip", {"files/UnLimbited_Arm_v2.1.scad": "// v2.1"}); sources_dialog.add_zip("unlimbited_arm", p2)
        self.assertIs(sources_dialog.status("unlimbited_arm")[0], True); self.assertIn("✓", self._status_text())

    def test_generation_message_no_longer_points_to_a_developer_path(self):
        for lang in ("fr", "en"):
            msg = placement.TX[lang]["gen_noscad"]
            self.assertNotIn("docs/UNLIMBITED_ARM.md", msg); self.assertNotIn("part2/files", msg); self.assertIn("UnLimbited_Arm_v2.1.scad", msg)
        self.assertIn("partie 2 sur 2", placement.TX["fr"]["gen_noscad"]); self.assertIn("part 2 of 2", placement.TX["en"]["gen_noscad"])

    def test_find_similar_keeps_unversioned_names_generic(self):
        f = self.src / "phoenix_scad" / "UnLimbitedPhoenix (1).scad"; f.parent.mkdir(parents=True); f.write_text("//")
        self.assertEqual(paths.find_similar("UnLimbitedPhoenix.scad", "phoenix_scad")[0], f)


if __name__ == "__main__": unittest.main()
