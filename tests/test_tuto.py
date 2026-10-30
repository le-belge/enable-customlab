import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("CUSTOMLAB_SYNC", "1")
from PySide6.QtWidgets import QApplication
from customlab import gui, tuto_dialog

_app = QApplication.instance() or QApplication([])


class Tuto(unittest.TestCase):
    def test_menu_button_and_dialog_text(self):
        w = gui.MainWindow()
        self.assertEqual(w.m_help.title(), "Aide"); self.assertIn("Tuto", w.a_tuto.text()); self.assertIn("tuto", w.b_tuto.text())
        dlg = tuto_dialog.TutoDialog(w, "fr"); txt = dlg.view.toPlainText()
        for key in ("Phoenix", "Kinetic Hand", "Kinetic Arm", "Unlimbited Arm", "HandLen", "43"): self.assertIn(key, txt)


if __name__ == "__main__": unittest.main()
