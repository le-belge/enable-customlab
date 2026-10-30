"""Dialog: export every part of the device at the export scale (worker thread, cancellable)."""
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout)

from . import export_all

TX = {"fr": {"title": "Exporter toutes les pièces", "intro": "Chaque pièce cochée est exportée dans son propre dossier, avec l'échelle d'export de l'appareil{sc}. La pièce personnalisée garde sa décoration ; les autres sortent non décorées (miroir appliqué pour une main gauche Kinetic).",
             "all": "Tout cocher", "none": "Aucune", "go": "Exporter…", "cancel": "Annuler", "close": "Fermer", "running": "En cours : {p} ({i}/{n})",
             "done": "Terminé : {ok} exportée(s), {sk} ignorée(s), {fl} en échec.\nDossier : {d}", "pick": "Choisir le dossier d'export", "none_sel": "Cochez au moins une pièce.", "stopped": "Arrêté.",
             "sc_on": " ({p:g} %)", "sc_off": " (échelle d'export non cochée : 100 %)", "deco": " — décorée", "quick_title": "Exporter tout, prêt pour Bambu", "quick_intro": "Toutes les pièces sont exportées à l'échelle calculée{sc}, chacune dans son dossier. La pièce personnalisée garde son motif et un fichier .3mf prêt pour Bambu Studio est créé.", "reveal": "Ouvrir le dossier", "bambu": "Ouvrir dans Bambu Studio (couleurs prêtes)"},
      "en": {"title": "Export all parts", "intro": "Each ticked part is exported in its own folder at the device's export scale{sc}. The customised part keeps its decoration; the others are exported undecorated (mirrored for a left Kinetic hand).",
             "all": "Tick all", "none": "None", "go": "Export…", "cancel": "Cancel", "close": "Close", "running": "Working: {p} ({i}/{n})",
             "done": "Done: {ok} exported, {sk} skipped, {fl} failed.\nFolder: {d}", "pick": "Choose the export folder", "none_sel": "Tick at least one part.", "stopped": "Stopped.",
             "sc_on": " ({p:g} %)", "sc_off": " (export scale unticked: 100 %)", "deco": " — decorated", "quick_title": "Export everything, ready for Bambu", "quick_intro": "All parts are exported at the computed scale{sc}, each in its own folder. The customised part keeps its motif and a .3mf file ready for Bambu Studio is created.", "reveal": "Open the folder", "bambu": "Open in Bambu Studio (colours ready)"}}


class _Sig(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)


class _Job(QRunnable):
    def __init__(self, fn): super().__init__(); self.fn = fn

    def run(self): self.fn()


