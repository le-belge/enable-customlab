"""Windows + Qt offscreen (tests, command line, --selftest): Qt must be pointed at C:\\Windows\\Fonts, else text is drawn as empty boxes."""
import os
import unittest
from unittest import mock

import customlab


class WindowsOffscreenFonts(unittest.TestCase):
    def run_with(self, platform, env):
        with mock.patch.object(customlab._sys, "platform", platform), mock.patch.dict(os.environ, env, clear=True):
            customlab.windows_offscreen_fonts(); return os.environ.get("QT_QPA_FONTDIR")

    def test_windows_offscreen_uses_the_system_fonts(self):
        self.assertEqual(self.run_with("win32", {"QT_QPA_PLATFORM": "offscreen", "WINDIR": r"D:\Win"}), os.path.join(r"D:\Win", "Fonts"))

    def test_untouched_with_a_window_or_off_windows_or_when_set(self):
        self.assertIsNone(self.run_with("win32", {}))                                        # normal app with windows
        self.assertIsNone(self.run_with("linux", {"QT_QPA_PLATFORM": "offscreen"}))
        self.assertEqual(self.run_with("win32", {"QT_QPA_PLATFORM": "offscreen", "QT_QPA_FONTDIR": "X"}), "X")


if __name__ == "__main__":
    unittest.main()
