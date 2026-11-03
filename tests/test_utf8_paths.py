"""Constat 7 (audit 2026-11-03): .scad scripts and OpenSCAD's output must be UTF-8 whatever the system code page.

Windows is simulated by making every text I/O that does not name its encoding use cp1252 (Python's default there). A fake
OpenSCAD reads the script strictly as UTF-8 (as the real one does) and writes UTF-8 + an undefined cp1252 byte on stderr.
Paths contain accents and spaces ("Dossier é").
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from customlab import cache, deco, meshscale, messages, openscad, thumbs
from customlab.meshio import read_stl
from tests.test_deco import slab

FAKE = r'''#!{exe}
import re, shutil, sys
args = sys.argv[1:]; out = args[args.index("-o") + 1]; scad = args[-1]
if "{fail}" == "1":     # like OpenSCAD: the message names the script, in UTF-8 whatever the code page, plus undefined cp1252 bytes
    sys.stderr.buffer.write(("ERREUR : impossible d'ouvrir « %s » données\n" % scad).encode("utf-8") + b"\x81\x8d\x9d\n"); sys.exit(1)
try: text = open(scad, "rb").read().decode("utf-8")
except UnicodeDecodeError as e: sys.stderr.write("cannot decode script: %s\n" % e); sys.exit(1)
paths = re.findall(r'import\("([^"]+)"\)', text)
missing = [p for p in paths if not __import__("os").path.isfile(p)]
if missing:
    sys.stderr.buffer.write(("ERREUR : fichier introuvable « %s » données\n" % (missing or ["x"])[0]).encode("utf-8") + b"\x81\x8d\x9d\n"); sys.exit(1)
sys.stderr.buffer.write("Avertissement : géométrie\n".encode("utf-8") + b"\x81\x8d\x8f\x90\x9d\n")
shutil.copyfile(paths[0], out)
'''

_real_text_encoding = getattr(io, "text_encoding", None)      # Python 3.10+ only


def _windows_code_page():
    """Patches making every unspecified text encoding cp1252, as on a French Windows (Python 3.10+ via io.text_encoding, 3.9 via _bootlocale)."""
    if _real_text_encoding is not None:
        return [mock.patch.object(io, "text_encoding", lambda enc, stacklevel=2: _real_text_encoding(enc) if enc is not None else "cp1252"),
                mock.patch.object(subprocess, "_text_encoding", lambda: "cp1252")]
    return [mock.patch("_bootlocale.getpreferredencoding", lambda do_setlocale=True: "cp1252")]


class Utf8Paths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.dir = Path(self.tmp.name) / "Dossier é"; self.dir.mkdir()
        self.part = self.dir / "Paume gauche é.stl"; slab(self.part)
        self.patches = _windows_code_page()
        for p in self.patches: p.start()

    def tearDown(self):
        for p in self.patches: p.stop()
        self.tmp.cleanup()

    def _fake(self, fail=False):
        """Fake OpenSCAD, run as "python <script> -o ... file.scad": Windows cannot execute a .py script directly (WinError 193)."""
        f = self.dir / ("openscad fail.py" if fail else "openscad é.py")
        f.write_text(FAKE.replace("{exe}", sys.executable).replace("{fail}", "1" if fail else "0"), encoding="utf-8")
        real = openscad.build_command
        return [mock.patch.object(openscad, "find_openscad", return_value=str(f)),
                mock.patch.object(openscad, "build_command", lambda *a, **k: [sys.executable] + real(*a, **k))]

    def _with_fake(self, fail=False):
        for p in self._fake(fail): p.start(); self.addCleanup(p.stop)

    def test_simulation_really_breaks_unspecified_encoding(self):
        """Guard: without encoding="utf-8" the simulated Windows writes cp1252, which OpenSCAD cannot read."""
        p = self.dir / "t.scad"; p.write_text('import("C:/Users/Données/x.stl");')
        with self.assertRaises(UnicodeDecodeError): p.read_bytes().decode("utf-8")

    def test_meshscale_scad_with_accented_path(self):
        self._with_fake()
        out = meshscale.scale_stl_openscad(self.part, self.dir / "sortie é.stl", 110)
        self.assertEqual(len(read_stl(out)), 12)

    def test_engrave_scad_with_accented_path(self):
        s = deco.DecoSpec(kind="text", text="Léo", size_mm=30, u=30, v=30, depth_mm=0.8, mode="engrave")
        self._with_fake()
        r = deco.apply_decoration(self.part, s, hm=deco.build_heightmap(read_stl(self.part), "+z", 0.25))
        self.assertEqual(r.errors, []); self.assertEqual(len(r.triangles), 12)

    def test_openscad_stderr_decoded_as_utf8(self):
        self._with_fake(fail=True)
        with self.assertRaises(RuntimeError) as cm: openscad.render(self.dir / "absent é.scad", self.dir / "o.stl", {})
        self.assertNotIsInstance(cm.exception, UnicodeDecodeError); self.assertIn("Dossier é", str(cm.exception))

    def test_timeout_is_explained_in_french_and_english(self):
        with mock.patch.object(openscad, "find_openscad", return_value="openscad"), \
             mock.patch.object(openscad.subprocess, "run", side_effect=subprocess.TimeoutExpired("openscad", 5)):
            with self.assertRaises(RuntimeError) as cm: openscad.render("a.scad", "a.stl", {}, timeout=5)
        self.assertIn("n'a pas terminé en 5 s", str(cm.exception))
        sev, en, matched = messages.localize(str(cm.exception), "en"); self.assertTrue(matched); self.assertIn("did not finish within 5 s", en)

    def test_cache_and_thumbnail_stamp_in_accented_home(self):
        with mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": str(self.dir / "données"), "CUSTOMLAB_CACHE": "1"}):
            cache.put_axis(self.part, False, "+z", {"+z": 1.0}); self.assertEqual(cache.get_axis(self.part, False)["axis"], "+z")
            files = [self.part]; png = thumbs._png("phoenix_hand"); png.parent.mkdir(parents=True, exist_ok=True); png.write_bytes(b"x")
            png.with_suffix(".txt").write_text(thumbs._stamp(files), encoding="utf-8")
            self.assertEqual(png.with_suffix(".txt").read_text(encoding="utf-8"), thumbs._stamp(files))
            with mock.patch.object(thumbs, "sources", return_value=files): self.assertEqual(thumbs.cached("phoenix_hand"), png)


if __name__ == "__main__": unittest.main()
