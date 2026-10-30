"""Measure on a photo: a ruler (or tape) lies next to the limb; the user marks two points on the ruler, types the real distance between them,
then marks the two edges of the wrist. Pure geometry: result = measured pixel distance x (real ruler mm / ruler pixels).
The photo must be taken straight on, with the ruler in the same plane as the wrist: perspective is NOT corrected, so the value must be checked."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

TX = {"fr": {"title": "Mesurer sur une photo", "open": "Ouvrir une photo…", "reset": "Recommencer", "undo": "Annuler le dernier point", "zin": "Zoom +", "zout": "Zoom −", "zfit": "Ajuster", "zhelp": "Molette : zoom · clic droit + glisser : déplacer · glisser un point : l'ajuster · double-clic : tout voir.", "use": "Utiliser cette mesure", "close": "Fermer",
             "ruler_mm": "Distance réelle entre vos 2 repères :", "ref": "Objet de référence :", "ref_ruler": "Mètre / règle (je saisis la distance)", "ref_card": "Carte bancaire (largeur 85,6 mm)", "ref_a4w": "Feuille A4 (côté court 210 mm)", "ref_a4l": "Feuille A4 (côté long 297 mm)", "target": "Appliquer à :", "pick": "Choisir la photo",
             "s0": "1. Ouvrez une photo prise bien de face : le membre et un objet de taille connue (mètre, carte bancaire, feuille A4) posé juste à côté, dans le même plan.", "s1": "2. Cliquez le 1er repère de la référence (ex. graduation 10 cm du mètre, ou un coin de la carte).", "s2": "3. Cliquez le 2e repère (ex. 20 cm, ou l'autre coin de la carte) ; la distance réelle est réglée plus bas.",
             "s3": "4. Cliquez un bord du poignet, sur la ligne d'articulation.", "s4": "5. Cliquez l'autre bord du poignet.", "done": "Mesure : {v:.1f} mm. Vérifiez-la avec un mètre : la perspective n'est pas corrigée.",
             "warn": "Photo de face, mètre dans le même plan que le poignet, pas d'objectif très grand-angle. Valeur indicative : à contrôler."},
      "en": {"title": "Measure on a photo", "open": "Open a photo…", "reset": "Start over", "undo": "Undo the last point", "zin": "Zoom +", "zout": "Zoom −", "zfit": "Fit", "zhelp": "Wheel: zoom · right-drag: pan · drag a point: adjust it · double-click: fit.", "use": "Use this measure", "close": "Close",
             "ruler_mm": "Real distance between your 2 marks:", "ref": "Reference object:", "ref_ruler": "Ruler / tape (I type the distance)", "ref_card": "Bank card (width 85.6 mm)", "ref_a4w": "A4 sheet (short side 210 mm)", "ref_a4l": "A4 sheet (long side 297 mm)", "target": "Apply to:", "pick": "Choose the photo",
             "s0": "1. Open a photo taken straight on: the limb and an object of known size (ruler, bank card, A4 sheet) right beside it, in the same plane.", "s1": "2. Click the 1st mark of the reference (e.g. the 10 cm line, or one corner of the card).", "s2": "3. Click the 2nd mark (e.g. 20 cm, or the card's other corner); the real distance is set below.",
             "s3": "4. Click one edge of the wrist, on the wrist joint line.", "s4": "5. Click the other edge of the wrist.", "done": "Measure: {v:.1f} mm. Check it with a tape: perspective is not corrected.",
             "warn": "Straight-on photo, ruler in the same plane as the wrist, no strong wide-angle lens. Indicative value: to be checked."}}


def measure_mm(ruler_a, ruler_b, ruler_mm, edge_a, edge_b):
    """Real length of the segment edge_a-edge_b, given two ruler marks (pixel points) that are ruler_mm apart in reality."""
    px = math.dist(ruler_a, ruler_b)
    if px < 1 or ruler_mm <= 0: raise ValueError("ruler marks too close or distance not positive")
    return math.dist(edge_a, edge_b) * ruler_mm / px


class PhotoView(QWidget):
    """Photo with zoom (wheel, centred on the cursor) and pan (right/middle drag); a point can be dragged to be placed precisely."""
    def __init__(self):
        super().__init__(); self.setMinimumSize(560, 400); self.pix = None; self.pts = []; self.setCursor(Qt.CrossCursor)
        self.zoom = 1.0; self.pan = QPointF(0, 0); self._pan_from = None; self._drag_i = None; self.setMouseTracking(True)

    def _rect(self):
        if self.pix is None: return QRectF()
        w, h = self.pix.width(), self.pix.height(); s = min(self.width() / w, self.height() / h) * self.zoom
        return QRectF((self.width() - w * s) / 2 + self.pan.x(), (self.height() - h * s) / 2 + self.pan.y(), w * s, h * s)

    def to_img(self, p):
        r = self._rect(); return ((p.x() - r.x()) / r.width() * self.pix.width(), (p.y() - r.y()) / r.height() * self.pix.height())

    def to_px(self, q):
        r = self._rect(); return QPointF(r.x() + q[0] / self.pix.width() * r.width(), r.y() + q[1] / self.pix.height() * r.height())

    def reset_view(self): self.zoom = 1.0; self.pan = QPointF(0, 0); self.update()

    def zoom_at(self, pos, factor):
        if self.pix is None: return
        before = self.to_img(pos); self.zoom = max(1.0, min(40.0, self.zoom * factor)); after = self.to_px(before)
        self.pan = QPointF(self.pan.x() + pos.x() - after.x(), self.pan.y() + pos.y() - after.y())
        if self.zoom <= 1.0001: self.pan = QPointF(0, 0)
        self.update()

    def wheelEvent(self, e): self.zoom_at(e.position(), 1.2 ** (e.angleDelta().y() / 120.0)); e.accept()

    def mouseDoubleClickEvent(self, e): self.reset_view()

    def _near(self, pos):
        for i, q in enumerate(self.pts):
            if math.dist((pos.x(), pos.y()), (self.to_px(q).x(), self.to_px(q).y())) <= 9: return i
        return None

    def mousePressEvent(self, e):
        if self.pix is None: return
        if e.button() in (Qt.RightButton, Qt.MiddleButton): self._pan_from = e.position(); return
        i = self._near(e.position())
        if i is not None: self._drag_i = i; return                                        # grab an existing point to move it
        if len(self.pts) >= 4 or not self._rect().contains(e.position()): return
        self.pts.append(self.to_img(e.position())); self.changed(); self.update()

    def mouseMoveEvent(self, e):
        if self._pan_from is not None:
            d = e.position() - self._pan_from; self._pan_from = e.position(); self.pan = QPointF(self.pan.x() + d.x(), self.pan.y() + d.y()); self.update()
        elif self._drag_i is not None and (e.buttons() & Qt.LeftButton): self.pts[self._drag_i] = self.to_img(e.position()); self.changed(); self.update()

    def mouseReleaseEvent(self, e): self._pan_from = None; self._drag_i = None

    def changed(self): pass

    def paintEvent(self, _):
        p = QPainter(self); p.fillRect(self.rect(), QColor("#222")); p.setRenderHint(QPainter.Antialiasing)
        if self.pix is None: return
        p.save(); p.setClipRect(self.rect()); p.drawPixmap(self._rect().toRect(), self.pix); p.restore()
        for k, (a, b, col) in enumerate(((0, 1, "#18c43c"), (2, 3, "#ff3030"))):
            for i in (a, b):
                if i < len(self.pts): p.setPen(QPen(QColor(col), 2)); p.setBrush(QColor(col)); p.drawEllipse(self.to_px(self.pts[i]), 4, 4)
            if b < len(self.pts): p.setPen(QPen(QColor(col), 2)); p.drawLine(self.to_px(self.pts[a]), self.to_px(self.pts[b]))


class PhotoMeasureDialog(QDialog):
    """targets: [(label, field_id)]. After exec(): .result_value = (field_id, mm) or None."""
    def __init__(self, parent, lang, targets):
        super().__init__(parent); self.t = TX[lang]; self.setWindowTitle(self.t["title"]); self.resize(860, 700); self.result_value = None
        v = QVBoxLayout(self); self.step = QLabel(); self.step.setWordWrap(True); v.addWidget(self.step)
        w = QLabel(self.t["warn"]); w.setWordWrap(True); w.setStyleSheet("color:#8a4b00;font-size:11px"); v.addWidget(w)
        self.view = PhotoView(); self.view.changed = self.update_state; hz = QLabel(self.t["zhelp"]); hz.setStyleSheet("color:#5b6b78;font-size:11px"); v.addWidget(hz); v.addWidget(self.view, 1)
        row = QHBoxLayout(); b_open = QPushButton(self.t["open"]); b_open.clicked.connect(self.open_photo)
        self.b_undo = QPushButton(self.t["undo"]); self.b_undo.clicked.connect(self.undo); b_reset = QPushButton(self.t["reset"]); b_reset.clicked.connect(self.reset)
        bz1 = QPushButton(self.t["zin"]); bz2 = QPushButton(self.t["zout"]); bz3 = QPushButton(self.t["zfit"])
        bz1.clicked.connect(lambda: self.view.zoom_at(QPointF(self.view.width() / 2, self.view.height() / 2), 1.5)); bz2.clicked.connect(lambda: self.view.zoom_at(QPointF(self.view.width() / 2, self.view.height() / 2), 1 / 1.5)); bz3.clicked.connect(self.view.reset_view)
        for x in (b_open, self.b_undo, b_reset, bz1, bz2, bz3): row.addWidget(x)
        row.addStretch(1); v.addLayout(row)
        row2 = QHBoxLayout(); row2.addWidget(QLabel(self.t["ref"])); self.ref = QComboBox()
        for k, mm in (("ref_ruler", None), ("ref_card", 85.6), ("ref_a4w", 210.0), ("ref_a4l", 297.0)): self.ref.addItem(self.t[k], mm)
        self.ref.currentIndexChanged.connect(self._ref_changed); row2.addWidget(self.ref); row2.addWidget(QLabel(self.t["ruler_mm"])); self.ruler = QDoubleSpinBox(); self.ruler.setRange(1, 5000); self.ruler.setDecimals(1); self.ruler.setValue(100.0); self.ruler.setSuffix(" mm")
        self.ruler.valueChanged.connect(self.update_state); row2.addWidget(self.ruler); row2.addStretch(1); v.addLayout(row2)
        row3 = QHBoxLayout(); row3.addWidget(QLabel(self.t["target"])); self.target = QComboBox(); [self.target.addItem(l, i) for l, i in targets]; row3.addWidget(self.target); row3.addStretch(1)
        self.result = QLabel(); self.result.setStyleSheet("font-weight:700"); row3.addWidget(self.result)
        self.b_use = QPushButton(self.t["use"]); self.b_use.setObjectName("primary"); self.b_use.setEnabled(False); self.b_use.clicked.connect(self.use)
        b_close = QPushButton(self.t["close"]); b_close.clicked.connect(self.reject); row3.addWidget(self.b_use); row3.addWidget(b_close); v.addLayout(row3)
        self.update_state()

    def _ref_changed(self, *_):
        mm = self.ref.currentData()
        if mm: self.ruler.setValue(mm)
        self.ruler.setEnabled(mm is None); self.update_state()

    def open_photo(self, path=None):
        if not path: path, _ = QFileDialog.getOpenFileName(self, self.t["pick"], "", "Images (*.png *.jpg *.jpeg *.heic *.bmp)")
        if not path: return
        pix = QPixmap(path)
        if pix.isNull(): return
        self.view.pix = pix; self.reset()

    def reset(self): self.view.pts = []; self.view.reset_view(); self.update_state()

    def undo(self):
        if self.view.pts: self.view.pts.pop()
        self.view.update(); self.update_state()

    def value(self):
        p = self.view.pts
        return measure_mm(p[0], p[1], self.ruler.value(), p[2], p[3]) if len(p) == 4 else None

    def update_state(self):
        n = len(self.view.pts) if self.view.pix is not None else -1
        self.step.setText("" if n >= 4 else self.t["s0"] if n < 0 else self.t[f"s{n + 1}"])
        self.b_undo.setEnabled(n > 0)
        val = self.value() if n == 4 else None
        self.result.setText(self.t["done"].format(v=val) if val else ""); self.b_use.setEnabled(val is not None)

    def use(self):
        val = self.value()
        if val: self.result_value = (self.target.currentData(), round(val, 1)); self.accept()
