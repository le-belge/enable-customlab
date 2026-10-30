"""Look & feel of CustomLab: e-NABLE France colours (read from e-nable.fr's stylesheet, 2026-10-29) and gentle animations.

The e-Nable France logo (assets/enable_france_logo.png, see LOGO_NOTICE.txt) is shown in the header. Animations are skipped when CUSTOMLAB_SYNC=1 (tests) or when
the platform reports reduced motion is not available, so that nothing ever waits on a timer.
"""
import os
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

NAVY = "#0b314d"        # e-nable.fr: titles, footer, text on light
SKY = "#8dc9e5"         # accent / selection
TEAL = "#68d4c4"
CYAN = "#25bec3"
YELLOW = "#fec327"
ORANGE = "#f5842c"
PURPLE = "#734fa1"
RED = "#dc3545"
FRENCH_BLUE, FRENCH_RED = "#1d3f8f", "#d6202a"       # tricolour stripe, as in the association's emblem
TINT = "#f3f9fc"        # page background (very light sky)
LINE = "#d5e6ef"
TEXT = "#212529"
MUTED = "#5b6b78"
OK = "#1f8a70"
WARN = "#b25a00"

STATUS = {"verified": OK, "experimental": ORANGE, "unavailable": RED}
FONT_STACK = '"Lato", "Helvetica Neue", "Segoe UI", "Roboto", "Arial"'


def animated():
    return os.environ.get("CUSTOMLAB_SYNC") != "1" and os.environ.get("QT_QPA_PLATFORM") != "offscreen"


CHECK = (Path(__file__).parent / "assets" / "check.svg").as_posix()
LOGO = Path(__file__).parent / "assets" / "enable_france_logo.png"
QSS = f"""
* {{ font-family: {FONT_STACK}; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {TINT}; }}
QWidget#page {{ background: transparent; }}
QMenuBar {{ background: {NAVY}; color: white; padding: 2px 6px; }}
QMenuBar::item {{ background: transparent; color: white; padding: 5px 10px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: rgba(141,201,229,0.28); }}
QMenu {{ background: white; border: 1px solid {LINE}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 5px; }}
QMenu::item:selected {{ background: {SKY}; color: {NAVY}; }}
QLabel {{ background: transparent; }}
QFrame#card {{ background: white; border: 1px solid {LINE}; border-radius: 14px; }}
QFrame#card:hover {{ border: 1px solid {SKY}; }}
QPushButton {{ background: white; color: {NAVY}; border: 1px solid {SKY}; border-radius: 10px; padding: 8px 18px; font-weight: 600; }}
QPushButton:hover {{ background: #e6f3f9; border-color: {CYAN}; }}
QPushButton:pressed {{ background: {SKY}; }}
QPushButton:disabled {{ background: #eef3f6; color: #98a8b3; border-color: {LINE}; }}
QPushButton#primary {{ background: {NAVY}; color: white; border: 1px solid {NAVY}; }}
QPushButton#primary:hover {{ background: #14486f; }}
QPushButton#primary:pressed {{ background: #07202f; }}
QPushButton#primary:disabled {{ background: #9fb3c0; border-color: #9fb3c0; color: white; }}
QPushButton#chip {{ padding: 4px 8px; border-radius: 8px; font-weight: 500; }}
QPushButton#lang {{ background: transparent; color: white; border: 1px solid rgba(255,255,255,0.45); padding: 5px 14px; }}
QPushButton#lang:hover {{ background: rgba(141,201,229,0.28); }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox {{ background: white; border: 1px solid {LINE}; border-radius: 8px; padding: 5px 8px; selection-background-color: {SKY}; selection-color: {NAVY}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 1.5px solid {CYAN}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: white; border: 1px solid {LINE}; selection-background-color: {SKY}; selection-color: {NAVY}; outline: 0; }}
QTextEdit, QPlainTextEdit {{ background: white; border: 1px solid {LINE}; border-radius: 10px; padding: 6px; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid {SKY}; background: white; }}
QCheckBox::indicator:checked {{ background: {CYAN}; border-color: {CYAN}; image: url({CHECK}); }}
QSlider::groove:horizontal {{ height: 5px; background: {LINE}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {NAVY}; width: 16px; margin: -6px 0; border-radius: 8px; }}
QSlider::sub-page:horizontal {{ background: {CYAN}; border-radius: 2px; }}
QProgressBar {{ background: {LINE}; border: none; border-radius: 4px; height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {CYAN}; border-radius: 4px; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SKY}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {CYAN}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SKY}; border-radius: 4px; min-width: 28px; }}
QToolTip {{ background: {NAVY}; color: white; border: none; padding: 6px 8px; }}
QTableView, QTableWidget, QListWidget {{ background: white; border: 1px solid {LINE}; border-radius: 10px; gridline-color: {LINE}; selection-background-color: {SKY}; selection-color: {NAVY}; }}
QHeaderView::section {{ background: {TINT}; border: none; border-bottom: 1px solid {LINE}; padding: 6px; font-weight: 600; color: {NAVY}; }}
QGroupBox {{ border: 1px solid {LINE}; border-radius: 10px; margin-top: 12px; padding-top: 10px; background: white; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {NAVY}; font-weight: 600; }}
"""


