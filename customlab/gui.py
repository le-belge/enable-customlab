"""e-NABLE CustomLab — first PySide6 GUI: catalogue -> measures -> result/3D -> export."""
import json
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
                               QTextEdit, QVBoxLayout, QWidget)

from . import kinetic_arm, openscad, phoenix, theme
from .meshio import is_watertight, read_stl, write_stl
from .meshscale import scale_stl_python
from .profiles import SizingError, compute_phoenix_sizing, compute_sizing, list_profiles
from . import armgen, deco
from .profiles import compute_kinetic_arm_sizing, compute_kinetic_sizing
from . import messages as M
from .placement import CustomizePage
from . import thumbs
from .paths import get_setting, save_setting
from .glview import make_view, set_default_format
from .placement import _Job, _Signals

ASSETS = Path(__file__).resolve().parent / "assets" / "schemas"
SCHEMA = {"phoenix_hand": "poignet", "unlimbited_arm": "bras"}
SCALE_RANGE = {"phoenix_hand": (100.0, 160.0), "kinetic_hand": (50.0, 100.0), "kinetic_arm": (50.0, 100.0)}      # documented ranges: a value outside is refused, never corrected
SCALABLE = ("phoenix_hand", "kinetic_hand", "kinetic_arm")            # uniform scale applied by CustomLab at export (the arm is scaled by its own SCAD)
DECO_DEVICES = ("phoenix_hand", "unlimbited_arm", "kinetic_hand", "kinetic_arm")      # devices for which the customisation page works (arm parts are generated from the official SCAD)

T = {
 "fr": {"title": "e-NABLE CustomLab", "catalog": "1 · Appareil", "measures": "2 · Mesures & dimensionnement", "custom": "3 · Personnalisation", "result": "4 · Aperçu 3D & export",
        "next": "Suivant →", "back": "← Retour", "side": "Côté", "part": "Pièce", "left": "Gauche", "right": "Droite",
        "status_experimental": "EXPÉRIMENTAL", "status_unavailable": "INDISPONIBLE", "status_verified": "VÉRIFIÉ",
        "license": "Licence", "blocked": "Blocage", "info": "Information", "import_stl": "Importer un STL officiel (100 %)…",
        "import_scad": "Fournir le .scad officiel…", "export": "Exporter le STL…", "generate": "Générer",
        "no_sizing": "Dimensionnement indisponible pour cet appareil. Voir le blocage ci-dessus.",
        "jig": "Imprimez d'abord le gabarit Phoenix pour vérifier l'ajustement.", "lang": "English",
        "disclaimer": "Aucune validation médicale ni d'impression : à faire contrôler par un bénévole e-NABLE compétent.",
        "scale": "Échelle", "usable": "Largeurs de poignet utilisables", "err": "Erreur",
        "kcheck": "Contrôle de cohérence Kinetic Arm (documenté NIH 3D) — ce n'est pas un dimensionnement",
        "resid": "Longueur du moignon", "forearm": "Avant-bras valide", "pick": "Choisissez un appareil.", "hello": "Quel appareil voulez-vous adapter ?", "hello2": "Dimensionnez-le à partir des mesures du bénéficiaire, personnalisez-le, puis exportez les pièces pour l'impression.", "select": "Sélectionner", "scale_cb": "Appliquer l'échelle calculée à l'export (uniforme, vérifiée sur le SCAD officiel)", "scale_cb_kinetic": "Appliquer l'échelle du tableau du manuel à l'export (uniforme, toutes les pièces)", "nocustom": "Personnalisation disponible pour la Phoenix uniquement.", "nopart": "Choisissez d'abord la pièce à l'étape 3.", "export_dir": "Exporter la pièce (STL + fiche)…", "export_all": "Exporter toutes les pièces à cette échelle…", "m_help": "Aide", "m_scale": "Mettre à l'échelle : pas à pas (appareil choisi)…", "scale_btn": "ℹ️ Comment calculer l'échelle ? (pas à pas)", "photo_btn": "📷 Mesurer sur une photo (avec un mètre ou une carte bancaire à côté)…", "export_one": "Exporter tout, prêt pour Bambu…", "m_view": "Affichage", "m_adv": "Mode avancé (tous les réglages)", "m_sources": "Fichiers sources (SCAD / STL)…", "m_tuto": "Tuto : mesures, échelles et personnalisation…", "tuto_btn": "📖 Lire le tuto avant de commencer", "exported": "Exporté", "open_slicer": "Ouvrir dans le trancheur (Bambu Studio)", "m_file": "Fichier", "m_new": "Nouveau projet", "m_open": "Ouvrir un projet…", "m_save": "Enregistrer le projet…", "m_recent": "Projets récents", "m_prof": "Profils bénéficiaires…", "m_people": "Bénéficiaires", "proj_filter": "Projet CustomLab (*.customlab.json)", "saved": "Projet enregistré", "none_recent": "(aucun)", "load_problems": "Projet ouvert avec des éléments introuvables"},
 "en": {"title": "e-NABLE CustomLab", "catalog": "1 · Device", "measures": "2 · Measures & sizing", "custom": "3 · Customisation", "result": "4 · 3D preview & export",
        "next": "Next →", "back": "← Back", "side": "Side", "part": "Part", "left": "Left", "right": "Right",
        "status_experimental": "EXPERIMENTAL", "status_unavailable": "UNAVAILABLE", "status_verified": "VERIFIED",
        "license": "Licence", "blocked": "Blocker", "info": "Information", "import_stl": "Import official STL (100 %)…",
        "import_scad": "Provide official .scad…", "export": "Export STL…", "generate": "Generate",
        "no_sizing": "Sizing is unavailable for this device. See the blocker above.",
        "jig": "Print the Phoenix verification jig first to check the fit.", "lang": "Français",
        "disclaimer": "No medical or print validation: have a qualified e-NABLE volunteer check it.",
        "scale": "Scale", "usable": "Usable wrist widths", "err": "Error",
        "kcheck": "Kinetic Arm consistency check (NIH 3D documented) — not a sizing method",
        "resid": "Residual limb length", "forearm": "Sound forearm length", "pick": "Choose a device.", "hello": "Which device would you like to adapt?", "hello2": "Size it from the beneficiary's measurements, personalise it, then export the parts for printing.", "select": "Select", "scale_cb": "Apply the computed scale on export (uniform, checked against the official SCAD)", "scale_cb_kinetic": "Apply the manual's chart scale on export (uniform, all parts)", "nocustom": "Customisation is available for the Phoenix only.", "nopart": "Choose the part in step 3 first.", "export_dir": "Export the part (STL + sheet)…", "export_all": "Export all parts at this scale…", "m_help": "Help", "m_scale": "Scaling: step by step (chosen device)…", "scale_btn": "ℹ️ How is the scale computed? (step by step)", "photo_btn": "📷 Measure on a photo (with a ruler or bank card beside it)…", "export_one": "Export everything, ready for Bambu…", "m_view": "View", "m_adv": "Advanced mode (all settings)", "m_sources": "Source files (SCAD / STL)…", "m_tuto": "Tutorial: measuring, scaling and customising (in French)…", "tuto_btn": "📖 Read the tutorial before starting (in French)", "exported": "Exported", "open_slicer": "Open in the slicer (Bambu Studio)", "m_file": "File", "m_new": "New project", "m_open": "Open a project…", "m_save": "Save the project…", "m_recent": "Recent projects", "m_prof": "Beneficiary profiles…", "m_people": "Beneficiaries", "proj_filter": "CustomLab project (*.customlab.json)", "saved": "Project saved", "none_recent": "(none)", "load_problems": "Project opened with items not found"},
}
BADGE = theme.STATUS


def spin(lo=0.0, hi=2000.0, val=0.0, dec=1):
    s = QDoubleSpinBox(); s.setRange(lo, hi); s.setDecimals(dec); s.setValue(val); s.setSuffix(" mm"); return s


class _RSig(QObject):
    done = Signal(int, object)


class _RJob(QRunnable):
    def __init__(self, gen, fn, sig): super().__init__(); self.gen, self.fn, self.sig = gen, fn, sig

    def run(self):
        try: res = ("ok", self.fn())
        except Exception as e: res = ("err", e)
        self.sig.done.emit(self.gen, res)


