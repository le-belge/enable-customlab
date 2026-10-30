"""Génère les images de l'assistant d'installation Windows (BMP) à partir du logo e-NABLE France : PYTHONPATH=. .venv/bin/python packaging/make_installer_images.py"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
app = QGuiApplication([])
here = Path(__file__).parent; logo = QImage(str(here.parent / "customlab" / "assets" / "enable_france_logo.png"))
NAVY = QColor("#0b314d")


def big(path):
    im = QImage(164, 314, QImage.Format_RGB32); im.fill(Qt.white); p = QPainter(im); p.setRenderHint(QPainter.SmoothPixmapTransform)
    lg = logo.scaledToWidth(120, Qt.SmoothTransformation); p.drawImage((164 - lg.width()) // 2, 40, lg)
    p.setPen(NAVY); f = QFont("Helvetica", 12); f.setBold(True); p.setFont(f); p.drawText(QRect(0, 190, 164, 24), Qt.AlignCenter, "e-NABLE CustomLab")
    f = QFont("Helvetica", 9); p.setFont(f); p.drawText(QRect(0, 216, 164, 20), Qt.AlignCenter, "par e-NABLE France")
    p.fillRect(0, 306, 55, 8, QColor("#2d5aa0")); p.fillRect(55, 306, 54, 8, Qt.white); p.fillRect(109, 306, 55, 8, QColor("#d62d2d")); p.end(); im.save(str(path), "BMP")


def small(path):
    im = QImage(55, 55, QImage.Format_RGB32); im.fill(Qt.white); p = QPainter(im); p.setRenderHint(QPainter.SmoothPixmapTransform)
    lg = logo.scaledToHeight(47, Qt.SmoothTransformation); p.drawImage((55 - lg.width()) // 2, 4, lg); p.end(); im.save(str(path), "BMP")


big(here / "wizard_large.bmp"); small(here / "wizard_small.bmp"); print("ok")
