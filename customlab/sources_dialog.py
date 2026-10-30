"""Window "Fichiers sources": where the user's own SCAD/STL downloads go, what is found, OpenSCAD status.

CustomLab bundles none of these files (only the Phoenix parts under customlab/bundled_parts). The user downloads them from the official
pages, drops them in the sources folder and presses "Vérifier". Nothing is downloaded by the app.
"""
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout)

from . import openscad, paths
from .profiles import load_profile

# device -> (sub-folder of the sources folder, official page, what is needed)
DEVICES = {
    "kinetic_hand": ("kinetic_hand", "https://www.thingiverse.com/thing:4618922", "stl"),
    "kinetic_arm": ("kinetic_arm", "https://www.thingiverse.com/thing:6736769", "stl"),
    "unlimbited_arm": ("unlimbited_arm", "https://www.thingiverse.com/thing:1672381", "scad"),
    "phoenix_hand": ("phoenix_scad", "https://www.thingiverse.com/thing:1674320", "optional"),
}
TX = {"fr": {"title": "Fichiers sources", "intro": "CustomLab n'embarque pas les fichiers des appareils (licences, taille) : seules les pièces Phoenix sont incluses. Téléchargez les fichiers depuis les pages officielles (bouton « Ouvrir la page »), décompressez-les dans le dossier ci-dessous en gardant le nom du sous-dossier indiqué, puis cliquez sur « Vérifier ».",
             "folder": "Dossier des sources :", "choose": "Changer de dossier…", "reveal": "Ouvrir le dossier", "check": "Vérifier", "close": "Fermer", "page": "Ouvrir la page officielle",
             "ok_stl": "✓ {n} fichier(s) STL trouvé(s)", "ko_stl": "✗ aucun STL trouvé", "ok_scad": "✓ SCAD officiel trouvé", "ko_scad": "✗ SCAD officiel introuvable : {p}", "opt": "Facultatif : les pièces Phoenix incluses suffisent ({n} fichier(s) trouvé(s))",
             "sub": "sous-dossier « {d} »", "scad_ok": "✓ OpenSCAD trouvé : {p}", "scad_ko": "✗ OpenSCAD introuvable : à installer depuis openscad.org (gravure et Unlimbited Arm) ; relancez ensuite CustomLab.",
             "names": {"kinetic_hand": "Kinetic Hand", "kinetic_arm": "Kinetic Arm", "unlimbited_arm": "Unlimbited Arm", "phoenix_hand": "Phoenix (SCAD, facultatif)"}},
      "en": {"title": "Source files", "intro": "CustomLab does not bundle the device files (licences, size): only the Phoenix parts are included. Download the files from the official pages (\"Open the page\" button), unzip them into the folder below keeping the sub-folder name shown, then click \"Check\".",
             "folder": "Sources folder:", "choose": "Change folder…", "reveal": "Open the folder", "check": "Check", "close": "Close", "page": "Open the official page",
             "ok_stl": "✓ {n} STL file(s) found", "ko_stl": "✗ no STL found", "ok_scad": "✓ Official SCAD found", "ko_scad": "✗ Official SCAD not found: {p}", "opt": "Optional: the bundled Phoenix parts are enough ({n} file(s) found)",
             "sub": "sub-folder \"{d}\"", "scad_ok": "✓ OpenSCAD found: {p}", "scad_ko": "✗ OpenSCAD not found: install it from openscad.org (engraving and Unlimbited Arm), then restart CustomLab.",
             "names": {"kinetic_hand": "Kinetic Hand", "kinetic_arm": "Kinetic Arm", "unlimbited_arm": "Unlimbited Arm", "phoenix_hand": "Phoenix (SCAD, optional)"}}}


def status(pid):
    """(found: bool|None, count, detail path) for one device; None = optional."""
    sub, _, need = DEVICES[pid]; base = paths.sources_dir() / sub
    if need == "scad":
        p = paths.resolve(load_profile(pid).get("official_scad") or ""); return p.is_file(), 0, p
    n = sum(1 for f in base.rglob("*") if f.suffix.lower() == ".stl") if base.is_dir() else 0
    return (n > 0 if need == "stl" else None), n, base


class SourcesDialog(QDialog):
    def __init__(self, parent, lang):
        super().__init__(parent); self.lang = lang; self.t = TX[lang]; self.setWindowTitle(self.t["title"]); self.resize(760, 520); self.changed = False
        v = QVBoxLayout(self); intro = QLabel(self.t["intro"]); intro.setWordWrap(True); v.addWidget(intro)
        row = QHBoxLayout(); row.addWidget(QLabel(self.t["folder"])); self.path = QLabel(); self.path.setTextInteractionFlags(Qt.TextSelectableByMouse); row.addWidget(self.path, 1)
        b1 = QPushButton(self.t["choose"]); b1.clicked.connect(self.choose); b2 = QPushButton(self.t["reveal"]); b2.clicked.connect(self.reveal); row.addWidget(b1); row.addWidget(b2); v.addLayout(row)
        self.grid = QGridLayout(); v.addLayout(self.grid); self.scad = QLabel(); self.scad.setWordWrap(True); v.addWidget(self.scad); v.addStretch(1)
        row2 = QHBoxLayout(); row2.addStretch(1); bc = QPushButton(self.t["check"]); bc.setObjectName("primary"); bc.clicked.connect(self.refresh); bx = QPushButton(self.t["close"]); bx.clicked.connect(self.accept)
        row2.addWidget(bc); row2.addWidget(bx); v.addLayout(row2); self.refresh()

    def refresh(self):
        self.path.setText(str(paths.sources_dir()))
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()
        for i, pid in enumerate(DEVICES):
            found, n, p = status(pid); sub, url, need = DEVICES[pid]
            if need == "optional": txt = self.t["opt"].format(n=n)
            elif need == "scad": txt = self.t["ok_scad"] if found else self.t["ko_scad"].format(p=p)
            else: txt = self.t["ok_stl"].format(n=n) if found else self.t["ko_stl"]
            name = QLabel(f"<b>{self.t['names'][pid]}</b><br><span style='font-size:11px'>{self.t['sub'].format(d=sub)}</span>"); st = QLabel(txt); st.setWordWrap(True)
            st.setStyleSheet("color:%s" % ("#1b7f3b" if found else "#8a4b00" if found is False else "#5b6b78"))
            b = QPushButton(self.t["page"]); b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            self.grid.addWidget(name, i, 0); self.grid.addWidget(st, i, 1); self.grid.addWidget(b, i, 2)
        o = openscad.find_openscad(); self.scad.setText(self.t["scad_ok"].format(p=o) if o else self.t["scad_ko"])
        self.changed = True

    def choose(self):
        d = QFileDialog.getExistingDirectory(self, self.t["folder"], str(paths.sources_dir()))
        if d: paths.save_setting("sources_dir", d); self.refresh()

    def reveal(self):
        d = paths.sources_dir(); d.mkdir(parents=True, exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))