class MainWindow(QMainWindow):
    def __init__(self, lang="fr"):
        super().__init__()
        self.advanced = bool(get_setting("advanced_mode", False))
        self.lang = lang; self.profiles = {p["id"]: p for p in list_profiles()}
        self.dev = None; self.scad = None; self.base_tris = None; self.out_tris = None; self.sizing = None
        self.resize(1320, 760)
        root = QWidget(); self.setCentralWidget(root); v = QVBoxLayout(root); v.setContentsMargins(18, 14, 18, 14); v.setSpacing(12)
        self.step = QLabel(); self.langbtn = QPushButton(); self.langbtn.clicked.connect(self.toggle_lang)
        self.header = theme.Header(self.step, self.langbtn); v.addWidget(self.header)
        self.stack = QStackedWidget(); v.addWidget(self.stack, 1)
        self.disc = QLabel(); self.disc.setWordWrap(True); self.disc.setStyleSheet(f"color:{theme.WARN};font-size:11px"); v.addWidget(self.disc)
        nav = QHBoxLayout(); self.bback = QPushButton(); self.bnext = QPushButton()
        self.bback.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
        self.bnext.clicked.connect(lambda: self.go(self.stack.currentIndex() + 1))
        self.bnext.setObjectName("primary"); self.bnext.setMinimumWidth(130); self.bback.setMinimumWidth(110)
        nav.addWidget(self.bback); nav.addStretch(1); nav.addWidget(self.bnext); v.addLayout(nav)
        self.arm_gen = None; self._gpool = QThreadPool(); self._gpool.setMaxThreadCount(1); self._gsig = _RSig(); self._gsig.done.connect(self._on_generated); self._ggen = 0
        self._rpool = QThreadPool(); self._rpool.setMaxThreadCount(1); self._rsig = _RSig(); self._rsig.done.connect(self._on_result); self._rgen = 0; self._rmsgs = None
        self.build_menus()
        self.build_catalog(); self.build_measures()
        self.custom = CustomizePage(self.lang); self.stack.addWidget(self.custom)
        self.custom.generate_requested.connect(self.generate_arm_part); self.custom.batch_requested.connect(self.camo_batch); self.custom.scale_provider = lambda: self.scale_percent() if self.scale_cb.isChecked() else None
        self.deco_result = None; self.src_path = None
        self.build_result()
        self.custom.set_advanced(self.advanced)
        self.retranslate(); self.go(0)

    def t(self, k): return T[self.lang][k]

    def set_advanced(self, flag):
        """Simple mode (default): only what a volunteer needs; advanced mode: every setting. The choice is remembered."""
        self.advanced = bool(flag)
        try: save_setting("advanced_mode", self.advanced)
        except OSError: pass
        self.custom.set_advanced(self.advanced)
        if self.dev:
            self.fill_measures()
            if self.stack.currentIndex() == 3: self.show_result()

    # --- menus, projects, profiles
    def build_menus(self):
        mb = self.menuBar(); self.m_file = mb.addMenu(""); self.m_people = mb.addMenu(""); self.m_help = mb.addMenu(""); self.a_tuto = QAction(self); self.a_tuto.triggered.connect(self.show_tuto); self.m_help.addAction(self.a_tuto)
        self.a_scale = QAction(self); self.a_scale.triggered.connect(self.show_scale_guide); self.m_help.insertAction(self.a_tuto, self.a_scale)
        self.a_src = QAction(self); self.a_src.triggered.connect(self.show_sources); self.m_help.addAction(self.a_src)
        self.a_new = QAction(self); self.a_new.triggered.connect(self.new_project)
        self.a_open = QAction(self); self.a_open.triggered.connect(lambda: self.open_project_dialog())
        self.a_save = QAction(self); self.a_save.triggered.connect(lambda: self.save_project_dialog())
        self.m_recent = self.m_file.addMenu("")
        for a in (self.a_new, self.a_open, self.a_save): self.m_file.insertAction(self.m_recent.menuAction(), a)
        self.a_prof = QAction(self); self.a_prof.triggered.connect(self.show_profiles); self.m_people.addAction(self.a_prof)
        self.m_view = mb.addMenu(""); self.a_adv = QAction(self); self.a_adv.setCheckable(True); self.a_adv.setChecked(self.advanced); self.a_adv.toggled.connect(self.set_advanced); self.m_view.addAction(self.a_adv)

    def _home(self): return Path(os.environ.get("CUSTOMLAB_HOME") or Path.home() / ".customlab")

    def recent_projects(self):
        try: return [p for p in json.loads((self._home() / "recent.json").read_text(encoding="utf-8")) if Path(p).is_file()]
        except Exception: return []

    def _remember(self, path):
        try:
            rec = [str(path)] + [p for p in self.recent_projects() if p != str(path)]
            self._home().mkdir(parents=True, exist_ok=True); (self._home() / "recent.json").write_text(json.dumps(rec[:8]), encoding="utf-8")
        except Exception: pass
        self.refresh_recent_menu()

    def refresh_recent_menu(self):
        self.m_recent.clear(); recent = self.recent_projects()
        if not recent: a = self.m_recent.addAction(self.t("none_recent")); a.setEnabled(False)
        for p in recent:
            a = self.m_recent.addAction(Path(p).name); a.triggered.connect(lambda _=False, q=p: self.open_project(q))

    def state_dict(self):
        st = {"version": 1, "device": self.dev, "side": self.side.currentData(), "part": self.part.currentText(), "measures": self.values(),
              "scale_on_export": self.scale_cb.isChecked(), "scale_override": self.scale_override, "step": self.stack.currentIndex()}
        if self.dev in DECO_DEVICES and self.custom.part_path: st["custom"] = self.custom.state_dict()
        if self.dev == "unlimbited_arm" and self.arm_gen: st["arm_gen"] = {"defines": self.arm_gen["defines"], "path": str(self.arm_gen["path"])}
        return st

    def load_state(self, d):
        """Restore a project/record. Returns a list of problems (missing files); never raises on a missing file."""
        if not d or d.get("device") not in self.profiles: return ["Projet vide ou appareil inconnu"]
        self.select(d["device"])
        i = self.side.findData(d.get("side")); self.side.setCurrentIndex(max(0, i))
        j = self.part.findText(d.get("part", "")); self.part.setCurrentIndex(max(0, j))
        for k, v in d.get("measures", {}).items():
            if k in self.fields: self.fields[k].setValue(v)
        self.scale_cb.setChecked(bool(d.get("scale_on_export", False))); self.scale_override = d.get("scale_override")
        self.sync_direct()
        self.update_mirror(reload=False)
        problems = self.custom.load_state(d["custom"]) if d.get("custom") else []
        g = d.get("arm_gen")
        if g and Path(g.get("path", "")).is_file(): self.arm_gen = {"defines": g["defines"], "path": Path(g["path"])}
        self.recompute(); self.go(int(d.get("step", 1)))
        return problems

    def save_project(self, path):
        path = str(path)
        if not path.endswith(".customlab.json"): path += ".customlab.json"
        Path(path).write_text(json.dumps(self.state_dict(), indent=2, ensure_ascii=False), encoding="utf-8"); self._remember(path); return path

    def open_project(self, path):
        problems = self.load_state(json.loads(Path(path).read_text(encoding="utf-8"))); self._remember(path)
        if problems: QMessageBox.warning(self, self.t("m_open"), self.t("load_problems") + " :\n" + "\n".join(problems))
        return problems

    def save_project_dialog(self):
        if not self.dev: return
        f, _ = QFileDialog.getSaveFileName(self, self.t("m_save"), "projet.customlab.json", self.t("proj_filter"))
        if f: self.save_project(f)

    def open_project_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, self.t("m_open"), "", self.t("proj_filter"))
        if f: self.open_project(f)

    def new_project(self):
        self.dev = None; self.sizing = None; self.scale_override = None; self.out_tris = None; self.deco_result = None; self.go(0)

    def show_sources(self):
        from .sources_dialog import SourcesDialog
        SourcesDialog(self, self.lang).exec()
        self.custom.reload_library() if getattr(self.custom, "device", None) not in (None, "unlimbited_arm") else None; self.load_pictures()

    def first_run_check(self):
        """First launch with an empty sources folder: show the window once so the user knows what to download."""
        from . import paths
        from .sources_dialog import status
        if paths.get_setting("sources_prompt_done"): return
        paths.save_setting("sources_prompt_done", True)
        if any(status(pid)[0] is False for pid in ("kinetic_hand", "kinetic_arm", "unlimbited_arm")): self.show_sources()

    def show_tuto(self):
        from .tuto_dialog import TutoDialog
        TutoDialog(self, self.lang).exec()

    def show_profiles(self):
        from .profiles_dialog import BeneficiaryDialog
        dlg = BeneficiaryDialog(self); dlg.exec(); return dlg

    # --- pages
    def build_catalog(self):
        w = QWidget(); w.setObjectName("page"); outer = QVBoxLayout(w); outer.setContentsMargins(2, 6, 2, 6); outer.setSpacing(14)
        self.hello = QLabel(); self.hello.setWordWrap(True); outer.addWidget(self.hello)
        self.b_tuto = QPushButton(); self.b_tuto.setObjectName("chip"); self.b_tuto.clicked.connect(self.show_tuto); outer.addWidget(self.b_tuto, 0, Qt.AlignLeft)
        self.cat_layout = QHBoxLayout(); self.cat_layout.setSpacing(16); self.cards = {}; self.pics = {}
        order = ["phoenix_hand", "unlimbited_arm", "kinetic_hand", "kinetic_arm"]
        for pid, p in sorted(self.profiles.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99):
            f = theme.card(); lay = QVBoxLayout(f); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(8)
            name = QLabel(f"<span style='font-size:17px;font-weight:700;color:{theme.NAVY}'>{p['name']}</span><br><span style='color:{theme.MUTED};font-size:11px'>{p['designer']}</span>"); name.setWordWrap(True)
            badge = QLabel(); info = QLabel(); info.setWordWrap(True); info.setStyleSheet(f"font-size:11px;color:{theme.MUTED}")
            btn = QPushButton(); btn.clicked.connect(lambda _=False, i=pid: self.select(i))
            pic = QLabel(); pic.setFixedHeight(150); pic.setAlignment(Qt.AlignCenter); pic.setStyleSheet(f"color:{theme.MUTED};font-size:11px;background:transparent"); self.pics[pid] = pic
            for x in (pic, name, badge, info): lay.addWidget(x)
            lay.addStretch(1); lay.addWidget(btn); f.setFixedHeight(400); self.cat_layout.addWidget(f)
            self.cards[pid] = (badge, info, btn)
        self.cat_layout.setAlignment(Qt.AlignTop); outer.addLayout(self.cat_layout); outer.addStretch(1); self.stack.addWidget(w); self.load_pictures()

    def load_pictures(self):
        """Device pictures: cached ones at once, missing ones made in a worker thread (never in tests)."""
        self._psig = _Signals(); self._psig.done.connect(self._on_picture); self._ppool = QThreadPool(); self._ppool.setMaxThreadCount(1); self._pids = {}
        for n, pid in enumerate(self.pics):
            c = thumbs.cached(pid)
            if c: self._show_picture(pid, c)
            elif not thumbs.sources(pid): self.pics[pid].setText("Aperçu disponible après la première génération de la pièce" if pid == "unlimbited_arm" else "Aperçu indisponible (fichiers sources absents)")
            elif os.environ.get("CUSTOMLAB_SYNC") != "1":
                self.pics[pid].setText("⏳ Préparation de l'aperçu…"); self._pids[n] = pid; self._ppool.start(_Job(n, lambda q=pid: thumbs.ensure(q), self._psig))

    def _on_picture(self, n, res):
        pid = self._pids.get(n)
        if pid and res[0] == "ok" and res[1]: self._show_picture(pid, res[1])
        elif pid: self.pics[pid].setText("Aperçu indisponible")

    def _show_picture(self, pid, path):
        pm = QPixmap(str(path)); self.pics[pid].setPixmap(pm.scaled(self.pics[pid].width() or 300, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)); self.pics[pid].setText("") if not pm.isNull() else None

    def _direct_edited(self):
        v = round(self.direct_spin.value(), 1); self.scale_override = v if v > 0 else None
        self.sync_direct(); self.recompute()
        if self.stack.currentIndex() == 3: self.show_result()

    def sync_direct(self):
        """Page 2 'direct scale' row: visible for the devices that allow it, shows the value in use and refuses (without correcting) one outside the documented range."""
        L = self.lang; show = self.dev in self.DIRECT; self.direct_row.setVisible(show)
        if not show: return
        self.direct_lab.setText("Ou choisir directement l'échelle :" if L == "fr" else "Or choose the scale directly:")
        self.direct_spin.setSpecialValueText("calculée d'après les mesures" if L == "fr" else "computed from the measures")
        self.direct_spin.blockSignals(True); self.direct_spin.setValue(self.scale_override or 0.0); self.direct_spin.blockSignals(False)
        r = self.scale_range(); v = self.scale_override
        if v is not None and r is not None and not (r[0] - 1e-9 <= v <= r[1] + 1e-9): self.direct_info.setText(f"⚠ {v:g} % hors de la plage documentée ({r[0]:g}–{r[1]:g} %) : refusée"); self.direct_info.setStyleSheet("color:#b00020;font-size:11px")
        else:
            self.direct_info.setStyleSheet(f"color:{theme.MUTED};font-size:11px")
            self.direct_info.setText((f"Plage documentée : {r[0]:g}–{r[1]:g} %. " if r else "") + ("Remplace le calcul d'après les mesures." if L == "fr" else "Replaces the computation from the measures.") if v is not None else (f"Plage documentée : {r[0]:g}–{r[1]:g} %." if r else ""))

    def build_measures(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.m_title = QLabel(); self.m_title.setStyleSheet(f"font-size:16px;font-weight:700;color:{theme.NAVY}")
        self.block = QLabel(); self.block.setWordWrap(True); self.block.setStyleSheet("")
        self.form = QFormLayout(); self.side = QComboBox(); self.part = QComboBox()
        self.fields = {}
        self.help = QLabel(); self.help.setWordWrap(True); self.help.setStyleSheet(f"color:{theme.MUTED}")
        self.live = QTextEdit(); self.live.setReadOnly(True); self.live.setMaximumHeight(300)
        for x in (self.m_title, self.block): lay.addWidget(x)
        top = QHBoxLayout(); top.addLayout(self.form, 1)
        self.schema = QSvgWidget(); self.schema.setFixedSize(460, 205); top.addWidget(self.schema, 0, Qt.AlignTop)
        self.direct_row = QWidget(); dr = QHBoxLayout(self.direct_row); dr.setContentsMargins(0, 0, 0, 0)
        self.direct_lab = QLabel(); self.direct_spin = QDoubleSpinBox(); self.direct_spin.setRange(0, 300); self.direct_spin.setDecimals(1); self.direct_spin.setSingleStep(2.5); self.direct_spin.setSuffix(" %"); self.direct_spin.setMinimumWidth(240)
        self.direct_info = QLabel(); self.direct_info.setStyleSheet(f"color:{theme.MUTED};font-size:11px")
        for x in (self.direct_lab, self.direct_spin, self.direct_info): dr.addWidget(x)
        dr.addStretch(1); self.direct_spin.editingFinished.connect(self._direct_edited)
        self.b_photo = QPushButton(); self.b_photo.clicked.connect(self.measure_on_photo); self.field_labels = {}; self.b_guide = QPushButton(); self.b_guide.clicked.connect(self.show_scale_guide)
        brow = QHBoxLayout(); brow.addWidget(self.b_photo); brow.addWidget(self.b_guide); brow.addStretch(1)
        lay.addLayout(top); lay.addLayout(brow); lay.addWidget(self.direct_row); lay.addWidget(self.help); lay.addWidget(self.live, 1)
        self.side.currentIndexChanged.connect(self.recompute); self.part.currentIndexChanged.connect(self.recompute)
        self.stack.addWidget(w)

    def build_result(self):
        w = QWidget(); h = QHBoxLayout(w); left = QVBoxLayout()
        self.res = QTextEdit(); self.res.setReadOnly(True)
        self.b_scad = QPushButton(); self.b_gen = QPushButton(); self.b_exp = QPushButton(); self.b_exp.setObjectName("primary"); self.b_expall = QPushButton(); self.b_expall.clicked.connect(self.export_all_parts); self.scale_cb = QCheckBox()
        self.b_scad.clicked.connect(self.import_scad)
        self.b_gen.clicked.connect(self.generate); self.b_exp.clicked.connect(self.export_stl)
        self.b_open = QPushButton(); self.b_open.setEnabled(False); self.b_open.clicked.connect(self.open_in_slicer); self.last_3mf = None; self.last_export_dir = None
        self.scale_override = None
        self.scale_row = QWidget(); sr = QHBoxLayout(self.scale_row); sr.setContentsMargins(0, 0, 0, 0)
        self.scale_lab = QLabel(); self.scale_spin = QDoubleSpinBox(); self.scale_spin.setRange(1, 300); self.scale_spin.setDecimals(1); self.scale_spin.setSingleStep(2.5); self.scale_spin.setSuffix(" %")
        self.scale_reset = QPushButton(); self.scale_reset.setObjectName("chip")
        for x in (self.scale_lab, self.scale_spin, self.scale_reset): sr.addWidget(x)
        sr.addStretch(1); self.scale_note = QLabel(); self.scale_note.setWordWrap(True); self.scale_note.setStyleSheet(f"color:{theme.MUTED};font-size:11px")
        self.scale_spin.editingFinished.connect(self._scale_edited); self.scale_reset.clicked.connect(self._scale_reset)
        self.scale_cb.setChecked(True)                                   # sizing rule confirmed on the official SCAD: applied unless unticked
        self.scale_cb.setStyleSheet(f"color:{theme.NAVY}"); self.scale_cb.toggled.connect(lambda *_: self.stack.currentIndex() == 3 and self.show_result())
        for x in (self.res, self.scale_cb, self.scale_row, self.scale_note, self.b_scad, self.b_gen, self.b_exp, self.b_expall, self.b_open): left.addWidget(x)
        self.view = make_view(); h.addLayout(left, 1); h.addWidget(self.view, 2); self.stack.addWidget(w)

    # --- logic
    def toggle_lang(self): self.lang = "en" if self.lang == "fr" else "fr"; self.retranslate()

    def retranslate(self):
        self.setWindowTitle(self.t("title")); self.langbtn.setText(self.t("lang"))
        self.m_file.setTitle(self.t("m_file")); self.m_people.setTitle(self.t("m_people")); self.m_help.setTitle(self.t("m_help")); self.a_tuto.setText(self.t("m_tuto")); self.a_scale.setText(self.t("m_scale")); self.a_src.setText(self.t("m_sources")); self.b_tuto.setText(self.t("tuto_btn")); self.m_recent.setTitle(self.t("m_recent"))
        self.a_new.setText(self.t("m_new")); self.a_open.setText(self.t("m_open")); self.a_save.setText(self.t("m_save")); self.a_prof.setText(self.t("m_prof")); self.m_view.setTitle(self.t("m_view")); self.a_adv.setText(self.t("m_adv")); self.refresh_recent_menu()
        self.hello.setText(f"<span style='font-size:20px;font-weight:700;color:{theme.NAVY}'>{self.t('hello')}</span><br><span style='color:{theme.MUTED}'>{self.t('hello2')}</span>")
        self.disc.setText(self.t("disclaimer")); self.bback.setText(self.t("back")); self.bnext.setText(self.t("next"))
        for pid, (badge, info, btn) in self.cards.items():
            p = self.profiles[pid]; st = p["status"]
            badge.setText(f"<span style='color:white;background:{BADGE[st]};padding:3px 9px;font-weight:700;font-size:10px'>&nbsp;{self.t('status_' + st)}&nbsp;</span>")
            cut = lambda t, n: t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
            full = f"{self.t('license')}: {p['license']['name']}" + (f"<br><span style='color:#b00020'>{self.t('blocked')}: {p['blocking']}</span>" if p.get("blocking") else "") + (f"<br><span style='color:{theme.NAVY}'>{self.t('info')}: {p['notice']}</span>" if p.get("notice") else "")
            info.setText(f"{self.t('license')}: {cut(p['license']['name'], 70)}" + (f"<br><span style='color:#b00020'>{self.t('blocked')}: {cut(p['blocking'], 110)}</span>" if p.get("blocking") else "") + (f"<br><span style='color:{theme.NAVY}'>{self.t('info')}: {cut(p['notice'], 150)}</span>" if p.get("notice") else ""))
            info.setToolTip(f"<div style='width:420px'>{full}</div>")
            btn.setText(self.t("select"))
        self.b_scad.setText(self.t("import_scad")); self.scale_cb.setText(self.t("scale_cb"))
        self.b_open.setText(self.t("open_slicer")); self.b_gen.setText(self.t("generate")); self.b_exp.setText(self.t("export_dir") if self.dev in DECO_DEVICES else self.t("export")); self.b_expall.setText(self.t("export_all"))
        self.custom.retranslate(self.lang)
        self.side.blockSignals(True); self.side.clear()
        self.side.addItem(self.t("left"), "left"); self.side.addItem(self.t("right"), "right"); self.side.blockSignals(False)
        if self.dev: self.fill_measures()
        self.go(self.stack.currentIndex())

    def go(self, i):
        i = max(0, min(3, i))
        if i >= 1 and not self.dev: i = 0
        changed = self.stack.currentIndex() != i
        self.stack.setCurrentIndex(i); self.header.steps.set_step(i)
        if changed: theme.fade_in(self.stack.currentWidget())
        self.step.setText([self.t("catalog"), self.t("measures"), self.t("custom"), self.t("result")][i])
        self.bback.setEnabled(i > 0); self.bnext.setEnabled(i < 3 and self.dev is not None)
        if i == 2:
            self.custom.setEnabled(self.dev in DECO_DEVICES); self.refresh_arm_bar()
            self.update_mirror(); self.custom.update_model()
        if i != 3: self._rgen += 1                                        # leaving the result page drops a pending background result
        if i == 3: self.show_result()

    def select(self, pid):
        if pid != self.dev: self.custom.clear_part(); self.arm_gen = None; self.scale_override = None
        self.custom.set_device(pid)
        self.dev = pid; self.scad = None; self.out_tris = None; self.deco_result = None
        self.fill_measures(); self.go(1)

    def update_mirror(self, reload=True):
        """Left Kinetic hand/arm = X-mirror of the RH models, applied before decorating (arm: only the files named RH, manual p. 22)."""
        left = self.side.currentData() == "left"
        if self.dev == "kinetic_hand": self.custom.mirror_rule = None; flag = left
        elif self.dev == "kinetic_arm":
            self.custom.mirror_rule = lambda p: left and kinetic_arm.part_info(Path(p).name, self.sizing.derived)["mirror_left"] if self.sizing else False
            flag = self.custom.mirror_rule(self.custom.part_path) if self.custom.part_path else False
        else: self.custom.mirror_rule = None; flag = False
        if reload: self.custom.set_mirror(flag)
        else: self.custom.mirror_x = flag

    def arm_part(self):
        """Per-file rules of the selected Kinetic Arm part, or None."""
        if self.dev != "kinetic_arm" or self.sizing is None or not self.custom.part_path: return None
        return kinetic_arm.part_info(Path(self.custom.part_path).name, self.sizing.derived)

    def fill_measures(self):
        p = self.profiles[self.dev]; L = self.lang; self.sync_direct()
        while self.form.rowCount():
            row = self.form.takeRow(0)
            for it in (row.labelItem, row.fieldItem):
                if it and it.widget() and it.widget() not in (self.side, self.part):
                    it.widget().deleteLater()
                elif it and it.widget():
                    it.widget().setParent(None)
        self.fields = {}
        self.m_title.setText(p["name"])
        self.block.setText((f"<span style='color:#b00020'>{self.t('blocked')}: {p['blocking']}</span><br>" if p.get("blocking") else "") + (f"<span style='color:{theme.NAVY}'>{self.t('info')}: {p['notice']}</span>" if p.get("notice") else "")); self.block.setTextFormat(Qt.RichText)
        self.part.blockSignals(True); self.part.clear(); self.part.addItems(p["parts"]); self.part.blockSignals(False)
        self.form.addRow(self.t("side"), self.side)
        if p["parts"]: self.form.addRow(self.t("part"), self.part)
        specs = p.get("wizard_inputs") or p["inputs"]
        helps = []
        for s in specs:
            sp = spin(val=s.get("default") or 0.0); sp.valueChanged.connect(self.recompute)
            self.fields[s["id"]] = sp; self.form.addRow(s[f"label_{L}"], sp); self.field_labels[s["id"]] = s[f"label_{L}"]
            if s.get(f"help_{L}"): helps.append(f"<b>{s[f'label_{L}']}</b>: {s[f'help_{L}']}")
        self.help.setText("<br>".join(helps)); self.b_photo.setText(self.t("photo_btn")); self.b_guide.setText(self.t("scale_btn")); self.b_guide.setVisible(True); self.b_photo.setVisible(any(k.endswith("_mm") for k in self.fields)); self.update_schema(); self.recompute()

    def show_scale_guide(self):
        from .scale_guide_dialog import ScaleGuideDialog
        ScaleGuideDialog(self, self.lang, self.dev or "phoenix_hand", {k: f.value() for k, f in self.fields.items()}).exec()

    def measure_on_photo(self):
        """Opens the photo ruler: the measured width/length goes into the chosen field (the usual range checks then apply)."""
        from .photo_measure import PhotoMeasureDialog
        targets = [(self.field_labels.get(k, k), k) for k in self.fields if k.endswith("_mm")]
        d = PhotoMeasureDialog(self, self.lang, targets)
        if d.exec() and d.result_value: self.fields[d.result_value[0]].setValue(d.result_value[1])

    def update_schema(self):
        name = SCHEMA.get(self.dev)
        f = ASSETS / f"{name}_{self.lang}.svg" if name else None
        self.schema.setVisible(bool(f and f.is_file()))
        if f and f.is_file():
            self.schema.load(str(f)); d = self.schema.renderer().defaultSize()
            if d.width() > 0: self.schema.setFixedSize(d.width(), d.height())

    DIRECT = ("phoenix_hand", "kinetic_hand")          # devices whose scale can be chosen directly (no measures needed)

    def scale_percent(self):
        """Scale CustomLab applies at export: the volunteer's own value if any (also without measures for the Phoenix and the Kinetic Hand),
        else the computed one. None if the device is not scaled here or nothing gives a scale."""
        if self.scale_override is not None and (self.dev in self.DIRECT or (self.dev in SCALABLE and self.computed_scale() is not None)): return self.scale_override
        return self.computed_scale()

    def scale_range(self): return SCALE_RANGE.get(self.dev)

    def scale_out_of_range(self):
        r = self.scale_range(); v = self.scale_percent()
        return r is not None and v is not None and self.scale_cb.isChecked() and not (r[0] - 1e-9 <= v <= r[1] + 1e-9)

    def computed_scale(self):
        """Uniform scale CustomLab computes from the measures (None if the device is not scaled here or sizing is invalid)."""
        if self.sizing is None: return None
        if self.dev == "phoenix_hand": return self.sizing.scad_defines.get("HandPerc")
        if self.dev == "kinetic_hand": return self.sizing.derived.get("scale_percent")
        if self.dev == "kinetic_arm":
            a = self.arm_part(); return None if a is None or a["prescaled"] else a["scale_percent"]
        return None

    def values(self): return {k: s.value() for k, s in self.fields.items()}

    def compute(self):
        """Returns (SizingResult|None, text). Never clamps; errors are shown verbatim."""
        p = self.profiles[self.dev]; v = self.values(); side = self.side.currentData(); part = self.part.currentText()
        if p["status"] == "unavailable":
            return None, self.t("no_sizing")
        try:
            if p.get("method") == "kinetic_arm_chart":
                if v["hand_mm"] <= 0 or v["elbow_mm"] <= 0 or v["resid_mm"] <= 0: return None, ""
                r = compute_kinetic_arm_sizing(side, v["hand_mm"], v["elbow_mm"], v["resid_mm"], v.get("sound_mm", 0.0))
            elif p.get("method") == "kinetic_chart":
                if v["wrist_mm"] <= 0 or v["palm_mm"] <= 0: return None, ""
                r = compute_kinetic_sizing(side, "", v["wrist_mm"], v["palm_mm"], v.get("max_palm_mm", 0.0), v.get("sound_len_mm", 0.0))
            elif p.get("method") == "phoenix_wrist":
                if v["wrist_mm"] <= 0: return None, ""
                r = compute_phoenix_sizing(side, part, v["wrist_mm"], v["margin_mm"])
            else:
                if min(v.values()) <= 0: return None, ""
                r = compute_sizing(self.dev, side, part, v)
        except (SizingError, phoenix.OutOfRange, ValueError) as e:
            return None, str(e)
        return r, ""

    def describe(self, r, msg):
        """HTML for the measures page: key figures first, then the messages sorted by severity (block / check / info)."""
        L = self.lang
        if r is None:
            if msg: return M.messages_html([(msg, M.BLOCK)], L)
            hint = "Saisissez les mesures ci-dessus (en mm) : l'échelle calculée et les pièces conseillées s'afficheront ici." if L == "fr" else "Enter the measures above (in mm): the computed scale and the suggested parts will appear here."
            return f"<p style='color:{theme.MUTED};font-size:14px;margin:18px'>👆 {hint}</p>"
        head = ""
        if self.dev == "phoenix_hand":
            lo, hi = phoenix.wrist_range_mm(r.measurements["margin_mm"])
            head = (f"<h3 style='margin:2px 0'>{self.t('scale')} : {r.scad_defines['HandPerc']} %</h3>"
                    f"<p style='margin:2px 0'>{self.t('usable')} : {lo:.1f}–{hi:.1f} mm</p>")
        elif self.dev == "kinetic_arm":
            d = r.derived; fr = L == "fr"
            head = (f"<h3 style='margin:2px 0'>{'Composants inférieurs' if fr else 'Lower components'} : {d['lower_scale']:g} % · {'avant-bras type' if fr else 'forearm type'} {d['forearm_type']} · {'composants supérieurs' if fr else 'upper components'} {d['upper_scale']:g} %</h3>"
                    f"<h3 style='margin:2px 0'>Insert {d['insert']} · {'languette' if fr else 'tongue'} {d['tongue']} · {'doublure néoprène, jeu' if fr else 'neoprene liner set'} {d['liner_set']}</h3>"
                    f"<p style='margin:2px 0'>{'Fichiers pré-échelonnés' if fr else 'Pre-scaled files'} : {'paume et verrouillage' if fr else 'palm and locking mechanism'} {d['palm_scale']:g} % · {'tendeurs' if fr else 'tensioners'} {d['tensioner_scale']:g} % · "
                    f"{'bras gauche : symétrie de certaines pièces (manuel)' if (fr and r.side == 'left') else ('left arm: some parts mirrored (manual)' if r.side == 'left' else ('bras droit : fichiers tels quels' if fr else 'right arm: files as supplied'))}</p>")
        elif self.dev == "kinetic_hand":
            d = r.derived; row = d["design"]
            head = (f"<h3 style='margin:2px 0'>{self.t('scale')} : {d['scale_percent']:g} % ({'uniforme, toutes les pièces' if L == 'fr' else 'uniform, all parts'})</h3>"
                    f"<h3 style='margin:2px 0'>{'Insert souple' if L == 'fr' else 'Soft insert'} : {d['insert']} ({d['insert_mm']} mm)</h3>"
                    f"<p style='margin:2px 0'>{'Poignet mesuré' if L == 'fr' else 'Measured wrist'} {r.measurements['wrist_mm']:g} + 3 = {d['padded_wrist_mm']:g} mm · "
                    f"{'espace libre dans la paume' if L == 'fr' else 'free palm space'} {d['space_mm']:g} mm · {'main gauche : symétrie en X' if (L == 'fr' and r.side == 'left') else ('left hand: mirrored in X' if r.side == 'left' else ('main droite : fichiers tels quels' if L == 'fr' else 'right hand: files as supplied'))}</p>"
                    f"<p style='margin:2px 0;color:#555'>{'Modèle à cette échelle' if L == 'fr' else 'Design at this scale'} : " + " · ".join(f"{k.replace('_', ' ')} {row[k]:g}" for k in ("palm_length", "wrist_width", "max_palm_width", "overall_hand_length")) + " mm</p>")
            if d.get("advanced"):
                a = d["advanced"]; head += (f"<p style='margin:2px 0;color:#555'>{'Échelle avancée (information, non appliquée) : XY' if L == 'fr' else 'Advanced scaling (information, not applied): XY'} {a['scale_xy']:g} % / Z {a['scale_z']:g} % · insert {a['insert']}. "
                                          f"{'Peut affecter le fonctionnement (manuel).' if L == 'fr' else 'May affect function (manual).'}</p>")
        else:
            head = "<p style='margin:2px 0'>" + " · ".join(f"{k} = {x}" for k, x in r.scad_defines.items()) + "</p>"
            if r.derived.get("HandPerc"):
                head += (f"<h3 style='margin:2px 0'>{'Échelle de la main' if L == 'fr' else 'Hand scale'} : {r.derived['HandPerc']} %</h3>"
                         f"<p style='margin:2px 0'>{'calculée par le SCAD : HandLen / 135 × 100 (la main, les doigts et les broches sont mis à cette échelle)' if L == 'fr' else 'computed by the SCAD: HandLen / 135 × 100 (hand, fingers and pins use this scale)'}</p>")
        badge = f"<p><span style='color:white;background:{BADGE.get(r.status, '#555')};padding:2px 6px'>{self.t('status_' + r.status)}</span></p>"
        items = [(w, None) for w in r.warnings]
        return head + badge + M.messages_html(items, L)

    def recompute(self, *_):
        if not self.dev: return
        self.sizing, msg = self.compute(); self.live.setHtml(self.describe(self.sizing, msg))
        self.bnext.setEnabled(self.stack.currentIndex() < 3)

    def result_html(self, deco_msgs):
        """Structured summary of step 4: sizing, decoration, pieces/filaments, then messages by severity."""
        L = self.lang; ph = self.dev in SCALABLE; dd = self.dev in DECO_DEVICES; sp = self.custom.spec() if dd and self.custom.part_path else None
        h = [f"<h3 style='margin:2px 0'>{self.profiles[self.dev]['name']}</h3>"]
        if self.sizing is not None and self.dev == "unlimbited_arm" and self.sizing.derived.get('HandPerc'):
            h.append(f"<p style='margin:2px 0'><b>{self.sizing.part} :</b> " + " · ".join(f"{k} = {x}" for k, x in self.sizing.measurements.items()) + f" — {'échelle de la main' if L == 'fr' else 'hand scale'} {self.sizing.derived['HandPerc']} %</p>")
        if self.sizing is not None and self.dev == "kinetic_hand":
            d = self.sizing.derived
            h.append(f"<p style='margin:2px 0'><b>{self.t('scale')} :</b> {self.scale_percent():g} % — " + (("appliquée à l'export" if L == "fr" else "applied on export") if self.scale_cb.isChecked() else ("non appliquée : taille d'origine (100 %)" if L == "fr" else "not applied: original size (100 %)")) + f" · {'insert' if L == 'fr' else 'insert'} {d['insert']} ({d['insert_mm']} mm)</p>")
        elif self.sizing is not None and self.dev == "kinetic_arm":
            d = self.sizing.derived; a = self.arm_part()
            if a is not None:
                grp = {"lower": "composants inférieurs" if L == "fr" else "lower components", "upper": "composants supérieurs" if L == "fr" else "upper components"}[a["group"]]
                if a["prescaled"]: h.append(f"<p style='margin:2px 0'><b>{Path(self.custom.part_path).name} :</b> {a['note']}</p>")
                else: h.append(f"<p style='margin:2px 0'><b>{self.t('scale')} :</b> {self.scale_percent():g} % ({grp}) — " + (("appliquée à l'export" if L == "fr" else "applied on export") if self.scale_cb.isChecked() else ("non appliquée : taille d'origine (100 %)" if L == "fr" else "not applied: original size (100 %)")) + "</p>")
                if self.sizing.side == "left": h.append(f"<p style='margin:2px 0'>{'Bras gauche' if L == 'fr' else 'Left arm'} : " + (("pièce symétrisée en X avant décoration" if L == "fr" else "part mirrored in X before decorating") if a["mirror_left"] else ("pièce générique, non symétrisée" if L == "fr" else "generic part, not mirrored")) + "</p>")
            h.append(f"<p style='margin:2px 0'>{'Sélection' if L == 'fr' else 'Selection'} : {'avant-bras type' if L == 'fr' else 'forearm type'} {d['forearm_type']} · insert {d['insert']} · {'languette' if L == 'fr' else 'tongue'} {d['tongue']} · {'doublure' if L == 'fr' else 'liner set'} {d['liner_set']}</p>")
        elif self.sizing is not None and ph:
            lo, hi = phoenix.wrist_range_mm(self.sizing.measurements["margin_mm"])
            applied = self.scale_cb.isChecked()
            h.append(f"<p style='margin:2px 0'><b>{self.t('scale')} :</b> {self.scale_percent():g} % — " +
                     (("appliquée à l'export" if L == "fr" else "applied on export") if applied else ("non appliquée : taille d'origine conservée" if L == "fr" else "not applied: original size kept")) +
                     f" ({self.t('usable')} {lo:.1f}–{hi:.1f} mm)</p>")
        if self.sizing is None and ph and self.scale_override is not None and self.dev in self.DIRECT:
            h.append(f"<p style='margin:2px 0'><b>{self.t('scale')} :</b> {self.scale_override:g} % — " + ("choisie directement (sans mesures)" if L == "fr" else "chosen directly (no measures)") + " — " + (("appliquée à l'export" if L == "fr" else "applied on export") if self.scale_cb.isChecked() else ("non appliquée : taille d'origine (100 %)" if L == "fr" else "not applied: original size (100 %)")) + "</p>")
        if sp is not None:
            names = {"fr": {"relief": "relief", "engrave": "gravure", "inlay": "incrustation affleurante"}, "en": {"relief": "relief", "engrave": "engraving", "inlay": "flush inlay"}}[L]
            camo = sp.kind == "camo"
            one = lambda x: x.text if x.kind == "text" else (self.custom.t("camo_" + x.camo_style) + f" #{x.camo_seed}" if x.kind == "camo" else Path(x.path).name)
            what = " + ".join(one(x) for x in (sp,) + tuple(sp.extra) if not deco.spec_empty(x)) or one(sp)
            sizetxt = (f"{'taches' if L == 'fr' else 'patches'} ~{sp.camo_scale_mm:g} mm" if camo else f"{sp.size_mm:g} mm")
            h.append(f"<p style='margin:2px 0'><b>{'Décoration' if L == 'fr' else 'Decoration'} :</b> {what or '—'} · {names[sp.mode]} · {sizetxt} · {sp.depth_mm:g} mm · {'qualité' if L == 'fr' else 'quality'} {sp.res_mm:g} mm</p>")
            if camo:
                from . import camo as C
                bc, bn = C.PALETTES[sp.camo_style]["base"]; h.append(f"<p style='margin:2px 0'>{self.custom.t('camo_base').format(c=bn[L] + ' ' + bc)}</p>")
            r = self.deco_result
            if r is not None and not r.errors and r.layers:
                h.append("<p style='margin:2px 0'><b>" + ("Pièces et filaments" if L == "fr" else "Parts and filaments") + " :</b></p><table cellspacing='4'>")
                h.append(f"<tr><td>■</td><td>{'Base (pièce d' + chr(39) + 'origine)' if L == 'fr' else 'Base (original part)'}</td><td>→ filament 1</td></tr>")
                for n, lay in enumerate(r.layers, start=2):
                    h.append(f"<tr><td style='color:{lay['hex']}'>■</td><td>{lay['hex']}</td><td>→ filament {n}</td></tr>")
                h.append("</table>")
            elif r is not None and not r.errors and sp.mode in ("inlay", "relief") and r.deco_triangles:
                h.append("<p style='margin:2px 0'>" + ("Base → filament 1, décoration → filament 2" if L == "fr" else "Base → filament 1, decoration → filament 2") + "</p>")
        h.append(M.messages_html(deco_msgs, L))
        h.append(f"<p style='margin:6px 0;color:#555'>{deco.DISCLAIMER if L == 'fr' else 'EXPERIMENTAL decoration. Functional areas (joints, pin holes, cable paths, skin-contact surfaces) are not detected automatically; no physical or clinical validation.'}</p>")
        return "".join(h)

    def _scale_edited(self):
        c = self.computed_scale(); v = round(self.scale_spin.value(), 1)
        self.scale_override = None if (c is not None and abs(v - c) < 0.05) else v
        self.sync_direct(); self.show_result()

    def _scale_reset(self): self.scale_override = None; self.sync_direct(); self.show_result()

    def refresh_scale_row(self):
        """Final size control: the motif is drawn at standard size (100 %) and follows the device scale on export."""
        c = self.computed_scale(); L = self.lang; show = self.dev in SCALABLE and self.scale_cb.isChecked() and self.scale_percent() is not None
        self.scale_row.setVisible(show); self.scale_note.setVisible(show)
        if not show: return
        r = self.scale_range(); v = self.scale_percent(); sp = self.custom.spec() if self.custom.part_path else None
        self.scale_lab.setText("Taille finale de l'appareil :" if L == "fr" else "Final device size:"); self.scale_reset.setText(f"{'Valeur calculée' if L == 'fr' else 'Computed value'} ({c:g} %)" if c is not None else ""); self.scale_reset.setVisible(self.scale_override is not None and c is not None)
        self.scale_spin.blockSignals(True); self.scale_spin.setValue(v); self.scale_spin.blockSignals(False)
        motif = (f" {'Un motif de' if L == 'fr' else 'A motif of'} {sp.size_mm:g} mm {'devient' if L == 'fr' else 'becomes'} {sp.size_mm * v / 100:.1f} mm." if sp is not None and sp.kind != "camo" and not self.custom.is_empty() else "")
        rng = f"{r[0]:g}–{r[1]:g} %" if r else ""
        self.scale_note.setText((f"La personnalisation est dessinée à la taille standard (100 %) puis réduite/agrandie avec la pièce.{motif} Plage documentée : {rng}." if L == "fr" else f"The customisation is drawn at standard size (100 %) and scaled with the part.{motif} Documented range: {rng}."))

    def show_result(self):
        self.recompute(); ph = self.dev in SCALABLE; dd = self.dev in DECO_DEVICES; self.refresh_scale_row()
        self.scale_cb.setText(self.t("scale_cb_kinetic") if self.dev in ("kinetic_hand", "kinetic_arm") else self.t("scale_cb"))
        self.b_scad.setVisible(False); self.b_gen.setVisible(False); self.scale_cb.setVisible(ph)         # the arm is generated on page 3

        self.b_exp.setText(self.t("export_dir") if dd else self.t("export")); self.b_expall.setVisible(self.dev in ("phoenix_hand", "kinetic_hand", "kinetic_arm"))
        one = not self.advanced and self.b_expall.isVisibleTo(self)                    # simple mode: a single "export everything" button
        self.b_expall.setText(self.t("export_one" if one else "export_all")); self.b_exp.setVisible(not one); self.b_open.setVisible(not one)
        self.b_expall.setObjectName("primary" if one else ""); self.b_expall.style().unpolish(self.b_expall); self.b_expall.style().polish(self.b_expall)
        base = []
        if self.sizing is not None: base += [(w, None) for w in self.sizing.warnings]
        elif self.live.toPlainText(): base.append((self.live.toPlainText(), M.BLOCK))
        self._rgen += 1; self.out_tris = None; self.deco_result = None
        if not dd: self._render_result(base); return
        self.custom.ensure_fresh(); self.b_exp.setEnabled(False)
        if self.custom.sync or not self.custom.part_path or self._arm_stale():
            self._render_result(base + self._phoenix_result()); return
        # heavy part (solid construction, up to several seconds at fine quality) runs in a worker thread
        self._rmsgs = base; self.res.setHtml(f"<p style='color:{theme.NAVY}'>{self.custom.t('busy')}</p>")
        inputs = self.custom.result_inputs(); gen = self._rgen
        self._rpool.start(_RJob(gen, lambda: CustomizePage.compute_result_raw(*inputs), self._rsig))

    def _on_result(self, gen, res):
        if gen != self._rgen: return                                   # the user went elsewhere / changed something meanwhile
        base = self._rmsgs or []
        if res[0] == "err": self.deco_result = None; self._render_result(base + [(str(res[1]), M.BLOCK)]); return
        self._render_result(base + self._phoenix_result(res[1]))

    def wait_result(self):
        """Wait for a pending background computation (used before exporting and by tests)."""
        self.custom.ensure_fresh(); self._rpool.waitForDone(); QApplication.processEvents()

    def _render_result(self, msgs):
        if self.dev in SCALABLE and self.scale_cb.isChecked() and self.scale_percent() is None and self.out_tris is not None:
            msgs = msgs + [("Échelle demandée mais non calculable : saisissez les mesures (étape 2), choisissez l'échelle directement (%) ou décochez l'option.", M.BLOCK)]
        if self.scale_out_of_range():
            r = self.scale_range(); msgs = msgs + [((f"Échelle {self.scale_percent():g} % hors de la plage documentée ({r[0]:g}–{r[1]:g} %) : refusée, aucune correction automatique." if self.lang == "fr" else f"Scale {self.scale_percent():g} % is outside the documented range ({r[0]:g}–{r[1]:g} %): refused, no automatic correction."), M.BLOCK)]
        blocked = (self.dev in SCALABLE and self.scale_cb.isChecked() and self.scale_percent() is None) or self.scale_out_of_range()
        self.res.setHtml(self.result_html(msgs) if self.dev else ""); self.b_gen.setEnabled(self.sizing is not None); self.b_exp.setEnabled(self.out_tris is not None and not blocked)
        if self.out_tris is None:
            self.view.message = ""; self.view.set_triangles([])

    def _phoenix_result(self, r=None):
        """Original STL (size untouched) + experimental decoration. Scaling only on export and only if ticked.
        Returns the engine messages as [(text, default_severity)]."""
        self.out_tris = None; self.deco_result = None
        if self.dev == "unlimbited_arm":
            if self.sizing is None: return [("Mesures manquantes ou hors plage : corrigez-les à l'étape 2.", M.BLOCK)]
            if self._arm_stale(): return [("La pièce générée ne correspond pas aux mesures actuelles : générez-la à l'étape 3.", M.BLOCK)]
        if not self.custom.part_path: return [("Choisissez d'abord la pièce à l'étape 3.", M.BLOCK)]
        r = r if r is not None else self.custom.compute_result(); self.deco_result = r
        if r.errors: return [(e, M.BLOCK) for e in r.errors] + [(w, None) for w in r.warnings]
        self.out_tris = r.triangles
        mode = self.custom.spec().mode
        hlc = r.preview_colors or None
        if r.preview_triangles: self.view.set_triangles(r.preview_triangles, r.preview_highlight, overlay=True, hl_colors=hlc)
        else: self.view.set_triangles(r.triangles, r.preview_highlight if (hlc and mode == "relief") else (len(r.deco_triangles) if mode == "relief" else 0), hl_colors=hlc if mode == "relief" else None)
        self.view.set_basis(self.custom.view_basis()); self.view.face_front()      # straight-on, same orientation as the placement view
        return [(w, None) for w in r.warnings]

    # ---- Unlimbited Arm: parts are generated from the official SCAD (supplied locally), then customised like any STL
    def _arm_stale(self):
        return self.dev == "unlimbited_arm" and (self.sizing is None or not self.arm_gen or self.arm_gen["defines"] != self.sizing.scad_defines)

    def refresh_arm_bar(self):
        c = self.custom
        if self.dev != "unlimbited_arm": return
        prof = self.profiles["unlimbited_arm"]
        if armgen.scad_path(prof) is None: c.set_gen_status(c.t("gen_noscad"), enabled=False); return
        if self.sizing is None: c.set_gen_status(c.t("gen_need"), enabled=False); return
        part = self.sizing.part; est = prof.get("render_times_s", {}).get(part)
        txt = (c.t("gen_ready").format(part=part) + (f" (≈ {est / 60:.0f} min)" if est and est >= 60 else ""))
        if self.arm_gen and not self._arm_stale(): txt = c.t("gen_done").format(part=part)
        c.set_gen_status(txt, enabled=True)

    def generate_arm_part(self):
        """Render the selected arm part for the current measures (cached). Runs in a worker thread (a Cuff takes minutes)."""
        if self.dev != "unlimbited_arm" or self.sizing is None: return
        defines = dict(self.sizing.scad_defines); self._ggen += 1; gen = self._ggen
        job = lambda: armgen.generate_part("unlimbited_arm", defines)
        if self.custom.sync: self._on_generated(gen, ("ok", job()), defines); return
        self.custom.set_gen_status(self.custom.t("gen_busy").format(part=defines["part"]), busy=True, enabled=False); self._gdefs = defines
        self._gpool.start(_RJob(gen, job, self._gsig))

    def _on_generated(self, gen, res, defines=None):
        defines = defines or getattr(self, "_gdefs", None)
        if gen != self._ggen or defines is None: return
        if res[0] == "err":
            self.custom.set_gen_status(self.custom.t("gen_fail").format(err=str(res[1])[:200]), enabled=True); return
        path, cached = res[1]; self.arm_gen = {"defines": defines, "path": path}
        self.custom.set_part(str(path)); self.refresh_arm_bar()
        a = getattr(self, "_pending_preset", None)
        if a is not None: self._pending_preset = None; _apply_deco_preset(self.custom, a, centre=(a.u == 0 and a.v == 0))

    def wait_generation(self): self._gpool.waitForDone(); QApplication.processEvents()

    def load_stl(self, f):
        self.src_path = f; self.custom.set_part(f); self._phoenix_result(); self.b_exp.setEnabled(self.out_tris is not None)

    def import_scad(self):
        f, _ = QFileDialog.getOpenFileName(self, "SCAD", "", "OpenSCAD (*.scad)")
        if f: self.scad = f

    def generate(self):
        """Unlimbited Arm: render the user-provided official .scad with the validated defines."""
        if self.sizing is None: return
        try:
            if self.scad:
                with tempfile.TemporaryDirectory() as d:
                    self.out_tris = read_stl(openscad.render(self.scad, Path(d) / "o.stl", self.sizing.scad_defines))
            else:
                self.view.message = "Fournir le .scad officiel / Provide the official .scad"; self.view.update(); return
        except Exception as e:
            QMessageBox.warning(self, self.t("err"), str(e)); return
        self.view.set_basis(None); self.view.set_triangles(self.out_tris); self.b_exp.setEnabled(True)

    def scale_for_part(self, path):
        """(scale %, error) applied on export to ANY part of the current device, mirroring the single-part rules."""
        if self.dev not in SCALABLE or not self.scale_cb.isChecked(): return None, None
        if self.dev == "kinetic_arm":
            if self.sizing is None: return None, "Échelle demandée mais non calculable : saisissez les mesures (étape 2) ou décochez l'option."
            a = kinetic_arm.part_info(Path(path).name, self.sizing.derived); v = None if a["prescaled"] else a["scale_percent"]
        else:
            v = self.scale_percent()
            if v is None: return None, "Échelle demandée mais non calculable : saisissez les mesures (étape 2), choisissez l'échelle directement (%) ou décochez l'option."
        r = self.scale_range()
        if v is not None and r is not None and not (r[0] - 1e-9 <= v <= r[1] + 1e-9): return None, f"Échelle {v:g} % hors de la plage documentée ({r[0]:g}–{r[1]:g} %)."
        return v, None

    def camo_batch(self):
        from .batch_dialog import BatchDialog
        if not self.custom.items: return
        c = self.custom; ctx = {"mirror_for": (lambda p: bool(c.mirror_rule(p)) if c.mirror_rule else c.mirror_x), "scale_for": self.scale_for_part, "extra": self.export_extra}
        BatchDialog(self, self.lang, c.items, c.spec(), ctx, c.part_path).exec()

    def export_all_parts(self):
        """All parts of the device at the export scale; the customised part keeps its decoration."""
        from .export_all_dialog import ExportAllDialog
        c = self.custom
        if not c.items: return
        ctx = {"mirror_for": (lambda p: bool(c.mirror_rule(p)) if c.mirror_rule else c.mirror_x), "scale_for": self.scale_for_part, "extra": self.export_extra}
        s = c.spec(); dec = (c.part_path, s, list(c.zones)) if (c.part_path and not c._no_artwork(s)) else None
        pct = self.scale_percent() if self.scale_cb.isChecked() and self.dev != "kinetic_arm" else None
        txt = (f" ({pct:g} %)" if pct else (" (selon chaque pièce)" if self.lang == "fr" else " (per part)") if (self.scale_cb.isChecked() and self.dev == "kinetic_arm") else (" (échelle d'export non cochée : 100 %)" if self.lang == "fr" else " (export scale unticked: 100 %)"))
        ExportAllDialog(self, self.lang, c.items, dec, ctx, txt, c.part_path, quick=not self.advanced).exec()

    def export_extra(self):
        """Provenance block written next to every exported part."""
        arm = {"scad": self.profiles["unlimbited_arm"].get("official_scad"), "defines": self.arm_gen["defines"]} if (self.dev == "unlimbited_arm" and self.arm_gen) else None
        return {"device": self.dev, "arm_generation": arm, "sizing": {"measurements": self.sizing.measurements, "scad_defines": self.sizing.scad_defines, "status": self.sizing.status,
                            "warnings": self.sizing.warnings} if self.sizing else None,
                 "sizing_rule_confirmed_for_this_source": True,
                 "note": ("Échelle uniforme (HandPerc) vérifiée sur le SCAD officiel 1674320 ; la valeur de 43 mm vient de la page e-NABLE France (non mesurée). Essayer le gabarit Phoenix avant impression." if self.dev == "phoenix_hand" else "Kinetic Hand : échelle uniforme du tableau « Hand Scaling Chart » (manuel Free 3D Hands, annexe 1) ; main gauche = symétrie en X des fichiers RH100 %. Imprimer une paume d'essai avant tout assemblage. Aucun essayage ni impression : à valider par un bénévole compétent." if self.dev == "kinetic_hand" else "Kinetic Arm : sélection et échelles du manuel Free 3D Hands (étapes 3 à 8) ; fichiers pré-échelonnés non remis à l'échelle ; pièces RH symétrisées en X pour un bras gauche. Imprimer un bras d'essai avant le bras final. Aucun essayage ni impression : à valider par un bénévole compétent." if self.dev == "kinetic_arm" else "Pièce générée par le SCAD officiel UnLimbited Arm v2.1 aux mesures indiquées (A = BicepCircum, B = ForearmLen, C = HandLen). Aucun essayage ni impression : à valider par un bénévole e-NABLE compétent.")}

    def export_to(self, out_dir):
        """Phoenix export: STL + JSON sheet + attribution, outside the source folder."""
        self.wait_result()
        if self.deco_result is None or self.deco_result.errors: raise deco.DecoError("Nothing valid to export")
        scale = None
        if self.dev in SCALABLE and self.scale_cb.isChecked():
            scale = self.scale_percent()
            if scale is None: raise deco.DecoError("Échelle demandée mais non calculable : saisissez les mesures (étape 2), choisissez l'échelle directement (%) ou décochez l'option.")
            if self.scale_out_of_range(): raise deco.DecoError("Échelle hors de la plage documentée.")
        extra = self.export_extra()
        out = deco.export_result(self.deco_result, self.custom.part_path, self.custom.spec(), out_dir, self.custom.zones, scale, extra)
        self.last_export_dir = Path(out).parent; m = next(self.last_export_dir.glob("*_Bambu_pret.3mf"), None)
        self.last_3mf = m if (m and self.custom.spec().mode in ("inlay", "relief")) else None
        self.b_open.setEnabled(self.last_3mf is not None)
        return out

    def open_in_slicer(self):
        import os, subprocess
        if not self.last_3mf: return
        try:
            if sys.platform == "darwin": subprocess.Popen(["open", str(self.last_3mf)])
            elif sys.platform.startswith("win"): os.startfile(str(self.last_3mf))     # default .3mf application
            else: subprocess.Popen(["xdg-open", str(self.last_3mf)])
        except Exception as e: QMessageBox.warning(self, self.t("err"), str(e))

    def export_stl(self):
        if self.dev in DECO_DEVICES:
            d = QFileDialog.getExistingDirectory(self, self.t("export_dir"))
            if not d: return
            try: out = self.export_to(d)
            except Exception as e: QMessageBox.warning(self, self.t("err"), str(e)); return
            self.res.append(f"\n{self.t('exported')}: {out}" + (f"\n→ {self.last_3mf.name} (prêt pour Bambu Studio, filaments déjà assignés)" if self.last_3mf else "")); return
        f, _ = QFileDialog.getSaveFileName(self, "STL", f"{self.dev}.stl", "STL (*.stl)")
        if f and self.out_tris: write_stl(f, self.out_tris)


def _apply_deco_preset(c, a, centre=False):
    if a.logo:
        kind = "svg" if a.logo.lower().endswith(".svg") else "image"
        c.kind.setCurrentIndex(c.kind.findData(kind)); c.svg_path = str(Path(a.logo).resolve())
    c.size.setValue(a.size); c.depth.setValue(a.depth); c.ncol.setValue(a.colors)
    c.mode.setCurrentIndex(c.mode.findData(a.mode)); c.qual.setCurrentIndex(c.qual.findData(a.res))
    if centre and c.hm is not None: c.place(c.hm.u0 + c.hm.shape[0] * c.hm.res / 2, c.hm.v0 + c.hm.shape[1] * c.hm.res / 2)
    else: c.place(a.u, a.v)


def preset_arm(w, a):
    """Open the Unlimbited Arm with measures A/B/C and the part generated, then place the motif at the centre of the part."""
    w.select("unlimbited_arm"); w.side.setCurrentIndex(max(0, w.side.findData(a.side))); w.part.setCurrentIndex(max(0, w.part.findText(a.arm_part)))
    w.fields["BicepCircum"].setValue(a.a); w.fields["ForearmLen"].setValue(a.b); w.fields["HandLen"].setValue(a.c); w.recompute()
    w.go(2)
    if w.sizing is None: return
    w._pending_preset = a if a.logo else None; w.generate_arm_part()


def preset_kinetic(w, a):
    """Open the Kinetic Hand with the wrist/palm measures, pick a part from the library and place the motif on a free spot."""
    w.select("kinetic_hand"); w.side.setCurrentIndex(max(0, w.side.findData(a.side)))
    w.fields["wrist_mm"].setValue(a.wrist if a.wrist != 40.0 else 48.0); w.fields["palm_mm"].setValue(a.palm); w.recompute(); w.go(2)
    c = w.custom; pick = next((i for i in range(1, c.lib.count()) if c.lib.itemText(i).startswith(a.kin_part)), None)
    if pick is None: raise SystemExit(f"Pièce introuvable dans la bibliothèque : {a.kin_part}")
    c.pick_library(pick)
    if a.logo:
        _apply_deco_preset(c, a, centre=False) if (a.u or a.v) else (_apply_deco_preset(c, a, centre=True), c.find_free_spot())


def preset(w, a):
    """Preload the Phoenix customisation page from command-line options (all optional)."""
    w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(a.wrist); c = w.custom
    pick = next((i for i in range(1, c.lib.count()) if c.lib.itemText(i).startswith(a.part)), None)
    if pick is None: raise SystemExit(f"Pièce introuvable dans la bibliothèque : {a.part}")
    c.pick_library(pick)
    if a.logo:
        kind = "svg" if a.logo.lower().endswith(".svg") else "image"
        c.kind.setCurrentIndex(c.kind.findData(kind)); c.svg_path = str(Path(a.logo).resolve())
    c.size.setValue(a.size); c.depth.setValue(a.depth); c.ncol.setValue(a.colors)
    c.mode.setCurrentIndex(c.mode.findData(a.mode)); c.qual.setCurrentIndex(c.qual.findData(a.res))
    c.place(a.u, a.v); w.go(2)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="customlab.gui")
    ap.add_argument("--device", default="phoenix_hand", choices=["phoenix_hand", "unlimbited_arm", "kinetic_hand", "kinetic_arm"])
    ap.add_argument("--palm", type=float, default=40.0, help="Kinetic Hand: affected palm length (mm)"); ap.add_argument("--kin-part", default="Gauntlet cover")
    ap.add_argument("--a", type=float, default=220.0, help="arm: A = BicepCircum (mm)"); ap.add_argument("--b", type=float, default=200.0, help="arm: B = ForearmLen (mm)"); ap.add_argument("--c", type=float, default=150.0, help="arm: C = HandLen (mm)")
    ap.add_argument("--arm-part", default="Cuff"); ap.add_argument("--side", default="left", choices=["left", "right"])
    ap.add_argument("--logo", help="SVG or PNG/JPEG file to preload on the customisation page")
    ap.add_argument("--part", default="Palm · left"); ap.add_argument("--wrist", type=float, default=40.0)
    ap.add_argument("--size", type=float, default=30.0); ap.add_argument("--depth", type=float, default=1.0)
    ap.add_argument("--u", type=float, default=0.0); ap.add_argument("--v", type=float, default=0.0)
    ap.add_argument("--colors", type=int, default=1); ap.add_argument("--mode", default="inlay", choices=["relief", "engrave", "inlay"])
    ap.add_argument("--res", type=float, default=0.15, choices=[0.25, 0.15, 0.10])
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    set_default_format(); app = QApplication(sys.argv[:1]); theme.apply(app); app.setWindowIcon(QIcon(str(theme.LOGO))); w = MainWindow(); w.show()
    if os.environ.get("CUSTOMLAB_SYNC") != "1" and not os.environ.get("CUSTOMLAB_NO_FIRST_RUN"): w.first_run_check()
    if a.device == "unlimbited_arm": preset_arm(w, a)
    elif a.device == "kinetic_hand": preset_kinetic(w, a)
    elif a.logo: preset(w, a)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
