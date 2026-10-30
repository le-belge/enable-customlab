"""Dialog: export every part of the device at the export scale (worker thread, cancellable)."""
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout)

from . import export_all

TX = {"fr": {"title": "Exporter toutes les pièces", "intro": "Chaque pièce cochée est exportée dans son propre dossier, avec l'échelle d'export de l'appareil{sc}. La pièce personnalisée garde sa décoration ; les autres sortent non décorées (miroir appliqué pour une main gauche Kinetic).",
             "all": "Tout cocher", "none": "Aucune", "go": "Exporter…", "cancel": "Annuler", "close": "Fermer", "running": "En cours : {p} ({i}/{n})",
             "done": "Terminé : {ok} exportée(s), {sk} ignorée(s), {fl} en échec.\nDossier : {d}", "pick": "Choisir le dossier d'export", "none_sel": "Cochez au moins une pièce.", "stopped": "Arrêté.",
             "sc_on": " ({p:g} %)", "sc_off": " (échelle d'export non cochée : 100 %)", "deco": " — décorée"},
      "en": {"title": "Export all parts", "intro": "Each ticked part is exported in its own folder at the device's export scale{sc}. The customised part keeps its decoration; the others are exported undecorated (mirrored for a left Kinetic hand).",
             "all": "Tick all", "none": "None", "go": "Export…", "cancel": "Cancel", "close": "Close", "running": "Working: {p} ({i}/{n})",
             "done": "Done: {ok} exported, {sk} skipped, {fl} failed.\nFolder: {d}", "pick": "Choose the export folder", "none_sel": "Tick at least one part.", "stopped": "Stopped.",
             "sc_on": " ({p:g} %)", "sc_off": " (export scale unticked: 100 %)", "deco": " — decorated"}}


class _Sig(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)


class _Job(QRunnable):
    def __init__(self, fn): super().__init__(); self.fn = fn

    def run(self): self.fn()


class ExportAllDialog(QDialog):
    def __init__(self, parent, lang, items, decorated, ctx, scale_text, current=None):
        super().__init__(parent); self.t = TX[lang].get; self.setWindowTitle(self.t("title")); self.resize(620, 620)
        self.decorated, self.ctx, self.cancel_flag, self.out = decorated, ctx, threading.Event(), None
        v = QVBoxLayout(self); intro = QLabel(self.t("intro").format(sc=scale_text)); intro.setWordWrap(True); v.addWidget(intro)
        self.list = QListWidget(); dec = Path(str(decorated[0])).resolve() if decorated else None
        for it in items:
            is_dec = dec is not None and Path(str(it["path"])).resolve() == dec
            li = QListWidgetItem(it["label"].split(" — ")[0] + (self.t("deco") if is_dec else "")); li.setFlags(li.flags() | Qt.ItemIsUserCheckable); li.setCheckState(Qt.Checked)
            li.setData(Qt.UserRole, it["path"]); self.list.addItem(li)
        v.addWidget(self.list, 1)
        row = QHBoxLayout(); self.b_all = QPushButton(self.t("all")); self.b_none = QPushButton(self.t("none"))
        self.b_all.clicked.connect(lambda: self._set_all(Qt.Checked)); self.b_none.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        row.addWidget(self.b_all); row.addWidget(self.b_none); row.addStretch(1); v.addLayout(row)
        self.bar = QProgressBar(); self.bar.setVisible(False); self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(140); v.addWidget(self.bar); v.addWidget(self.log)
        row2 = QHBoxLayout(); self.b_go = QPushButton(self.t("go")); self.b_go.setObjectName("primary"); self.b_cancel = QPushButton(self.t("cancel")); self.b_close = QPushButton(self.t("close"))
        self.b_go.clicked.connect(self.start); self.b_cancel.clicked.connect(self.cancel_flag.set); self.b_close.clicked.connect(self.close); self.b_cancel.setEnabled(False)
        row2.addStretch(1)
        for x in (self.b_go, self.b_cancel, self.b_close): row2.addWidget(x)
        v.addLayout(row2); self.sig = _Sig(); self.sig.progress.connect(self._progress); self.sig.finished.connect(self._finished)

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
        self.results = results
