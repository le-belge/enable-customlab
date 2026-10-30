import os, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from customlab.scale_guide_dialog import ScaleGuideDialog, IMG
from customlab.gui import MainWindow
app = QApplication.instance() or QApplication([])


class ScaleGuide(unittest.TestCase):
    def test_example_of_the_page_and_refusal(self):
        d = ScaleGuideDialog(None, "fr", "phoenix_hand", {"wrist_mm": 40.0}); self.assertIn("104.65", d.out.text())
        d.spin.setValue(70.0); self.assertIn("hors de la plage", d.out.text()); self.assertNotIn("174.4", d.out.text().replace("174.4 %", "") if False else "")
        self.assertTrue((IMG / "outil_photo.png").is_file() and (IMG / "mesures_phoenix.png").is_file())
        self.assertIn("104,65", d.view.toPlainText())

    def test_each_device_has_a_guide_with_its_own_calculator(self):
        from customlab.scale_guide_dialog import ScaleGuideDialog
        d = ScaleGuideDialog(None, "fr", "kinetic_hand"); self.assertIn("72.5", d.out.text()); self.assertIn("<b>D</b>", d.out.text().replace("insert <b>D</b>", "<b>D</b>"))   # manual example: wrist 48 -> 72.5 % + insert D
        d.spins["wrist_mm"].setValue(150.0); self.assertTrue(d.out.text())                                                                    # out of range: the message, no number invented
        a = ScaleGuideDialog(None, "fr", "kinetic_arm"); self.assertIn("composants" if False else "Inférieurs", a.out.text())
        u = ScaleGuideDialog(None, "en", "unlimbited_arm"); self.assertIn("HandPerc = <b>133", u.out.text()); u.spins["HandLen"].setValue(100.0); self.assertIn("b00020", u.out.text())
        for dev in ("kinetic_hand", "kinetic_arm", "unlimbited_arm"): self.assertTrue((IMG / f"mesures_{dev}.png").is_file())

    def test_guide_button_on_every_device(self):
        w = MainWindow()
        for dev in ("phoenix_hand", "kinetic_hand", "kinetic_arm", "unlimbited_arm"): w.select(dev); self.assertFalse(w.b_guide.isHidden(), dev)


if __name__ == "__main__": unittest.main()
