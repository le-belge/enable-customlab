"""Personalisation page: choose a real STL part, place text/SVG/image on it, mark forbidden zones."""
import json
import os
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, QObject, QPointF, QRect, QRectF, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QIcon, QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (QStyledItemDelegate, QListView, QProgressBar, QScrollArea, QSlider, QFrame, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox, QFileDialog, QFontComboBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget)

from . import deco
from . import cache, library, thumbs
from .licenseinfo import read_license_info
from .meshio import read_stl
from .glview import make_view

SHOW_CAMO = False        # camouflage mode is built and tested (docs/CAMOUFLAGE.md) but hidden: the user dropped the idea
DRAFT_RES = 0.25         # mm: grid used while placing the motif (finer grids are only built for the result/export)

TX = {
 "fr": {"part": "Ou choisir un autre fichier STL…", "lib": "— Choisir une pièce —", "none": "Aucune pièce chargée. La décoration s'applique à la taille d'origine du STL ; l'original n'est jamais modifié.",
        "axis": "Vue (axe)", "mode": "Mode", "relief": "Relief", "engrave": "Gravure", "inlay": "Incrustation (affleurant)", "kind": "Contenu", "camo": "Camouflage (toute la pièce)", "camo_style": "Camouflage", "camo_seed": "Variante (n°)", "camo_scale": "Taille des taches", "camo_fr": "Français (style Centre Europe)", "camo_winter": "Hiver (neige)", "camo_all": "Appliquer le camouflage à plusieurs pièces…", "camo_base": "Couleur de la pièce conseillée : {c} (filament 1).", "text": "Texte", "svg": "SVG", "image": "Image (PNG/JPEG)",
        "txt": "Texte", "file": "Fichier…", "size": "Taille (mm)", "rot": "Rotation (°)", "u": "Position u (mm)", "v": "Position v (mm)", "depth": "Profondeur (mm)",
        "zone": "Tracer une zone interdite", "clear": "Effacer les zones", "bold": "Gras", "inv": "Inverser (image)", "white": "Blanc = vide", "thr": "Seuil image (0-255)", "ncol": "Couleurs (1 = une pièce)", "qual": "Qualité (finesse)",
        "warn": "EXPÉRIMENTAL : les zones fonctionnelles (articulations, trous de broches, passages de câbles, contact avec la peau) ne sont PAS détectées. Tracez les zones à protéger et faites relire le résultat par un bénévole compétent.",
        "lic": "Licence de la source", "unknown": "Provenance/licence INCONNUES — ne pas redistribuer.", "nc": "usage NON commercial",
        "busy": "⏳ Calcul en cours…", "analysing": "⏳ Analyse de la pièce (choix de la face)…", "axis_auto": "Vue choisie automatiquement : {axis} (face la plus plane). Vous pouvez la changer dans « Vue (axe) ».", "gen": "Générer la pièce depuis le SCAD officiel", "gen_ready": "Pièce « {part} » à générer pour ces mesures", "gen_busy": "⏳ Génération de « {part} » par OpenSCAD en cours… (ne fermez pas la fenêtre)", "gen_done": "✓ Pièce « {part} » générée pour ces mesures", "gen_need": "Saisissez d'abord des mesures valides (étape 2).", "gen_noscad": "Fichier SCAD officiel introuvable : placez-le dans sources/unlimbited_arm/part2/files/ (voir docs/UNLIMBITED_ARM.md).", "gen_fail": "Échec de la génération : {err}", "preparing": "⏳ Préparation de la pièce…", "hint": "Cliquez dans la vue pour placer le motif ; en mode zone, glissez un rectangle.", "spot_center": "Centre", "spot_top": "Haut", "spot_bottom": "Bas", "spot_left": "Gauche", "spot_right": "Droite", "spots": "Placer", "pad": "Déplacer / pivoter la vue", "thick": "Épaissir les traits fins (< 0,8 mm)", "model_dims": "Taille standard (100 %) : {x:.1f} × {y:.1f} × {z:.1f} mm", "model_final": "taille finale à {pct:g} % : {x:.1f} × {y:.1f} × {z:.1f} mm (le motif suit l'échelle)", "hint2": "Glisser : déplacer · molette : taille · Maj+molette : rotation · Ctrl+molette : zoom · clic droit : déplacer la vue · flèches : ajuster", "prot": "Marge auto autour des trous", "inl_off": "Dépassement de l'incrustation (mm)"},
 "en": {"part": "Or choose another STL file…", "lib": "— Choose a part —", "none": "No part loaded. Decoration is applied at the STL's original size; the original is never modified.",
        "axis": "View (axis)", "mode": "Mode", "relief": "Relief", "engrave": "Engrave", "inlay": "Inlay (flush)", "kind": "Content", "camo": "Camouflage (whole part)", "camo_style": "Camouflage", "camo_seed": "Variant (no.)", "camo_scale": "Patch size", "camo_fr": "French (Central Europe style)", "camo_winter": "Winter (snow)", "camo_all": "Apply the camouflage to several parts…", "camo_base": "Suggested part colour: {c} (filament 1).", "text": "Text", "svg": "SVG", "image": "Image (PNG/JPEG)",
        "txt": "Text", "file": "File…", "size": "Size (mm)", "rot": "Rotation (°)", "u": "Position u (mm)", "v": "Position v (mm)", "depth": "Depth (mm)",
        "zone": "Draw a forbidden zone", "clear": "Clear zones", "bold": "Bold", "inv": "Invert (image)", "white": "White = empty", "thr": "Image threshold (0-255)", "ncol": "Colours (1 = one piece)", "qual": "Quality (resolution)",
        "warn": "EXPERIMENTAL: functional zones (joints, pin holes, cable channels, skin contact) are NOT detected. Draw the zones to protect and have a qualified volunteer review the result.",
        "lic": "Source licence", "unknown": "Provenance/licence UNKNOWN — do not redistribute.", "nc": "NON-commercial use",
        "busy": "⏳ Computing…", "analysing": "⏳ Analysing the part (choosing the face)…", "axis_auto": "View chosen automatically: {axis} (flattest face). You can change it in “View (axis)”.", "gen": "Generate the part from the official SCAD", "gen_ready": "Part “{part}” to generate for these measures", "gen_busy": "⏳ Generating “{part}” with OpenSCAD… (do not close the window)", "gen_done": "✓ Part “{part}” generated for these measures", "gen_need": "Enter valid measures first (step 2).", "gen_noscad": "Official SCAD file not found: place it in sources/unlimbited_arm/part2/files/ (see docs/UNLIMBITED_ARM.md).", "gen_fail": "Generation failed: {err}", "preparing": "⏳ Preparing the part…", "hint": "Click in the view to place the motif; in zone mode, drag a rectangle.", "spot_center": "Centre", "spot_top": "Top", "spot_bottom": "Bottom", "spot_left": "Left", "spot_right": "Right", "spots": "Place", "pad": "Move / turn the view", "thick": "Thicken thin strokes (< 0.8 mm)", "model_dims": "Standard size (100 %): {x:.1f} × {y:.1f} × {z:.1f} mm", "model_final": "final size at {pct:g} %: {x:.1f} × {y:.1f} × {z:.1f} mm (the motif follows the scale)", "hint2": "Drag: move · wheel: size · Shift+wheel: rotate · Ctrl+wheel: zoom · right-drag: pan · arrows: nudge", "prot": "Auto margin around holes", "inl_off": "Inlay protrusion (mm)"},
}
TX["fr"].update({"motifs": "Motifs", "motif_add": "＋ Ajouter un motif", "motif_del": "✕ Retirer", "motif_n": "Motif {n}", "motif_empty": "(vide)"})
TX["en"].update({"motifs": "Motifs", "motif_add": "＋ Add a motif", "motif_del": "✕ Remove", "motif_n": "Motif {n}", "motif_empty": "(empty)"})


MOTIF_KEYS = ("kind", "text", "path", "font_family", "bold", "size_mm", "rotation_deg", "u", "v", "ncolors", "threshold", "white_is_empty", "thicken_thin", "invert_image")


