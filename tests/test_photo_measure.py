import os, tempfile, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication
from customlab import photo_measure as pm
from customlab.gui import MainWindow
app = QApplication.instance() or QApplication([])


class PhotoMeasure(unittest.TestCase):
    def test_math(self):
        self.assertAlmostEqual(pm.measure_mm((0, 0), (200, 0), 100, (10, 5), (10, 145)), 70.0)       # 200 px = 100 mm -> 140 px = 70 mm
        with self.assertRaises(ValueError): pm.measure_mm((0, 0), (0, 0), 100, (0, 0), (5, 5))

    def test_dialog_four_clicks_then_value_goes_to_the_field(self):
        w = MainWindow(); w.select("phoenix_hand"); self.assertFalse(w.b_photo.isHidden())
        d = pm.PhotoMeasureDialog(w, "fr", [("Poignet", "wrist_mm")])
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "p.png"); px = QPixmap(400, 300); px.fill(QColor("white")); px.save(f); d.open_photo(f)
        d.resize(600, 500); d.view.resize(400, 300); r = d.view._rect()
        for ix, iy in ((50, 50), (250, 50), (100, 200), (240, 200)):                                     # ruler 200 px = 100 mm ; wrist 140 px = 70 mm
            d.view.mousePressEvent(type("E", (), {"position": lambda s, p=d.view.to_px((ix, iy)): p, "button": lambda s: Qt.LeftButton})())
        self.assertEqual(len(d.view.pts), 4); self.assertAlmostEqual(d.value(), 70.0, delta=0.5); d.use()
        self.assertEqual(d.result_value[0], "wrist_mm"); self.assertAlmostEqual(d.result_value[1], 70.0, delta=0.5)


if __name__ == "__main__": unittest.main()


class PhotoZoom(unittest.TestCase):
    def test_zoom_keeps_the_point_under_the_cursor_and_points_stay_in_image_coordinates(self):
        v = pm.PhotoView(); v.resize(600, 400); px = QPixmap(400, 300); px.fill(QColor("white")); v.pix = px
        cur = QPointF(300, 200); before = v.to_img(cur); v.zoom_at(cur, 4.0)
        after = v.to_img(cur); self.assertAlmostEqual(before[0], after[0], places=3); self.assertAlmostEqual(before[1], after[1], places=3); self.assertAlmostEqual(v.zoom, 4.0)
        v.pts = [v.to_img(QPointF(310, 205))]; q = v.pts[0]; v.zoom_at(cur, 1.5); self.assertEqual(v.pts[0], q)      # the stored point does not move with the view
        v.reset_view(); self.assertEqual(v.zoom, 1.0)
        v.pts = [(100.0, 100.0)]; self.assertEqual(v._near(v.to_px((103.0, 100.0))), 0)
