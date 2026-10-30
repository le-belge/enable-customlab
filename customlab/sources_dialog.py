"""Window "Fichiers sources": where the user's own SCAD/STL downloads go, what is found, OpenSCAD status.

CustomLab bundles none of these files (only the Phoenix parts under customlab/bundled_parts). The user downloads them from the official
pages, drops them in the sources folder and presses "Vérifier". Nothing is downloaded by the app.
"""
import shutil
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QFileDialog, QGridLayout, QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout)

from . import armgen, openscad, paths
from .profiles import load_profile

# device -> (sub-folder of the sources folder, official page, what is needed)
DEVICES = {
    "kinetic_hand": ("kinetic_hand", "https://www.thingiverse.com/thing:4618922", "stl"),
    "kinetic_arm": ("kinetic_arm", "https://www.thingiverse.com/thing:6736769", "stl"),
    "unlimbited_arm": ("unlimbited_arm", "https://www.thingiverse.com/thing:1672381", "scad"),
}
TX = {"fr": {"title": "Fichiers sources", "intro": "<b>Pour utiliser un autre appareil que la Phoenix :</b><br>1. Cliquez sur « Ouvrir la page officielle » et téléchargez les fichiers (bouton de téléchargement du site).<br>2. Cliquez sur « Ajouter le .zip téléchargé… » et choisissez le fichier : CustomLab le range au bon endroit tout seul.<br>3. C'est prêt (✓ vert). Rien d'autre à faire.",
             "folder": "Dossier de rangement :", "choose": "Changer de dossier…", "reveal": "Ouvrir le dossier", "check": "Vérifier", "close": "Fermer", "page": "Ouvrir la page officielle",
             "add_zip": "Ajouter le .zip téléchargé…", "add_dir": "Ajouter un dossier…", "pick_zip": "Choisir le .zip téléchargé", "pick_dir": "Choisir le dossier téléchargé", "busy": "⏳ Copie en cours… ({i}/{n})", "added": "✓ {n} fichier(s) ajouté(s).", "err": "✗ Impossible d'ajouter : {e}",
             "ok_stl": "✓ prêt ({n} fichiers STL)", "ko_stl": "✗ pas encore de fichiers", "ok_scad": "✓ prêt (SCAD officiel trouvé)", "ko_scad": "✗ pas encore de fichiers", "opt": "Facultatif : les pièces Phoenix incluses suffisent",
             "sub": "", "scad_ok": "✓ OpenSCAD trouvé", "scad_ko": "✗ OpenSCAD (gratuit, openscad.org) n'est pas installé : il n'est nécessaire que pour la gravure et l'Unlimbited Arm. Installez-le puis relancez CustomLab.",
             "names": {"kinetic_hand": "Kinetic Hand", "kinetic_arm": "Kinetic Arm", "unlimbited_arm": "Unlimbited Arm", "phoenix_hand": "Phoenix (SCAD, facultatif)"}},
      "en": {"title": "Source files", "intro": "<b>To use a device other than the Phoenix:</b><br>1. Click \"Open the official page\" and download the files (the site's download button).<br>2. Click \"Add the downloaded .zip…\" and choose the file: CustomLab puts it in the right place by itself.<br>3. It is ready (green ✓). Nothing else to do.",
             "folder": "Storage folder:", "choose": "Change folder…", "reveal": "Open the folder", "check": "Check", "close": "Close", "page": "Open the official page",
             "add_zip": "Add the downloaded .zip…", "add_dir": "Add a folder…", "pick_zip": "Choose the downloaded .zip", "pick_dir": "Choose the downloaded folder", "busy": "⏳ Copying… ({i}/{n})", "added": "✓ {n} file(s) added.", "err": "✗ Could not add: {e}",
             "ok_stl": "✓ ready ({n} STL files)", "ko_stl": "✗ no files yet", "ok_scad": "✓ ready (official SCAD found)", "ko_scad": "✗ no files yet", "opt": "Optional: the bundled Phoenix parts are enough",
             "sub": "", "scad_ok": "✓ OpenSCAD found", "scad_ko": "✗ OpenSCAD (free, openscad.org) is not installed: only needed for engraving and the Unlimbited Arm. Install it, then restart CustomLab.",
             "names": {"kinetic_hand": "Kinetic Hand", "kinetic_arm": "Kinetic Arm", "unlimbited_arm": "Unlimbited Arm", "phoenix_hand": "Phoenix (SCAD, optional)"}}}


def status(pid):
    """(found: bool|None, count, detail path) for one device; None = optional."""
    sub, _, need = DEVICES[pid]; base = paths.sources_dir() / sub
    if need == "scad":
        prof = load_profile(pid); p = armgen.scad_path(prof); return p is not None, 0, p or paths.resolve(prof.get("official_scad") or "")
    n = sum(1 for f in base.rglob("*") if f.suffix.lower() == ".stl") if base.is_dir() else 0
    return (n > 0 if need == "stl" else None), n, base