class PlacementView(QWidget):
    """Interactive top view of the part. Left-drag moves the motif, wheel resizes it (over the motif) or zooms the view,
    Shift+wheel rotates, Ctrl+wheel zooms, right/middle-drag pans, double-click resets the view, arrows nudge."""
    clicked = Signal(float, float)        # recentre at a clicked point
    moved = Signal(float, float)          # new centre while dragging the motif
    scaled = Signal(float)                # size factor
    rotated = Signal(float)               # degrees
    nudged = Signal(float, float)         # mm
    zone_drawn = Signal(float, float, float, float)

    def __init__(self):
        super().__init__(); self.setMinimumSize(380, 340); self.setFocusPolicy(Qt.StrongFocus); self.setMouseTracking(True)
        self.hm = None; self.mask = None; self.layers = None; self.zones = []; self.protected = None; self.center_uv = None
        self.zone_mode = False; self._drag = None; self.base = None; self.msg = ""; self.zoom = 1.0; self.pan = QPointF(0, 0)
        self._moving = None; self._panning = None; self.hint = ""; self.rot = 0                      # rot = quarter turns (counter-clockwise) of the displayed part; 0 = as the axis gives it

    def set_data(self, hm, mask, zones, layers=None, protected=None):
        if hm is not self.hm:
            self.hm = hm; H = hm.H[:-1, :-1]; ok = ~np.isnan(H)
            g = np.full(H.shape, 255, np.uint8)
            if ok.any():
                n = (H - np.nanmin(H)) / (np.ptp(H[ok]) + 1e-9)
                g = np.where(ok, 40 + n * 170, 255).astype(np.uint8)
            g = np.ascontiguousarray(g.T[::-1])
            self.base = QImage(g.data, g.shape[1], g.shape[0], g.shape[1], QImage.Format_Grayscale8).copy()
            self.zoom = 1.0; self.pan = QPointF(0, 0)
        self.mask = mask; self.layers = layers; self.zones = list(zones); self.protected = protected; self.update()

    # --- geometry (fit + zoom + pan)
    def _vw(self): return self.height() if self.rot % 2 else self.width()          # size of the drawing frame (swapped for a quarter turn)
    def _vh(self): return self.width() if self.rot % 2 else self.height()

    def _loc(self, pos):
        """Widget position -> position in the drawing frame (quarter turn: the long side of the part is drawn vertical)."""
        W, H = self.width(), self.height()
        return (pos, QPointF(H - pos.y(), pos.x()), QPointF(W - pos.x(), H - pos.y()), QPointF(pos.y(), W - pos.x()))[self.rot % 4]

    def _rect(self):
        if self.base is None: return QRectF()
        w, h = self.base.width(), self.base.height(); s = min(self._vw() / w, self._vh() / h) * self.zoom
        return QRectF((self._vw() - w * s) / 2 + self.pan.x(), (self._vh() - h * s) / 2 + self.pan.y(), w * s, h * s)

    def _to_uv(self, p):
        r = self._rect(); nu, nv = self.hm.shape
        return (self.hm.u0 + (p.x() - r.x()) / r.width() * (nu - 1) * self.hm.res,
                self.hm.v0 + (1 - (p.y() - r.y()) / r.height()) * (nv - 1) * self.hm.res)

    def _to_px(self, u, v):
        r = self._rect(); nu, nv = self.hm.shape
        return QPointF(r.x() + (u - self.hm.u0) / ((nu - 1) * self.hm.res) * r.width(),
                       r.y() + (1 - (v - self.hm.v0) / ((nv - 1) * self.hm.res)) * r.height())

    def over_motif(self, pos):
        if self.mask is None or self.hm is None or not self.mask.any(): return False
        u, v = self._to_uv(pos); i = int((u - self.hm.u0) / self.hm.res); j = int((v - self.hm.v0) / self.hm.res)
        if not (0 <= i < self.mask.shape[0] and 0 <= j < self.mask.shape[1]): return False
        ii, jj = np.nonzero(self.mask)
        return bool(ii.min() - 3 <= i <= ii.max() + 3 and jj.min() - 3 <= j <= jj.max() + 3)           # bounding box of the motif

    def zoom_at(self, pos, factor):
        if self.hm is None: return
        before = self._to_uv(pos); self.zoom = max(1.0, min(12.0, self.zoom * factor))
        after = self._to_px(*before); self.pan = QPointF(self.pan.x() + pos.x() - after.x(), self.pan.y() + pos.y() - after.y())
        if self.zoom <= 1.0001: self.pan = QPointF(0, 0)
        self.update()

    # --- mouse / keyboard
    def mousePressEvent(self, e):
        if self.hm is None: return
        self.setFocus()
        pos = self._loc(e.position())
        if e.button() in (Qt.RightButton, Qt.MiddleButton): self._panning = pos; return
        if self.zone_mode: self._drag = (pos, pos); return
        u, v = self._to_uv(pos)
        if self.over_motif(pos) and self.center_uv: self._moving = (self.center_uv[0] - u, self.center_uv[1] - v)
        else: self._moving = (0.0, 0.0); self.clicked.emit(u, v)

    def mouseMoveEvent(self, e):
        pos = self._loc(e.position())
        if self._panning is not None:
            d = pos - self._panning; self._panning = pos; self.pan = QPointF(self.pan.x() + d.x(), self.pan.y() + d.y()); self.update(); return
        if self._drag: self._drag = (self._drag[0], pos); self.update(); return
        if self._moving is not None and self.hm is not None and (e.buttons() & Qt.LeftButton):
            u, v = self._to_uv(pos); self.moved.emit(u + self._moving[0], v + self._moving[1])
        elif self.hm is not None:
            self.setCursor(Qt.OpenHandCursor if self.over_motif(pos) else Qt.CrossCursor)

    def mouseReleaseEvent(self, e):
        self._panning = None; self._moving = None
        if self._drag:
            a, b = self._to_uv(self._drag[0]), self._to_uv(self._loc(e.position())); self._drag = None
            if abs(a[0] - b[0]) > 0.5 and abs(a[1] - b[1]) > 0.5: self.zone_drawn.emit(a[0], a[1], b[0], b[1])
            self.update()

    def mouseDoubleClickEvent(self, e): self.zoom = 1.0; self.pan = QPointF(0, 0); self.update()

    def wheel_action(self, delta, mods, pos):
        """Separated from wheelEvent so it can be tested: returns the action taken."""
        steps = delta / 120.0
        if mods & (Qt.ControlModifier | Qt.MetaModifier): self.zoom_at(pos, 1.15 ** steps); return "zoom"
        if mods & Qt.ShiftModifier: self.rotated.emit(5.0 * steps); return "rotate"
        if self.over_motif(pos): self.scaled.emit(1.05 ** steps); return "scale"
        self.zoom_at(pos, 1.15 ** steps); return "zoom"

    def wheelEvent(self, e): self.wheel_action(e.angleDelta().y(), e.modifiers(), self._loc(e.position())); e.accept()

    def keyPressEvent(self, e):
        step = 5.0 if e.modifiers() & Qt.ShiftModifier else 0.5
        d = {Qt.Key_Left: (-step, 0), Qt.Key_Right: (step, 0), Qt.Key_Up: (0, step), Qt.Key_Down: (0, -step)}.get(e.key())
        if d: self.nudged.emit(*d); return
        if e.key() in (Qt.Key_Plus, Qt.Key_Equal): self.scaled.emit(1.05); return
        if e.key() == Qt.Key_Minus: self.scaled.emit(1 / 1.05); return
        super().keyPressEvent(e)

    def paintEvent(self, _):
        p = QPainter(self); p.fillRect(self.rect(), QColor("#eaf4f9")); p.setClipRect(self.rect())
        if self.base is None:
            p.setPen(QColor("#667")); p.drawText(self.rect(), Qt.AlignCenter, self.msg or "—"); return
        p.save()
        W, H = self.width(), self.height()                                           # draw in the turned frame
        if self.rot % 4: p.translate(*((0, H), (W, H), (W, 0))[self.rot % 4 - 1]); p.rotate((-90, 180, 90)[self.rot % 4 - 1])
        r = self._rect(); p.drawImage(r, self.base)
        def overlay(arr_bool, bgra):
            m = np.zeros(arr_bool.shape + (4,), np.uint8); m[arr_bool] = bgra
            m = np.ascontiguousarray(m.transpose(1, 0, 2)[::-1])
            p.drawImage(r, QImage(m.data, m.shape[1], m.shape[0], m.shape[1] * 4, QImage.Format_ARGB32).copy())
        if self.protected is not None and self.protected.any(): overlay(self.protected, (0, 140, 255, 95))        # amber = auto-protected (holes, slots, steep rims)
        if self.mask is not None and self.mask.any():
            m = np.zeros(self.mask.shape + (4,), np.uint8); m[self.mask] = (0, 0, 220, 170)   # BGRA
            for _, (cr, cg, cb), lm in (getattr(self, "layers", None) or []): m[lm] = (cb, cg, cr, 215)
            m = np.ascontiguousarray(m.transpose(1, 0, 2)[::-1])
            p.drawImage(r, QImage(m.data, m.shape[1], m.shape[0], m.shape[1] * 4, QImage.Format_ARGB32).copy())
            if self.protected is not None and (self.mask & self.protected).any(): overlay(self.mask & self.protected, (0, 0, 255, 255))  # offending cells
            ii, jj = np.nonzero(self.mask); a = self._to_px(self.hm.u0 + ii.min() * self.hm.res, self.hm.v0 + (jj.max() + 1) * self.hm.res)
            b = self._to_px(self.hm.u0 + (ii.max() + 1) * self.hm.res, self.hm.v0 + jj.min() * self.hm.res)
            p.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine)); p.setBrush(Qt.NoBrush); p.drawRect(QRectF(a, b).normalized())   # motif frame
        p.setPen(QPen(QColor("#e07000"), 2)); p.setBrush(QColor(224, 112, 0, 70))
        for a, b, c, d in self.zones: p.drawRect(QRectF(self._to_px(a, b), self._to_px(c, d)).normalized())
        if self._drag: p.drawRect(QRectF(self._drag[0], self._drag[1]).normalized())
        p.restore()
        if self.hint:
            p.setPen(QColor("#334")); p.setBrush(QColor(255, 255, 255, 205)); box = QRectF(6, self.height() - 54, self.width() - 12, 50)
            p.drawRect(box); p.drawText(box.adjusted(4, 0, -4, 0), Qt.AlignCenter | Qt.TextWordWrap, self.hint)


