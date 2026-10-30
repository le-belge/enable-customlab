"""Regenerates the screenshots used by the in-app "mettre à l'échelle" guide (customlab/assets/guide/*.png) from the real windows (offscreen).
Run: PYTHONPATH=. .venv/bin/python packaging/make_guide_images.py   (images are illustrations: the 'photo' is drawn, not a real person)."""
import os, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["CUSTOMLAB_SYNC"] = "1"; os.environ["CUSTOMLAB_HOME"] = tempfile.mkdtemp()
from pathlib import Path
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from customlab.gui import MainWindow
from customlab.photo_measure import PhotoMeasureDialog

OUT = Path(__file__).resolve().parent.parent / "customlab" / "assets" / "guide"; OUT.mkdir(parents=True, exist_ok=True)
app = QApplication([])


def fake_photo(path):
    """Drawn illustration: a hand lying flat (wrist 40 units wide) and a bank card beside it."""
    px = QPixmap(900, 600); px.fill(QColor("#d9c7a8")); p = QPainter(px); p.setRenderHint(QPainter.Antialiasing)
    skin, edge = QColor("#f1d3b8"), QColor("#8a6a50"); p.setPen(edge); p.setBrush(skin)
    p.drawRoundedRect(QRectF(317, 330, 126, 300), 20, 20)                                    # forearm / wrist (126 px = 40 mm at 0.317 mm/px)
    p.drawRoundedRect(QRectF(280, 130, 200, 210), 40, 40)                                    # palm
    for i, (x, h) in enumerate(((282, 120), (326, 150), (372, 160), (418, 140))): p.drawRoundedRect(QRectF(x, 130 - h + 20, 40, h), 20, 20)
    p.setBrush(QColor("#2c5aa0")); p.setPen(QColor("#1b3a70")); p.drawRoundedRect(QRectF(560, 330, 270, 170), 12, 12)           # card 85.6 mm -> 270 px
    p.setPen(QColor("white")); f = QFont(); f.setPixelSize(22); p.setFont(f); p.drawText(QRectF(560, 330, 270, 170), Qt.AlignCenter, "CARTE 85,6 mm")
    p.end(); px.save(str(path))


w = MainWindow(); w.resize(1180, 640); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(40.0); w.show(); app.processEvents(); w.go(1); app.processEvents()
w.grab().save(str(OUT / "mesures_phoenix.png"))
ph = OUT / "photo_exemple.png"; fake_photo(ph)
d = PhotoMeasureDialog(w, "fr", [("Largeur du poignet (mm)", "wrist_mm")]); d.resize(900, 760); d.show(); d.open_photo(str(ph)); app.processEvents()
d.ref.setCurrentIndex(1)                                                                      # bank card
v = d.view
for ix, iy in ((560, 415), (830, 415), (317, 560), (443, 560)): v.pts.append((float(ix), float(iy)))
v.update(); d.update_state(); app.processEvents(); d.grab().save(str(OUT / "outil_photo.png"))
for dev, vals in (("kinetic_hand", {"wrist_mm": 48.0, "palm_mm": 40.0}), ("kinetic_arm", {"hand_mm": 180.0, "elbow_mm": 60.0, "resid_mm": 150.0}), ("unlimbited_arm", {"HandLen": 180.0, "ForearmLen": 220.0, "BicepCircum": 250.0})):
    w.select(dev)
    for k, val in vals.items(): w.fields[k].setValue(val)
    w.go(1); app.processEvents(); app.sendPostedEvents(None, QEvent.DeferredDelete); app.processEvents(); w.grab().save(str(OUT / f"mesures_{dev}.png"))
print("ok", sorted(p.name for p in OUT.iterdir()))