class ExportAllDialog(QDialog):
    def __init__(self, parent, lang, items, decorated, ctx, scale_text, current=None, quick=False):
        super().__init__(parent); self.t = TX[lang].get; self.quick = quick; self.setWindowTitle(self.t("quick_title" if quick else "title")); self.resize(620, 620)
        self.decorated, self.ctx, self.cancel_flag, self.out = decorated, ctx, threading.Event(), None
        v = QVBoxLayout(self); intro = QLabel(self.t("quick_intro" if quick else "intro").format(sc=scale_text)); intro.setWordWrap(True); v.addWidget(intro)
        self.list = QListWidget(); dec = Path(str(decorated[0])).resolve() if decorated else None
        for it in items:
            is_dec = dec is not None and Path(str(it["path"])).resolve() == dec
            li = QListWidgetItem(it["label"].split(" — ")[0] + (self.t("deco") if is_dec else "")); li.setFlags(li.flags() | Qt.ItemIsUserCheckable); li.setCheckState(Qt.Checked)
            li.setData(Qt.UserRole, it["path"]); self.list.addItem(li)
        v.addWidget(self.list, 1); self.list.setVisible(not quick)
        row = QHBoxLayout(); self.b_all = QPushButton(self.t("all")); self.b_none = QPushButton(self.t("none"))
        self.b_all.clicked.connect(lambda: self._set_all(Qt.Checked)); self.b_none.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        row.addWidget(self.b_all); row.addWidget(self.b_none); row.addStretch(1); v.addLayout(row); self.b_all.setVisible(not quick); self.b_none.setVisible(not quick)
        self.bar = QProgressBar(); self.bar.setVisible(False); self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(140); v.addWidget(self.bar); v.addWidget(self.log)
        row2 = QHBoxLayout(); self.b_go = QPushButton(self.t("go")); self.b_go.setObjectName("primary"); self.b_cancel = QPushButton(self.t("cancel")); self.b_close = QPushButton(self.t("close"))
        self.b_go.clicked.connect(self.start); self.b_cancel.clicked.connect(self.cancel_flag.set); self.b_close.clicked.connect(self.close); self.b_cancel.setEnabled(False)
        row2.addStretch(1)
        for x in (self.b_go, self.b_cancel, self.b_close): row2.addWidget(x)
        self.b_reveal = QPushButton(self.t("reveal")); self.b_reveal.setVisible(False); self.b_reveal.clicked.connect(self._reveal); row2.insertWidget(1, self.b_reveal)
        self.b_bambu = QPushButton(self.t("bambu")); self.b_bambu.setObjectName("primary"); self.b_bambu.setVisible(False); self.b_bambu.clicked.connect(self._open_bambu); row2.insertWidget(1, self.b_bambu); self.bambu_file = None
        v.addLayout(row2); self.sig = _Sig(); self.sig.progress.connect(self._progress); self.sig.finished.connect(self._finished)
        if quick: QTimer.singleShot(0, self._quick_start)

    def _quick_start(self):
        self.start()
        if self.out is None: self.close()                         # folder choice cancelled

    def _open_bambu(self):
        """The customised part's multi-colour .3mf (filaments already assigned), opened with the default 3MF application (Bambu Studio)."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        if self.bambu_file: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.bambu_file)))

    def _reveal(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        if self.out: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.out)))

    def _set_all(self, st):
        for i in range(self.list.count()): self.list.item(i).setCheckState(st)

    def selected(self):
        return [(self.list.item(i).text().replace(self.t("deco"), ""), self.list.item(i).data(Qt.UserRole)) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]

    def start(self):
        parts = self.selected()
        if not parts: QMessageBox.information(self, self.t("title"), self.t("none_sel")); return
        d = QFileDialog.getExistingDirectory(self, self.t("pick"))
        if not d: return
        self.out = Path(d) / "export_toutes_les_pieces"; self.cancel_flag.clear(); self.bar.setRange(0, len(parts)); self.bar.setValue(0); self.bar.setVisible(True)
        self.b_go.setEnabled(False); self.b_cancel.setEnabled(True); self.log.clear()
        QThreadPool.globalInstance().start(_Job(lambda: self.sig.finished.emit(export_all.run(parts, self.decorated, self.out, self.ctx, lambda i, n, m: self.sig.progress.emit(i, n, m), self.cancel_flag.is_set))))

    def _progress(self, i, n, msg):
        self.bar.setValue(i); self.bar.setFormat(self.t("running").format(p=msg, i=min(i + 1, n), n=n) if msg else "")

    def _finished(self, results):
        self.b_go.setEnabled(True); self.b_cancel.setEnabled(False); self.bar.setVisible(False)
        n = {k: sum(1 for r in results if r["status"] == k) for k in ("ok", "skipped", "failed")}
        txt = self.t("done").format(ok=n["ok"], sk=n["skipped"], fl=n["failed"], d=self.out) + ("\n" + self.t("stopped") if self.cancel_flag.is_set() else "")
        self.log.setPlainText(txt + "\n\n" + "\n".join(f"[{r['status']}] {r['part']} — {r['message']}" for r in results if r["status"] != "ok"))
        self.results = results; self.b_reveal.setVisible(n["ok"] > 0)
        self.bambu_file = next(iter(sorted(Path(self.out).rglob("*_Bambu_pret.3mf"))), None) if self.out else None; self.b_bambu.setVisible(self.bambu_file is not None)
