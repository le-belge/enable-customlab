import os, subprocess, sys, tempfile, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from unittest import mock
from customlab import profiles, selftest

ROOT = Path(__file__).resolve().parent.parent


class SelfTest(unittest.TestCase):
    """Constat 8 : --selftest vérifie imports, profils, mise à l'échelle et export d'une pièce Phoenix incluse, code 0/1."""

    def test_passes_and_exports_scaled_phoenix_part(self):
        lines = []
        self.assertEqual(selftest.run(lines.append), 0, "\n".join(lines))
        self.assertTrue(any(l.startswith("[OK] export Phoenix") and "104.65pct.stl" in l for l in lines), lines)
        self.assertEqual(lines[-1], "selftest OK")

    def test_fails_with_exit_1_when_profiles_are_missing(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(profiles, "PROFILE_DIR", Path(d)):
            lines = []
            self.assertEqual(selftest.run(lines.append), 1)
        self.assertTrue(any(l.startswith("[ÉCHEC / FAILED] profils") for l in lines), lines)

    def test_report_file_written_even_without_stdout(self):         # windowed Windows build: sys.stdout is None
        with tempfile.TemporaryDirectory() as d, mock.patch.object(sys, "stdout", None):
            rep = Path(d) / "rapport.txt"
            self.assertEqual(selftest.main(["--selftest", "--report", str(rep)]), 0)
            self.assertIn("selftest OK", rep.read_text(encoding="utf-8"))

    def test_packaged_entry_point_dispatches_selftest_without_gui(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, PYTHONPATH=str(ROOT), QT_QPA_PLATFORM="offscreen", CUSTOMLAB_HOME=home)
            p = subprocess.run([sys.executable, str(ROOT / "packaging" / "entry.py"), "--selftest"], env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("selftest OK", p.stdout)


if __name__ == "__main__": unittest.main()