ADVANCED_ROWS = {"axis", "thr", "qual", "prot", "inl_off", "camo_seed", "camo_scale"}   # technical rows, shown in advanced mode only


def dspin(lo, hi, val, dec=1, suffix=""):
    s = QDoubleSpinBox(); s.setRange(lo, hi); s.setDecimals(dec); s.setValue(val); s.setSingleStep(0.5 if dec else 1)
    if suffix: s.setSuffix(suffix)
    return s


def zone_file_for(part_path, axis, mirror):
    """Where the forbidden zones drawn on this part (for this view and mirroring) are kept."""
    import hashlib
    root = Path(os.environ.get("CUSTOMLAB_HOME") or Path.home() / ".customlab") / "zones"
    h = hashlib.sha256(Path(part_path).read_bytes()).hexdigest()[:16]
    return root / f"{h}_{axis}{'_m' if mirror else ''}.json"


def zones_for(part_path, axis, mirror):
    try:
        f = zone_file_for(part_path, axis, mirror)
        return [tuple(z) for z in json.loads(f.read_text(encoding="utf-8"))] if f.is_file() else []
    except Exception: return []


class _Signals(QObject):
    done = Signal(int, object)


class _FontPreviewDelegate(QStyledItemDelegate):
    """Each font of the list drawn in its own style, followed by the typed text, so the choice is visual."""
    def __init__(self, sample, parent=None): super().__init__(parent); self.sample = sample

    def sizeHint(self, option, index): return QSize(380, 36)

    def paint(self, p, option, index):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QStyle
        if option.state & QStyle.State_Selected: p.fillRect(option.rect, option.palette.highlight())
        fam = index.data(); f = QFont(fam); f.setPointSize(16); p.save(); p.setFont(f)
        p.setPen(option.palette.highlightedText().color() if option.state & QStyle.State_Selected else option.palette.text().color())
        p.drawText(option.rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, f"{self.sample()}   ·   {fam}"); p.restore()