def apply(app):
    """Global style sheet + base font. Safe to call once per QApplication."""
    f = QFont(); f.setFamilies(["Lato", "Helvetica Neue", "Segoe UI", "Roboto", "Arial"]); f.setPointSizeF(max(app.font().pointSizeF(), 10.5)); app.setFont(f)
    app.setStyleSheet(QSS)


def fade_in(widget, ms=220):
    """Soft cross-fade when a page appears (no-op in tests)."""
    if not animated(): return
    eff = QGraphicsOpacityEffect(widget); widget.setGraphicsEffect(eff)
    a = QPropertyAnimation(eff, b"opacity", widget); a.setDuration(ms); a.setStartValue(0.0); a.setEndValue(1.0); a.setEasingCurve(QEasingCurve.OutCubic)
    a.finished.connect(lambda: widget.setGraphicsEffect(None)); a.start(QPropertyAnimation.DeleteWhenStopped); widget._fade = a


class _Hover(QObject):
    """Shadow that blooms smoothly under a card while the mouse is over it."""
    def __init__(self, card):
        super().__init__(card); self.card = card; self.fx = QGraphicsDropShadowEffect(card); self.fx.setBlurRadius(0); self.fx.setOffset(0, 3); self.fx.setColor(QColor(11, 49, 77, 0))
        card.setGraphicsEffect(self.fx); card.installEventFilter(self)
        self.anim = QVariantAnimation(self); self.anim.setDuration(180); self.anim.setEasingCurve(QEasingCurve.OutCubic); self.anim.valueChanged.connect(self._set)

    def _set(self, v):
        v = float(v); self.fx.setBlurRadius(v); self.fx.setColor(QColor(11, 49, 77, int(70 * min(v, 26.0) / 26.0)))

    def eventFilter(self, obj, ev):
        if animated() and ev.type() in (QEvent.Enter, QEvent.Leave):
            self.anim.stop(); self.anim.setStartValue(self.fx.blurRadius()); self.anim.setEndValue(26.0 if ev.type() == QEvent.Enter else 0.0); self.anim.start()
        return False


def card(layout_cls=None):
    """A white rounded panel with a hover shadow."""
    f = QFrame(); f.setObjectName("card"); _Hover(f); return f


class StepBar(QWidget):
    """Four dots joined by a line; the current step is highlighted and the progress line glides to it."""
    def __init__(self, n=4):
        super().__init__(); self.n = n; self.cur = 0; self.shown = 0.0; self.setFixedHeight(26); self.setMinimumWidth(150)
        self.anim = QVariantAnimation(self); self.anim.setDuration(260); self.anim.setEasingCurve(QEasingCurve.InOutCubic); self.anim.valueChanged.connect(self._tick)

    def _tick(self, v): self.shown = float(v); self.update()

    def set_step(self, i):
        self.cur = i
        if animated(): self.anim.stop(); self.anim.setStartValue(self.shown); self.anim.setEndValue(float(i)); self.anim.start()
        else: self.shown = float(i); self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); w, h = self.width() - 24, self.height(); x0 = 12; gap = w / (self.n - 1); cy = h / 2
        p.setPen(QColor(255, 255, 255, 70)); p.drawLine(int(x0), int(cy), int(x0 + w), int(cy))
        p.setPen(QColor(SKY)); p.drawLine(int(x0), int(cy), int(x0 + gap * self.shown), int(cy))
        for i in range(self.n):
            x = x0 + gap * i; done = i <= self.shown + 0.01; cur = i == self.cur
            p.setPen(Qt.NoPen); p.setBrush(QColor(YELLOW) if cur else QColor(SKY) if done else QColor(NAVY).lighter(160))
            r = 7 if cur else 5; p.drawEllipse(int(x - r), int(cy - r), 2 * r, 2 * r)


class Header(QFrame):
    """Navy band with the app name, tricolour hairline, step name, step dots and the language button."""
    def __init__(self, step_label, lang_button):
        super().__init__(); self.setObjectName("header"); self.setStyleSheet(f"QFrame#header {{ background: {NAVY}; border-radius: 14px; }}")
        lay = QHBoxLayout(self); lay.setContentsMargins(18, 10, 14, 10); lay.setSpacing(14)
        logo = QLabel(); logo.setStyleSheet("background:white;border-radius:23px;padding:3px"); pm = QPixmap(str(LOGO))
        if not pm.isNull(): logo.setPixmap(pm.scaledToHeight(40, Qt.SmoothTransformation)); lay.addWidget(logo)
        brand = QLabel("e-NABLE <span style='color:%s'>CustomLab</span>" % SKY); brand.setStyleSheet("color:white;font-size:17px;font-weight:700;background:transparent")
        stripe = QWidget(); stripe.setFixedSize(3, 22); stripe.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {FRENCH_BLUE}, stop:0.34 {FRENCH_BLUE}, stop:0.34 white, stop:0.67 white, stop:0.67 {FRENCH_RED}, stop:1 {FRENCH_RED}); border-radius:1px")
        step_label.setStyleSheet("color:white;font-size:15px;font-weight:600;background:transparent")
        self.steps = StepBar(); lang_button.setObjectName("lang")
        for x in (brand, stripe): lay.addWidget(x)
        lay.addWidget(step_label, 1); lay.addWidget(self.steps); lay.addWidget(lang_button)
