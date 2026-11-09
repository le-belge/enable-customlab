"""Windows dark mode / high display scale: the light design must stay readable and the measures page must scroll instead of squashing its rows."""
import os, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["CUSTOMLAB_SYNC"] = "1"
import tempfile
from unittest import mock
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QScrollArea
from customlab import theme
app = QApplication.instance() or QApplication([])


class ForceLight(unittest.TestCase):
    def setUp(self): self.old_pal = QPalette(app.palette()); self.old_style = app.style().objectName()

    def tearDown(self): app.setStyle(self.old_style); app.setPalette(self.old_pal)

    def test_dark_system_palette_becomes_light(self):
        dark = QPalette()
        for role, col in ((QPalette.Window, "#202020"), (QPalette.Base, "#1c1c1c"), (QPalette.WindowText, "#ffffff"), (QPalette.Text, "#ffffff")): dark.setColor(role, QColor(col))
        app.setPalette(dark); self.assertLess(app.palette().color(QPalette.Window).lightness(), 128)
        theme.force_light(app)
        self.assertGreaterEqual(app.palette().color(QPalette.Window).lightness(), 128)
        self.assertLess(app.palette().color(QPalette.Text).lightness(), 128)          # dark text on the light background

    def test_light_palette_untouched(self):
        light = QPalette(); light.setColor(QPalette.Window, QColor("#f3f9fc")); app.setPalette(light); style = app.style().objectName()
        theme.force_light(app); self.assertEqual(app.style().objectName(), style)

    def test_scroll_areas_are_transparent_in_the_style_sheet(self):
        self.assertIn("QScrollArea {", theme.QSS.replace("{{", "{")); self.assertIn("background: transparent", theme.QSS)


class MeasuresPageScrolls(unittest.TestCase):
    def test_measures_page_is_scrollable(self):
        from customlab.gui import MainWindow
        with mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": tempfile.mkdtemp()}):
            w = MainWindow(); page = w.stack.widget(1)
            self.assertIsInstance(page, QScrollArea); self.assertTrue(page.widgetResizable())