class PartCombo(QComboBox):
    """Part picker whose pop-up is a wrapped grid of pictures with the name underneath (compact, all parts visible at once)."""
    def showPopup(self):
        super().showPopup(); self.view().setRowHidden(0, True)
        box = self.view().window(); w = min(720, max(self.width(), 640)); n = self.count() - 1; cols = max(1, (w - 20) // 154); rows = (n + cols - 1) // cols
        h = min(640, rows * 130 + 16); g = self.mapToGlobal(self.rect().bottomLeft()); box.setGeometry(g.x(), g.y(), w, h)


class _ThumbSig(QObject):
    ready = Signal(str, str)                 # part path, picture path


class _Job(QRunnable):
    def __init__(self, gen, fn, sig): super().__init__(); self.gen, self.fn, self.sig = gen, fn, sig

    def run(self):
        try: res = ("ok", self.fn())
        except Exception as e: res = ("err", e)
        self.sig.done.emit(self.gen, res)


class CustomizePage(QWidget):
    SIDE_MIN_WIDTH = 1250       # below this window width the small 3D view is hidden: the placement view and the form matter most

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "side"): self.side.setVisible(self.width() >= self.SIDE_MIN_WIDTH)

    changed = Signal()
    generate_requested = Signal()
    batch_requested = Signal()

    def __init__(self, lang="fr"):
        super().__init__(); self.lang = lang
        self.sync = os.environ.get("CUSTOMLAB_SYNC") == "1"; self.mirror_x = False; self.mirror_rule = None; self._gen = 0; self._specs = {}
        self._tsig = _ThumbSig(); self._tsig.ready.connect(self._on_thumb); self._tgen = 0; self._tpool = QThreadPool(); self._tpool.setMaxThreadCount(1)
        self._lsig = _Signals(); self._lsig.done.connect(self._on_loaded); self._lgen = 0; self._lpool = QThreadPool(); self._lpool.setMaxThreadCount(1)
        self._sig = _Signals(); self._sig.done.connect(self._on_done); self._pool = QThreadPool(); self._pool.setMaxThreadCount(1)
        self._timer = QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(120); self._timer.timeout.connect(self._start_job)
        self.part_path = None; self.tris = None; self.hm = None; self.zones = []; self.lic = None; self.svg_path = ""
        self.mask = None; self.errors = []; self.warns = []; self.advanced = False; self.view_rot = 0; self._rots = {}
        h = QHBoxLayout(self); left = QVBoxLayout(); h.setContentsMargins(0, 0, 0, 0)
        panel = QWidget(); panel.setObjectName("page"); panel.setLayout(left); scroll = QScrollArea(); scroll.setWidget(panel); scroll.setWidgetResizable(True)      # the form may be taller than the screen
        scroll.setFrameShape(QFrame.NoFrame); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); h.addWidget(scroll, 2)
        self.gen_box = QWidget(); gb = QVBoxLayout(self.gen_box); gb.setContentsMargins(0, 0, 0, 0)
        self.gen_label = QLabel(); self.gen_label.setWordWrap(True); self.gen_btn = QPushButton(); self.gen_bar = QProgressBar(); self.gen_bar.setRange(0, 0); self.gen_bar.setVisible(False)
        for x in (self.gen_label, self.gen_bar, self.gen_btn): gb.addWidget(x)
        self.gen_box.setVisible(False)
        self.lib = PartCombo(); self.lib.activated.connect(self.pick_library)
        self.b_part = QPushButton(); self.b_part.clicked.connect(self.choose_part)
        self.prov = QLabel(); self.prov.setWordWrap(True); self.prov.setStyleSheet("font-size:11px")
        self.axis = QComboBox(); [self.axis.addItem(a, a) for a in deco.AXES]
        self.mode = QComboBox(); self.kind = QComboBox()
        self.text = QLineEdit(); self.text.setPlaceholderText("ex. Léo"); self.font = QFontComboBox(); self.font.setEditable(False); self.font.setMaxVisibleItems(10); self.font.setMinimumWidth(220); self.font.setView(QListView()); self.font.view().setItemDelegate(_FontPreviewDelegate(lambda: self.text.text().strip() or "Léo", self.font.view())); self.font.view().setMinimumWidth(420); self.bold = QCheckBox(); self.bold.setChecked(True)
        self.b_file = QPushButton(); self.b_file.clicked.connect(self.choose_file); self.b_rmfile = QPushButton("✕"); self.b_rmfile.setObjectName("chip"); self.b_rmfile.setMinimumWidth(36); self.b_rmfile.clicked.connect(self.remove_file)
        self.file_box = QWidget(); _fl = QHBoxLayout(self.file_box); _fl.setContentsMargins(0, 0, 0, 0); _fl.addWidget(self.b_file, 1); _fl.addWidget(self.b_rmfile);
        self.inv = QCheckBox(); self.white = QCheckBox(); self.white.setChecked(True); self.thick = QCheckBox(); self.thick.setChecked(False); self.thr = dspin(10, 245, 128, 0); self.ncol = QSpinBox(); self.ncol.setRange(1, 4); self.ncol.setValue(1); self.prot = dspin(0, 6, 2.0, 1, ' mm')
        self.qual = QComboBox(); [self.qual.addItem(t, v) for t, v in (('Standard (0,25 mm)', 0.25), ('Fin (0,15 mm)', 0.15), ('Très fin (0,10 mm)', 0.10))]; self.qual.setCurrentIndex(1)
        self.size = dspin(2, 200, 20, 1, " mm"); self.rot = dspin(-180, 180, 0, 0, "°")
        self.size_w = self._with_slider(self.size, 2, 200); self.rot_w = self._with_slider(self.rot, -180, 180)
        self.u = dspin(-1000, 1000, 0, 1); self.v = dspin(-1000, 1000, 0, 1); self.depth = dspin(0.0, 5, 1.0, 2, " mm"); self.inl_off = dspin(*deco.INLAY_OFFSET_RANGE, deco.INLAY_TOP_OFFSET_MM, 2, " mm"); self.inl_off.setSingleStep(0.05)
        self.spots = QWidget(); sl = QHBoxLayout(self.spots); sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(4); self.spot_btns = {}
        for k in ("center", "top", "bottom", "left", "right"):
            b = QPushButton(); b.setObjectName("chip"); b.clicked.connect(lambda _=False, k=k: self.place_at(k)); sl.addWidget(b); self.spot_btns[k] = b
        self.pad = QWidget(); pl = QHBoxLayout(self.pad); pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(4); self.pad_step = dspin(0.1, 20, 1.0, 1, " mm"); self.pad_step.setSingleStep(0.5)
        for sym, du, dv in (("◀", -1, 0), ("▲", 0, 1), ("▼", 0, -1), ("▶", 1, 0)):
            b = QPushButton(sym); b.setObjectName("chip"); b.setMinimumWidth(36); b.setAutoRepeat(True); b.setAutoRepeatInterval(120); b.clicked.connect(lambda _=False, a=du, c=dv: self.nudge(a * self.pad_step.value(), c * self.pad_step.value())); pl.addWidget(b)
        pl.addWidget(self.pad_step); self.b_turn = QPushButton("↻"); self.b_turn.setObjectName("chip"); self.b_turn.setMinimumWidth(36); self.b_turn.clicked.connect(lambda: self.turn_view(1)); pl.addWidget(self.b_turn); pl.addStretch(1)
        self.motif_sel = QComboBox(); self.b_addm = QPushButton(); self.b_delm = QPushButton(); self.motif_list = [{}]; self.cur = 0
        self.motif_box = QWidget(); _ml = QHBoxLayout(self.motif_box); _ml.setContentsMargins(0, 0, 0, 0); _ml.addWidget(self.motif_sel, 1); _ml.addWidget(self.b_addm); _ml.addWidget(self.b_delm)
        self.motif_sel.activated.connect(self.select_motif); self.b_addm.clicked.connect(self.add_motif); self.b_delm.clicked.connect(self.remove_motif)
        self.camo_style = QComboBox(); self.camo_seed = QSpinBox(); self.camo_seed.setRange(1, 9999); self.camo_seed.setValue(1); self.camo_scale = dspin(10, 120, 28, 0, " mm")
        self.form = QFormLayout()
        self.rows = {}
        for k, w in (("axis", self.axis), ("mode", self.mode), ("motifs", self.motif_box), ("kind", self.kind), ("camo_style", self.camo_style), ("camo_seed", self.camo_seed), ("camo_scale", self.camo_scale), ("txt", self.text), ("fontrow", self.font), ("bold", self.bold),
                     ("file", self.file_box), ("white", self.white), ("thick", self.thick), ("thr", self.thr), ("ncol", self.ncol), ("qual", self.qual), ("prot", self.prot), ("inv", self.inv), ("size", self.size_w), ("rot", self.rot_w), ("spots", self.spots), ("pad", self.pad), ("u", self.u), ("v", self.v), ("depth", self.depth), ("inl_off", self.inl_off)):
            lab = QLabel(); self.rows[k] = lab; self.form.addRow(lab, w)
        self.b_all = QPushButton(); self.b_all.clicked.connect(lambda: self.batch_requested.emit())
        self.b_zone = QPushButton(); self.b_zone.setCheckable(True); self.b_zone.toggled.connect(self.set_zone_mode)
        self.b_clear = QPushButton(); self.b_clear.clicked.connect(self.clear_zones)
        self.warnbox = QLabel(); self.warnbox.setWordWrap(True); self.warnbox.setStyleSheet("color:#8a4b00;font-size:11px")
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(110)
        self.busy = QLabel(""); self.busy.setStyleSheet("color:#0b314d")
        for x in (self.gen_box, self.lib, self.b_part, self.prov, self.form, self.b_all, self.b_zone, self.b_clear, self.warnbox, self.busy, self.log):
            (left.addLayout if hasattr(x, "addRow") else left.addWidget)(x)
        self.view = PlacementView(); right = QVBoxLayout(); h.addWidget(self.view, 1); self.side = QWidget(); self.side.setLayout(right); right.setContentsMargins(0, 0, 0, 0); self.side.setFixedWidth(230); h.addWidget(self.side); scroll.setMinimumWidth(615); scroll.setMaximumWidth(650)      # form | placement | 3D, the two views side by side with equal room
        self.model = make_view(); self.model.setMinimumSize(200, 160); self.dims = QLabel(); self.dims.setWordWrap(True); self.dims.setStyleSheet("font-size:11px;color:%s" % "#5b6b78")
        right.addWidget(self.model, 1); right.addWidget(self.dims); self.scale_provider = None
        self.kind.currentIndexChanged.connect(self._kind_changed)
        for w in (self.axis, self.mode, self.kind, self.camo_style): w.currentIndexChanged.connect(self.refresh)
        for w in (self.camo_seed, self.camo_scale): w.valueChanged.connect(self.refresh)
        for w in (self.size, self.rot, self.u, self.v, self.depth, self.inl_off): w.valueChanged.connect(self.refresh)
        self.text.textChanged.connect(self.refresh); self.font.currentFontChanged.connect(self.refresh)
        self.bold.toggled.connect(self.refresh); self.inv.toggled.connect(self.refresh); self.white.toggled.connect(self.refresh); self.thick.toggled.connect(self.refresh); self.thr.valueChanged.connect(self.refresh); self.ncol.valueChanged.connect(self.refresh); self.prot.valueChanged.connect(self.refresh)
        self.axis.currentIndexChanged.connect(self.rebuild_heightmap); self.axis.currentIndexChanged.connect(lambda *_: self.update_model())
        self.view.clicked.connect(self.place); self.view.moved.connect(self.place); self.view.zone_drawn.connect(self.add_zone)
        self.view.scaled.connect(self.scale_by); self.view.rotated.connect(self.rotate_by); self.view.nudged.connect(self.nudge)
        self.gen_btn.clicked.connect(lambda: self.generate_requested.emit())
        self.view.hint = self.t("hint2")
        self.retranslate(lang); self.reload_library()

    def t(self, k): return TX[self.lang][k]

    def retranslate(self, lang=None):
        self.lang = lang or self.lang
        self.b_part.setText(self.t("part")); self.b_file.setText(self.t("file"))
        if hasattr(self, "items"): self.lib.setItemText(0, self.t("lib"))
        for k, lab in self.rows.items(): lab.setText(self.t({"fontrow": "txt", "txt": "txt"}.get(k, k)) if k != "fontrow" else "Police")
        for k, combo, items in (("mode", self.mode, ("relief", "engrave", "inlay")), ("kind", self.kind, ("text", "svg", "image") + (("camo",) if SHOW_CAMO else ())), ("camo_style", self.camo_style, ("fr", "winter"))):
            cur = combo.currentData(); combo.blockSignals(True); combo.clear()
            for it in items: combo.addItem(self.t("camo_" + it if combo is self.camo_style else it), it)
            combo.setCurrentIndex(max(0, combo.findData(cur))); combo.blockSignals(False)
        for k, b in self.spot_btns.items(): b.setText(self.t("spot_" + k))
        self.b_addm.setText(self.t("motif_add")); self.b_delm.setText(self.t("motif_del")); self._motif_names(); self.b_all.setText(self.t("camo_all")); self.b_zone.setText(self.t("zone")); self.b_clear.setText(self.t("clear")); self.warnbox.setText(self.t("warn"))
        self.view.msg = self.t("none"); self.show_prov(); self.view.update(); self.update_model()

    # --- state
    def spec(self):
        """The edited motif's spec; the other motifs ride along in .extra (they share mode, depth, view and quality)."""
        b = self._base_spec()
        if len(self.motif_list) < 2: return b
        from dataclasses import replace
        return replace(b, extra=tuple(replace(b, extra=(), **{k: m[k] for k in MOTIF_KEYS}) for i, m in enumerate(self.motif_list) if i != self.cur and m))

    def _base_spec(self):
        return deco.DecoSpec(kind=self.kind.currentData() or "text", text=self.text.text(), path=self.svg_path,
                             font_family=self.font.currentFont().family(), bold=self.bold.isChecked(), size_mm=self.size.value(),
                             rotation_deg=self._part_rot(self.rot.value()), u=self.u.value(), v=self.v.value(), depth_mm=self.depth.value(),
                             mode=self.mode.currentData() or "relief", axis=self.axis.currentData() or "+z", invert_image=self.inv.isChecked(), mirror_x=self.mirror_x, thicken_thin=self.thick.isChecked(), white_is_empty=self.white.isChecked(), threshold=int(self.thr.value()), ncolors=int(self.ncol.value()), res_mm=float(self.qual.currentData() or 0.15), protect_margin_mm=float(self.prot.value()), inlay_offset_mm=float(self.inl_off.value()),
                             camo_style=self.camo_style.currentData() or "fr", camo_seed=int(self.camo_seed.value()), camo_scale_mm=float(self.camo_scale.value()))

    @staticmethod
    def _no_artwork(s): return all(deco.spec_empty(x) for x in (s,) + tuple(s.extra))

    def is_empty(self): return self._no_artwork(self.spec())

    def show_prov(self):
        if not self.part_path: self.prov.setText(self.t("none")); return
        l = self.lic
        txt = f"<b>{Path(self.part_path).name}</b><br>"
        if l and l.get("known"):
            txt += f"{self.t('lic')}: <b>{l['license']}</b>" + (f" — {self.t('nc')}" if l["non_commercial"] else "") + f"<br>{l['title']} / {l['author']}"
        else: txt += f"<span style='color:#b00020'>{self.t('unknown')}</span>"
        self.prov.setText(txt)

    def set_device(self, dev):
        arm = dev == "unlimbited_arm"; self.device = dev
        if getattr(self, "device_prev", dev) != dev: self.motif_list = [{}]; self.cur = 0; self._motif_names()
        self.device_prev = dev
        self.lib.setVisible(not arm); self.b_part.setVisible(not arm); self.gen_box.setVisible(arm)
        if not arm: self.reload_library()

    def set_gen_status(self, text, busy=False, enabled=True):
        self.gen_label.setText(text); self.gen_bar.setVisible(busy); self.gen_btn.setEnabled(enabled and not busy)
        self.gen_btn.setText(self.t("gen"))

    def turn_view(self, k=1):
        """Quarter turn of the displayed part (2D placement + 3D), remembered for this part: lets the volunteer stand it upright."""
        self.set_view_rot(self.view_rot + k)

    def set_view_rot(self, r):
        self.view_rot = int(r) % 4; self.view.rot = self.view_rot
        if self.part_path: self._rots[self.part_path] = self.view_rot
        self.view.update(); self.update_model(); self.refresh()

    def view_basis(self):
        """3D basis matching the placement view: u/v/normal of the chosen axis, turned a quarter when the placement view is."""
        u, v, n = (np.array(r, float) for r in deco.AXES[self.axis.currentData() or "+z"])
        right, up = ((u, v), (-v, u), (-u, -v), (v, -u))[self.view_rot % 4]
        return [right.tolist(), up.tolist(), n.tolist()]

    def update_model(self):
        """Whole part in 3D at the size it will have on export, with its dimensions (scale = what the export applies, else 100 %)."""
        if self.tris is None: self.model.set_triangles([]); self.model.message = self.t("none"); self.dims.setText(""); self.model.update(); return
        pct = (self.scale_provider() if self.scale_provider else None) or 100.0
        a = np.asarray(self.tris, float).reshape(-1, 3, 3); ext = np.ptp(a.reshape(-1, 3), axis=0)         # shown at standard size: the motif is placed on this model
        self.model.set_basis(self.view_basis()); self.model.set_triangles(a); self.model.face_front(); self.model.zoom = 1.15
        txt = self.t("model_dims").format(x=ext[0], y=ext[1], z=ext[2])
        if abs(pct - 100.0) > 1e-6: f = ext * pct / 100.0; txt += " · " + self.t("model_final").format(pct=pct, x=f[0], y=f[1], z=f[2])
        self.dims.setText(txt)

    def clear_part(self):
        self._lgen += 1; self.lib.setEnabled(True); self.b_part.setEnabled(True); self.busy.setText("")       # a load still running for the previous device must not land here
        self.part_path = None; self.tris = None; self.hm = None; self.zones = []; self.mask = None; self.layers = None; self.errors = []; self.warns = []
        self.view.hm = None; self.view.base = None; self.view.mask = None; self.view.layers = None; self.view.protected = None; self.view.update(); self.show_prov(); self.log.setHtml(""); self.update_model()

    def reload_library(self, root=None):
        self.items = library.scan(root) if root else [i for i in library.scan_all() if i.get("device") == getattr(self, "device", "phoenix_hand")]
        self.lib.blockSignals(True); self.lib.clear(); self.lib.addItem(self.t("lib"), None); self.lib.setIconSize(QSize(44, 33)); self.lib.setMaxVisibleItems(30)
        if not isinstance(self.lib.view(), QListView) or self.lib.view().iconSize().width() < 110:      # grid of pictures in the pop-up, small one in the closed box
            v = QListView(); v.setViewMode(QListView.IconMode); v.setIconSize(QSize(100, 75)); v.setGridSize(QSize(150, 126)); v.setWordWrap(True); v.setWrapping(True); v.setMovement(QListView.Static)
            v.setTextElideMode(Qt.ElideNone); v.setResizeMode(QListView.Adjust); v.setUniformItemSizes(True); v.setSpacing(2); v.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.lib.setView(v)
        missing = []
        for it in self.items:
            short = it["label"].split(" — ")[0]; self.lib.addItem(short, it["path"]); i = self.lib.count() - 1; self.lib.setItemData(i, it["label"], Qt.ToolTipRole)   # licence stays in the tooltip and the part panel
            c = thumbs.part_cached(it["path"])
            if c: self.lib.setItemIcon(i, QIcon(str(c)))
            else: missing.append(it["path"])
        self.lib.blockSignals(False); self._tgen += 1; gen = self._tgen
        if missing and not self.sync and cache.enabled():
            def work():
                for path in missing:
                    if gen != self._tgen: return
                    try: self._tsig.ready.emit(str(path), str(thumbs.part_render(path)))
                    except Exception: pass
            self._tpool.start(_Job(gen, work, _Signals()))

    def _on_thumb(self, path, png):
        for i in range(1, self.lib.count()):
            if str(self.lib.itemData(i)) == path: self.lib.setItemIcon(i, QIcon(png)); break

    def pick_library(self, i):
        path = self.lib.itemData(i)
        if path: self.load_part(path)

    def choose_part(self):
        f, _ = QFileDialog.getOpenFileName(self, "STL", "", "STL (*.stl)")
        if f: self.load_part(f)

    def load_part(self, path):
        """User-driven loading: the slow, cacheable steps (reading, face choice, height map) run in a worker so the window stays alive;
        set_part then finds them in the cache. Synchronous in tests."""
        if self.sync or not cache.enabled(): self.set_part(path); return
        mirror = bool(self.mirror_rule(path)) if self.mirror_rule else self.mirror_x; self._lgen += 1; gen = self._lgen
        self.busy.setText(self.t("preparing")); self.view.msg = self.t("preparing"); self.view.update(); self.lib.setEnabled(False); self.b_part.setEnabled(False)

        def work():
            if cache.get_axis(path, mirror) and cache.get_hm(path, mirror, cache.get_axis(path, mirror)["axis"], DRAFT_RES): return path       # already prepared
            tris = read_stl(path)
            if mirror: tris = deco.mirror_tris(tris)
            ax = self._axis_for(path, mirror, tris); self._hm_for(path, mirror, tris, ax, DRAFT_RES); return path
        self._lpool.start(_Job(gen, work, self._lsig)); self._pending_path = str(path)

    def _on_loaded(self, gen, res):
        if gen != self._lgen: return
        self.lib.setEnabled(True); self.b_part.setEnabled(True)
        if res[0] == "err": self.busy.setText(""); self.errors = [str(res[1])]; self.changed.emit(); return
        self.set_part(self._pending_path)

    def choose_file(self):
        flt = "SVG (*.svg)" if self.kind.currentData() == "svg" else "Images (*.png *.jpg *.jpeg)"
        f, _ = QFileDialog.getOpenFileName(self, "", "", flt)
        if f:
            self.svg_path = f; self.b_file.setText(Path(f).name)
            try: self.ncol.blockSignals(True); self.ncol.setValue(deco.suggest_colours(self.spec()))       # one filament per colour of the logo, automatically (changeable)
            finally: self.ncol.blockSignals(False)
            self.refresh()

    # --- several motifs: the form edits one (the selected one); the others are kept as field dicts
    def _cur_fields(self):
        b = self._base_spec(); return {k: getattr(b, k) for k in MOTIF_KEYS}

    def _apply_fields(self, d):
        from PySide6.QtGui import QFont
        self._loading = True
        try:
            self.kind.setCurrentIndex(max(0, self.kind.findData(d["kind"]))); self.text.setText(d["text"]); self.svg_path = d["path"]
            self.b_file.setText(Path(d["path"]).name if d["path"] else self.t("file"))
            if d["font_family"]: self.font.setCurrentFont(QFont(d["font_family"]))
            self.bold.setChecked(bool(d["bold"])); self.size.setValue(d["size_mm"]); self.rot.setValue(self._part_rot(d["rotation_deg"], back=True))
            self.u.setValue(d["u"]); self.v.setValue(d["v"]); self.ncol.setValue(int(d["ncolors"])); self.thr.setValue(d["threshold"])
            self.white.setChecked(bool(d["white_is_empty"])); self.thick.setChecked(bool(d["thicken_thin"])); self.inv.setChecked(bool(d["invert_image"]))
        finally: self._loading = False
        self._toggle_rows(); self.refresh()

    def _motif_label(self, i, m):
        what = m["text"].strip() if m["kind"] == "text" else (Path(m["path"]).name if m["path"] else "") if m["kind"] in ("svg", "image") else self.t("camo")
        return f"{i + 1} · {what or self.t('motif_empty')}"

    def _motif_names(self):
        self.motif_list[self.cur] = self._cur_fields()
        self.motif_sel.blockSignals(True); self.motif_sel.clear()
        for i, m in enumerate(self.motif_list): self.motif_sel.addItem(self._motif_label(i, m))
        self.motif_sel.setCurrentIndex(self.cur); self.motif_sel.blockSignals(False)
        self.b_delm.setVisible(len(self.motif_list) > 1); self.b_addm.setEnabled(self.kind.currentData() != "camo")

    def select_motif(self, i):
        if i == self.cur or not 0 <= i < len(self.motif_list): return
        self.motif_list[self.cur] = self._cur_fields(); self.cur = i; self._apply_fields(self.motif_list[i]); self._motif_names()

    def add_motif(self):
        if self.kind.currentData() == "camo": return
        self.motif_list[self.cur] = cur = self._cur_fields(); k = self.view_rot % 4; g = cur["size_mm"] * 0.9; u, v = cur["u"], cur["v"]
        (rx, ry), (ux, uy) = self._RIGHT[k], self._UP[k]; small = max(8.0, cur["size_mm"] * 0.5)
        spots = [(u - ux * g, v - uy * g), (u + rx * g, v + ry * g), (u - rx * g, v - ry * g), (u + ux * g, v + uy * g)]          # below, right, left, above (as displayed)
        pos = next((c for c in spots if self._fits(c[0], c[1], small / 2)), (u - ux * g, v - uy * g))
        new = dict(cur, kind="text", text="", path="", ncolors=1, size_mm=small, u=pos[0], v=pos[1])
        self.motif_list.append(new); self.cur = len(self.motif_list) - 1; self._apply_fields(new); self._motif_names()

    def _fits(self, u, v, half):
        """True when the centre and the four edge points of a square of half-side `half` lie on the part."""
        if self.hm is None: return True
        for du, dv in ((0, 0), (half, 0), (-half, 0), (0, half), (0, -half)):
            i, j = int(round((u + du - self.hm.u0) / self.hm.res)), int(round((v + dv - self.hm.v0) / self.hm.res))
            if not (0 <= i < self.hm.shape[0] and 0 <= j < self.hm.shape[1]) or np.isnan(self.hm.H[i, j]): return False
        return True

    def remove_motif(self):
        if len(self.motif_list) < 2: return
        del self.motif_list[self.cur]; self.cur = max(0, self.cur - 1); self._apply_fields(self.motif_list[self.cur]); self._motif_names()

    def remove_file(self):
        """Forget the chosen image/SVG so nothing of it stays on the part."""
        self.svg_path = ""; self.b_file.setText(self.t("file")); self.ncol.blockSignals(True); self.ncol.setValue(1); self.ncol.blockSignals(False); self.refresh()

    def set_part(self, path, auto_axis=True):
        if self.mirror_rule: self.mirror_x = bool(self.mirror_rule(path))      # per-part mirroring (e.g. Kinetic Arm: only the RH-named files)
        self.part_path = str(path); self.tris = read_stl(path); self.lic = read_license_info(path)
        self.view_rot = self._rots.get(self.part_path, 0); self.view.rot = self.view_rot
        if self.mirror_x: self.tris = deco.mirror_tris(self.tris)
        self.axis_note = ""
        if auto_axis:                                                       # parts are in print orientation: propose the flattest visible face
            self.busy.setText(self.t("analysing")); QApplication.processEvents()
            ax = self._axis_for(self.part_path, self.mirror_x, self.tris); self.axis.blockSignals(True); self.axis.setCurrentIndex(max(0, self.axis.findData(ax))); self.axis.blockSignals(False)
            self.axis_note = self.t("axis_auto").format(axis=ax)
        self.zones = []; self.hm = None; self.show_prov(); self.update_model(); self.rebuild_heightmap(center=True); self.load_zones()

    @staticmethod
    def _axis_for(path, mirror, tris):
        hit = cache.get_axis(path, mirror)
        if hit: return hit["axis"]
        ax, sc = deco.suggest_axis(tris); cache.put_axis(path, mirror, ax, sc); return ax

    @staticmethod
    def _hm_for(path, mirror, tris, axis, res):
        hm = cache.get_hm(path, mirror, axis, res) if path else None
        if hm is None:
            hm = deco.build_heightmap(tris, axis, res)
            if path: cache.put_hm(path, mirror, axis, res, hm)
        return hm

    def rebuild_heightmap(self, *_, center=False):
        if self.tris is None: return
        self.busy.setText(self.t("preparing")); QApplication.processEvents()
        self.hm = self._hm_for(self.part_path, self.mirror_x, self.tris, self.axis.currentData() or "+z", max(self.qual.currentData() or 0.15, DRAFT_RES))      # placement works on a light grid; the chosen finesse is built for the result
        if center:
            ok = np.argwhere(~np.isnan(self.hm.H)); c = (ok.min(0) + ok.max(0)) / 2
            for s, val in ((self.u, self.hm.u0 + c[0] * self.hm.res), (self.v, self.hm.v0 + c[1] * self.hm.res)):
                s.blockSignals(True); s.setValue(float(val)); s.blockSignals(False)
        self.zones = [] if center else self.zones
        if not center: self.load_zones()
        self.refresh(); self.update_model()

    def state_dict(self):
        sp = deco._spec_dict(self.spec()); sp.pop("extra", None); self.motif_list[self.cur] = self._cur_fields()
        return {"part_path": self.part_path, "spec": sp, "zones": [list(z) for z in self.zones], "view_rot": self.view_rot, "motifs": [dict(m) for m in self.motif_list], "motif_cur": self.cur}

    def load_state(self, d):
        """Restore a saved customisation. Returns a list of problems (missing files) instead of raising."""
        problems = []; sp = d.get("spec", {})
        self._loading = True
        try:
            self.mirror_x = bool(sp.get("mirror_x", self.mirror_x)); pp = d.get("part_path")
            if pp and Path(pp).is_file(): self._rots[str(pp)] = int(d.get("view_rot", 0)); self.set_part(pp, auto_axis=False)
            elif pp: problems.append(f"Pièce introuvable : {pp}")
            self.kind.setCurrentIndex(max(0, self.kind.findData(sp.get("kind", "text")))); self.text.setText(sp.get("text", ""))
            path = sp.get("path", "")
            if path and not Path(path).is_file(): problems.append(f"Fichier du motif introuvable : {path}"); path = ""
            self.svg_path = path; self.b_file.setText(Path(path).name if path else self.t("file"))
            if sp.get("font_family"): self.font.setCurrentFont(__import__("PySide6.QtGui", fromlist=["QFont"]).QFont(sp["font_family"]))
            self.bold.setChecked(bool(sp.get("bold", True))); self.size.setValue(sp.get("size_mm", 20.0)); self.rot.setValue(self._part_rot(sp.get("rotation_deg", 0.0), back=True))
            self.u.setValue(sp.get("u", 0.0)); self.v.setValue(sp.get("v", 0.0)); self.depth.setValue(sp.get("depth_mm", 1.0))
            self.mode.setCurrentIndex(max(0, self.mode.findData(sp.get("mode", "relief")))); self.ncol.setValue(int(sp.get("ncolors", 1))); self.thick.setChecked(bool(sp.get("thicken_thin", False)))
            self.thr.setValue(sp.get("threshold", 128)); self.white.setChecked(bool(sp.get("white_is_empty", True))); self.inv.setChecked(bool(sp.get("invert_image", False)))
            self.camo_style.setCurrentIndex(max(0, self.camo_style.findData(sp.get("camo_style", "fr")))); self.camo_seed.setValue(int(sp.get("camo_seed", 1))); self.camo_scale.setValue(sp.get("camo_scale_mm", 28.0))
            self.prot.setValue(sp.get("protect_margin_mm", 2.0)); self.inl_off.setValue(sp.get("inlay_offset_mm", deco.INLAY_LEGACY_OFFSET_MM)); self.qual.setCurrentIndex(max(0, self.qual.findData(sp.get("res_mm", 0.15))))
            ax = self.axis.findData(sp.get("axis", "+z"))
            if ax >= 0 and ax != self.axis.currentIndex(): self.axis.blockSignals(True); self.axis.setCurrentIndex(ax); self.axis.blockSignals(False)
        finally:
            self._loading = False
        if self.tris is not None: self.rebuild_heightmap()
        ms = d.get("motifs")
        if ms and all(set(MOTIF_KEYS) <= set(m) for m in ms):
            for m in ms:
                if m["path"] and not Path(m["path"]).is_file(): problems.append(f"Fichier du motif introuvable : {m['path']}"); m["path"] = ""
            self.motif_list = [dict(m) for m in ms]; self.cur = min(max(0, int(d.get("motif_cur", 0))), len(ms) - 1); self._apply_fields(self.motif_list[self.cur])
        else: self.motif_list = [{}]; self.cur = 0
        self._motif_names()
        if "zones" in d: self.zones = [tuple(z) for z in d["zones"]]; self.save_zones(); self.refresh()
        return problems

    def find_free_spot(self, step=None):
        """Scan the part with a coarse grid (step ~ a third of the motif size, one colour) for a position without error; place the motif
        there with the real settings and return (u, v), or None."""
        if self.hm is None: return None
        from dataclasses import replace
        s = self.spec(); coarse = replace(s, ncolors=1); prot = self.protected_mask(s)
        step = step or max(8, int(s.size_mm / self.hm.res / 3))
        for iu in range(0, self.hm.shape[0], step):
            for jv in range(0, self.hm.shape[1], step):
                if np.isnan(self.hm.H[iu, jv]): continue
                coarse.u, coarse.v = self.hm.u0 + iu * self.hm.res, self.hm.v0 + jv * self.hm.res
                try:
                    m, _ = deco.render_spec_masks(coarse, self.hm)
                    errors, _, _ = deco.check_placement(self.hm, m, list(self.zones), s.depth_mm, s.mode, prot)
                except deco.DecoError: continue
                if not errors and m.any():
                    self.place(coarse.u, coarse.v)
                    return float(self.u.value()), float(self.v.value())
        return None

    def scale_by(self, f): self.size.setValue(max(self.size.minimum(), min(self.size.maximum(), self.size.value() * f)))

    def rotate_by(self, deg):
        v = (self.rot.value() + deg + 180) % 360 - 180; self.rot.setValue(v)

    # displayed right / up expressed in part (u, v) for each quarter turn of the view
    _RIGHT = ((1, 0), (0, -1), (-1, 0), (0, 1)); _UP = ((0, 1), (1, 0), (0, -1), (-1, 0))

    def _part_rot(self, deg, back=False):
        """Motif angle shown on screen <-> angle in the part frame (the view may be turned by quarter turns): the motif stays upright on screen."""
        return (deg + (90 if back else -90) * self.view_rot + 180) % 360 - 180

    def nudge(self, du, dv):
        """du, dv in the displayed directions (right, up); converted to the part frame."""
        r, u = self._RIGHT[self.view_rot % 4], self._UP[self.view_rot % 4]
        self.place(self.u.value() + du * r[0] + dv * u[0], self.v.value() + du * r[1] + dv * u[1])

    def set_mirror(self, flag):
        """Left-hand versions of right-hand models: reload the part mirrored (keeps the current motif settings)."""
        flag = bool(flag)
        if flag == self.mirror_x: return
        self.mirror_x = flag
        if self.part_path:
            keep = self.spec(); path = self.part_path; self._loading = True
            try: self.set_part(path, auto_axis=False)
            finally: self._loading = False
            self.rebuild_heightmap(center=False)

    def set_zone_mode(self, on): self.view.zone_mode = on

    def _zone_file(self):
        return zone_file_for(self.part_path, self.axis.currentData() or "+z", self.mirror_x) if self.part_path else None

    def load_zones(self):
        try:
            f = self._zone_file()
            if f and f.is_file(): self.zones = [tuple(z) for z in json.loads(f.read_text(encoding="utf-8"))]; self.refresh()
        except Exception: pass                                   # a missing/corrupt zone file never blocks the app

    def save_zones(self):
        try:
            f = self._zone_file()
            if f: f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(self.zones), encoding="utf-8")
        except Exception: pass

    def add_zone(self, a, b, c, d): self.zones.append((a, b, c, d)); self.save_zones(); self.refresh()

    def clear_zones(self): self.zones = []; self.save_zones(); self.refresh()

    def _with_slider(self, spin, lo, hi):
        """The spin box and a slider side by side, kept in sync (the spin box stays the single source of truth)."""
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 0); sl = QSlider(Qt.Horizontal); sl.setRange(int(lo), int(hi)); sl.setValue(int(spin.value()))
        sl.valueChanged.connect(lambda v: spin.setValue(float(v)) if int(round(spin.value())) != v else None)
        spin.valueChanged.connect(lambda v: (sl.blockSignals(True), sl.setValue(int(round(v))), sl.blockSignals(False)))
        l.addWidget(spin); l.addWidget(sl, 1); return w

    def place_at(self, where):
        """Quick placement: centre or against an edge of the part's visible area (motif half-size + 3 mm margin)."""
        if self.hm is None: return
        ok = np.argwhere(~np.isnan(self.hm.H)); (i0, j0), (i1, j1) = ok.min(0), ok.max(0)
        u0, u1 = self.hm.u0 + i0 * self.hm.res, self.hm.u0 + i1 * self.hm.res; v0, v1 = self.hm.v0 + j0 * self.hm.res, self.hm.v0 + j1 * self.hm.res
        if where != "center":                                               # "top/left/..." are as displayed: map to the part frame
            vec = {"top": self._UP, "bottom": tuple((-x, -y) for x, y in self._UP), "right": self._RIGHT, "left": tuple((-x, -y) for x, y in self._RIGHT)}[where][self.view_rot % 4]
            where = {(0, 1): "top", (0, -1): "bottom", (1, 0): "right", (-1, 0): "left"}[vec]
        h = self.size.value() / 2 + 3; cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        u, v = {"center": (cu, cv), "top": (cu, v1 - h), "bottom": (cu, v0 + h), "left": (u0 + h, cv), "right": (u1 - h, cv)}[where]
        self.place(u, v)

    def place(self, u, v):
        for s, val in ((self.u, u), (self.v, v)): s.blockSignals(True); s.setValue(round(val, 1)); s.blockSignals(False)
        self.refresh()

    def _toggle_rows(self):
        kind = self.kind.currentData(); camo = kind == "camo"
        widgets = {"motifs": (self.motif_box,), "txt": (self.text,), "fontrow": (self.font,), "bold": (self.bold,), "file": (self.file_box,), "inv": (self.inv,), "white": (self.white,), "thick": (self.thick,), "thr": (self.thr,), "ncol": (self.ncol,), "prot": (self.prot,), "inl_off": (self.inl_off,),
                   "camo_style": (self.camo_style,), "camo_seed": (self.camo_seed,), "camo_scale": (self.camo_scale,), "size": (self.size_w,), "rot": (self.rot_w,), "spots": (self.spots,), "pad": (self.pad,), "u": (self.u,), "v": (self.v,)}
        show = {"motifs": not camo or len(self.motif_list) > 1, "txt": kind == "text", "fontrow": kind == "text", "bold": kind == "text", "file": kind in ("svg", "image"), "inv": kind == "image", "white": kind in ("svg", "image"), "thick": kind in ("svg", "image"), "thr": kind == "image",
                "ncol": kind in ("svg", "image") and self.mode.currentData() != "engrave", "prot": True, "inl_off": self.mode.currentData() == "inlay" and kind != "camo", "camo_style": camo, "camo_seed": camo, "camo_scale": camo,
                "size": not camo, "rot": not camo, "spots": not camo, "pad": not camo, "u": not camo, "v": not camo}
        for k, ws in widgets.items():
            vis = show[k] and (self.advanced or k not in ADVANCED_ROWS)
            self.rows[k].setVisible(vis); [w.setVisible(vis) for w in ws]
        self.b_all.setVisible(camo)
        for k, w in (("axis", self.axis), ("qual", self.qual)):
            self.rows[k].setVisible(self.advanced); w.setVisible(self.advanced)
        for w in (self.b_zone, self.b_clear, self.log): w.setVisible(self.advanced)

    def set_advanced(self, flag):
        """Simple mode hides the technical settings (they keep their defaults); advanced mode shows them all."""
        self.advanced = bool(flag); self._toggle_rows()

    def _kind_changed(self, *_):
        """First choice of the camouflage: sensible defaults (flush inlay, thin, standard grid); the volunteer can change them."""
        if self.kind.currentData() != "camo" or getattr(self, "_loading", False): return
        for combo, val in ((self.mode, "inlay"), (self.qual, 0.25)):
            combo.blockSignals(True); combo.setCurrentIndex(max(0, combo.findData(val))); combo.blockSignals(False)
        self.depth.blockSignals(True); self.depth.setValue(0.6); self.depth.blockSignals(False)

    def protected_mask(self, s):
        if s.protect_margin_mm <= 0: return None
        key = (id(self.hm), s.protect_margin_mm)
        if getattr(self, "_pm_key", None) != key: self._pm = deco.auto_protected_mask(self.hm, s.protect_margin_mm); self._pm_key = key
        return self._pm

    # ---- recomputation: debounced and run in a worker thread so the window never freezes
    def _is_watertight(self):
        key = id(self.tris)
        if getattr(self, "_wt_key", None) != key: self._wt = deco.is_watertight(self.tris); self._wt_key = key
        return self._wt

    def refresh(self, *_):
        self._toggle_rows()
        if self.motif_sel.count() == len(self.motif_list): self.motif_sel.setItemText(self.cur, self._motif_label(self.cur, self._cur_fields()))
        if self.hm is None or getattr(self, "_loading", False): return
        s = self.spec(); self._gen += 1
        if self.sync or s.kind == "text" or self.is_empty():           # cheap cases (text, nothing) and tests: immediate
            self._apply(self._compute(s, list(self.zones), self.hm, self.protected_mask(s), self._is_watertight() if s.mode == "engrave" else True), s); return
        self.busy.setText(self.t("busy")); self._timer.start(120)       # debounce: only the last change is computed

    def _compute(self, s, zones, hm, prot, watertight):
        """Pure computation (safe in a worker thread): returns what the page needs to display."""
        r = {"mask": None, "layers": None, "errors": [], "warns": []}
        if self._no_artwork(s): r["warns"] = ["(aucune décoration)"]; return r
        try:
            r["mask"], r["layers"] = deco.render_spec_masks(s, hm, prot, zones)
            r["errors"], w, info = deco.check_placement(hm, r["mask"], zones, s.depth_mm, s.mode, prot)
            r["warns"] = [x for x in w if not x.startswith("Zones fonctionnelles")]
            if s.mode == "engrave" and not watertight:
                r["errors"].append("Gravure impossible : pièce non étanche (soustraction non fiable). Utiliser le relief.")
        except deco.DecoError as e: r["errors"] = [str(e)]
        return r

    def _start_job(self):
        if self.hm is None: return
        s = self.spec(); gen = self._gen; zones = list(self.zones); hm = self.hm; prot = self.protected_mask(s)
        wt = self._is_watertight() if s.mode == "engrave" else True; self._specs[gen] = s
        self._pool.start(_Job(gen, lambda: self._compute(s, zones, hm, prot, wt), self._sig))

    def _on_done(self, gen, res):
        s = self._specs.pop(gen, None)
        if gen != self._gen or s is None: return                        # a newer change superseded this result
        if res[0] == "err": self.busy.setText(""); self.errors = [str(res[1])]; self.warns = []; self.changed.emit(); return
        self._apply(res[1], s)

    def ensure_fresh(self):
        """Wait until the displayed state matches the widgets (used before generating/exporting)."""
        if self._timer.isActive(): self._timer.stop(); self._start_job()
        self._pool.waitForDone(); QApplication.processEvents()

    def _apply(self, r, s):
        self.mask, self.layers, self.errors, self.warns = r["mask"], r["layers"], r["errors"], r["warns"]; self.busy.setText("")
        self.view.center_uv = (s.u, s.v); self.view.set_data(self.hm, self.mask, self.zones, self.layers, self.protected_mask(s))
        pal = "".join(f"<span style='color:{h}'>■</span> {h} — {int(m.sum())} {'points' if self.lang == 'fr' else 'points'} → {'pièce' if self.lang == 'fr' else 'part'} {n}<br>" for n, (h, _, m) in enumerate(self.layers or [], start=2))
        from . import messages as M
        body = M.messages_html([(e, M.BLOCK) for e in self.errors] + [(w, None) for w in self.warns], self.lang)
        note = f"<span style='color:#0b314d'>ℹ {self.axis_note}</span><br>" if getattr(self, "axis_note", "") else ""
        self.log.setHtml(note + pal + body if (note or pal or body) else "✓")
        self.changed.emit()

    # --- result (heavy: builds the solid / runs OpenSCAD for engraving)
    def compute_result(self):
        """Synchronous (tests, scripts)."""
        self.ensure_fresh()
        return self.compute_result_raw(*self.result_inputs())

    def result_inputs(self):
        """Everything the heavy computation needs, read from the widgets in the GUI thread."""
        sp = self.spec(); hm = self.hm if self.hm is not None and self.hm.res <= sp.res_mm + 1e-9 else None      # None: the fine grid is built in the worker
        return self.part_path, sp, list(self.zones), hm, self.is_empty(), self.tris

    @staticmethod
    def compute_result_raw(part_path, spec, zones, hm, empty, tris):
        """Pure computation, safe in a worker thread."""
        if not part_path: return None
        if empty: return deco.DecoResult(tris, [], [], ["(aucune décoration)"], {})
        return deco.apply_decoration(part_path, spec, zones, hm=hm)
