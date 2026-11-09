"""The version shown in error reports and the self-test matches the one of the installers."""
import re
import unittest
from pathlib import Path

import customlab

ROOT = Path(__file__).resolve().parent.parent


class VersionTest(unittest.TestCase):
    def test_version_matches_packaging(self):
        spec = re.search(r'VERSION\s*=\s*"([^"]+)"', (ROOT / "packaging" / "customlab.spec").read_text(encoding="utf-8")).group(1)
        iss = re.search(r"AppVersion=(\S+)", (ROOT / "packaging" / "installer.iss").read_text(encoding="utf-8")).group(1)
        self.assertEqual(customlab.__version__, spec)
        self.assertEqual(customlab.__version__, iss)


class ProfileNoticeTest(unittest.TestCase):
    def test_every_profile_has_an_english_notice(self):
        import json
        for f in sorted((ROOT / "customlab" / "profiles").glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("notice"): self.assertTrue(d.get("notice_en"), f"{f.name}: notice_en missing")


if __name__ == "__main__":
    unittest.main()
