"""Help window: the scaling / customising tutorial (docs/TUTO_ECHELLES.md, French) shown as formatted text."""
from pathlib import Path

from . import paths
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout

TUTO = paths.resource_dir() / "docs" / "TUTO_ECHELLES.md"
TX = {"fr": {"title": "Tuto : mesures, échelles et personnalisation", "close": "Fermer", "missing": "Fichier du tuto introuvable : {p}"},
      "en": {"title": "Tutorial: measuring, scaling and customising (in French)", "close": "Close", "missing": "Tutorial file not found: {p}"}}


class TutoDialog(QDialog):
    def __init__(self, parent, lang):
        super().__init__(parent); t = TX[lang]; self.setWindowTitle(t["title"]); self.resize(760, 680)
        v = QVBoxLayout(self); self.view = QTextBrowser(); self.view.setOpenExternalLinks(False); v.addWidget(self.view, 1)
        try: self.view.setMarkdown(TUTO.read_text(encoding="utf-8"))
        except OSError: self.view.setPlainText(t["missing"].format(p=TUTO))
        row = QHBoxLayout(); row.addStretch(1); b = QPushButton(t["close"]); b.clicked.connect(self.close); row.addWidget(b); v.addLayout(row)