def add_zip(pid, zip_path, progress=lambda i, n: None):
    """Unzip a downloaded archive into <sources>/<device sub-folder>/ (entries leaving that folder are refused). Returns the number of files written."""
    dest = (paths.sources_dir() / DEVICES[pid][0]).resolve(); dest.mkdir(parents=True, exist_ok=True); n = 0
    with zipfile.ZipFile(zip_path) as z:
        members = [m for m in z.infolist() if not m.is_dir() and not m.filename.startswith("__MACOSX/") and not Path(m.filename).name.startswith("._")]
        for i, m in enumerate(members):
            target = (dest / m.filename).resolve()
            if dest != target and dest not in target.parents: raise ValueError(f"Entrée refusée (hors du dossier) : {m.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as src, open(target, "wb") as out: shutil.copyfileobj(src, out)
            n += 1; progress(i + 1, len(members))
    return n


def add_folder(pid, folder, progress=lambda i, n: None):
    """Copy a downloaded, already unzipped folder into <sources>/<device sub-folder>/. Returns the number of files copied."""
    src = Path(folder).resolve(); dest = (paths.sources_dir() / DEVICES[pid][0]).resolve(); files = [p for p in src.rglob("*") if p.is_file() and not p.name.startswith("._") and p.name != ".DS_Store"]
    if dest == src or dest in src.parents or src in dest.parents: raise ValueError("Ce dossier est déjà dans le dossier des sources.")
    for i, p in enumerate(files):
        t = dest / p.relative_to(src); t.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, t); progress(i + 1, len(files))
    return len(files)


class _Sig(QObject):
    done = Signal(object)
    step = Signal(int, int)


class _Job(QRunnable):
    def __init__(self, fn): super().__init__(); self.fn = fn

    def run(self): self.fn()


class SourcesDialog(QDialog):
    def __init__(self, parent, lang):
        super().__init__(parent); self.lang = lang; self.t = TX[lang]; self.setWindowTitle(self.t["title"]); self.resize(820, 600); self.changed = False
        v = QVBoxLayout(self); intro = QLabel(self.t["intro"]); intro.setWordWrap(True); v.addWidget(intro); self.sig = _Sig(); self.sig.done.connect(self._added); self.sig.step.connect(self._step); self.note = QLabel()
        row = QHBoxLayout(); row.addWidget(QLabel(self.t["folder"])); self.path = QLabel(); self.path.setTextInteractionFlags(Qt.TextSelectableByMouse); row.addWidget(self.path, 1)
        b1 = QPushButton(self.t["choose"]); b1.clicked.connect(self.choose); b2 = QPushButton(self.t["reveal"]); b2.clicked.connect(self.reveal); row.addWidget(b1); row.addWidget(b2); v.addLayout(row)
        self.grid = QGridLayout(); v.addLayout(self.grid); self.scad = QLabel(); self.scad.setWordWrap(True); v.addWidget(self.note); v.addWidget(self.scad); v.addStretch(1)
        row2 = QHBoxLayout(); row2.addStretch(1); bc = QPushButton(self.t["check"]); bc.setObjectName("primary"); bc.clicked.connect(self.refresh); bx = QPushButton(self.t["close"]); bx.clicked.connect(self.accept)
        row2.addWidget(bc); row2.addWidget(bx); v.addLayout(row2); self.refresh()

    def refresh(self):
        self.path.setText(str(paths.sources_dir()))
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()
        for i, pid in enumerate(DEVICES):
            found, n, p = status(pid); sub, url, need = DEVICES[pid]
            if need == "optional": txt = self.t["opt"]
            elif need == "scad": txt = self.t["ok_scad"] if found else self.t["ko_scad"]
            else: txt = self.t["ok_stl"].format(n=n) if found else self.t["ko_stl"]
            name = QLabel(f"<b>{self.t['names'][pid]}</b>"); st = QLabel(txt); st.setWordWrap(True)
            st.setStyleSheet("color:%s" % ("#1b7f3b" if found else "#8a4b00" if found is False else "#5b6b78"))
            box = QWidget(); bl = QVBoxLayout(box); bl.setContentsMargins(0, 0, 0, 0); bl.setSpacing(4)
            b = QPushButton(self.t["page"]); b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            bz = QPushButton(self.t["add_zip"]); bz.setObjectName("primary"); bz.clicked.connect(lambda _=False, d=pid: self.pick(d, True))
            bd = QPushButton(self.t["add_dir"]); bd.clicked.connect(lambda _=False, d=pid: self.pick(d, False))
            for x in (b, bz, bd): bl.addWidget(x)
            self.grid.addWidget(name, i, 0); self.grid.addWidget(st, i, 1); self.grid.addWidget(box, i, 2)
        o = openscad.find_openscad(); self.scad.setText(self.t["scad_ok"] if o else self.t["scad_ko"])
        self.changed = True

    def pick(self, pid, zip_):
        """Ask for the downloaded archive/folder and copy it into place in a worker thread."""
        if zip_: f, _ = QFileDialog.getOpenFileName(self, self.t["pick_zip"], str(Path.home() / "Downloads"), "ZIP (*.zip)")
        else: f = QFileDialog.getExistingDirectory(self, self.t["pick_dir"], str(Path.home() / "Downloads"))
        if not f: return
        self.setEnabled(False); fn = add_zip if zip_ else add_folder

        def work():
            try: self.sig.done.emit(("ok", fn(pid, f, lambda i, n: self.sig.step.emit(i, n))))
            except Exception as e: self.sig.done.emit(("err", str(e)))
        QThreadPool.globalInstance().start(_Job(work))

    def _step(self, i, n): self.note.setText(self.t["busy"].format(i=i, n=n))

    def _added(self, res):
        self.setEnabled(True); self.refresh()
        self.note.setText(self.t["added"].format(n=res[1]) if res[0] == "ok" else self.t["err"].format(e=res[1]))

    def choose(self):
        d = QFileDialog.getExistingDirectory(self, self.t["folder"], str(paths.sources_dir()))
        if d: paths.save_setting("sources_dir", d); self.refresh()

    def reveal(self):
        d = paths.sources_dir(); d.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))
