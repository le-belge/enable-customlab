"""Dialog: apply the current camouflage to several parts of the device and export each one (worker thread, cancellable)."""
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
                               QTextEdit, QVBoxLayout)

from . import camo_batch

TX = {"fr": {"title": "Camouflage sur plusieurs pièces", "intro": "Cochez les pièces à décorer avec le camouflage choisi (style, taille des taches, profondeur et qualité de la page). Chaque pièce reçoit sa propre variante, sa vue et ses zones interdites déjà tracées ; un dossier par pièce est exporté.",
             "all": "Tout cocher", "none": "Aucune", "vary": "Une variante différente par pièce", "go": "Exporter…", "cancel": "Annuler", "close": "Fermer", "running": "En cours : {p} ({i}/{n})", "done": "Terminé : {ok} exportée(s), {sk} ignorée(s), {fl} en échec.\nDossier : {d}",
             "pick": "Choisir le dossier d'export", "none_sel": "Cochez au moins une pièce.", "stopped": "Arrêté."},
      "en": {"title": "Camouflage on several parts", "intro": "Tick the parts to decorate with the chosen camouflage (style, patch size, depth and quality from the page). Each part gets its own variant, view and the forbidden zones already drawn; one folder per part is exported.",
             "all": "Tick all", "none": "None", "vary": "A different variant for each part", "go": "Export…", "cancel": "Cancel", "close": "Close", "running": "Working: {p} ({i}/{n})", "done": "Done: {ok} exported, {sk} skipped, {fl} failed.\nFolder: {d}",
             "pick": "Choose the export folder", "none_sel": "Tick at least one part.", "stopped": "Stopped."}}


class _Sig(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)


class _Job(QRunnable):
    def __init__(self, fn): super().__init__(); self.fn = fn

    def run(self): self.fn()


class BatchDialog(QDialog):
    def __init__(self, parent, lang, items, base_spec, ctx, current=None):
        super().__init__(parent); self.t = TX[lang].get; self.setWindowTitle(self.t("title")); self.resize(640, 640)
        self.base_spec, self.ctx, self.cancel_flag, self.out = base_spec, ctx, threading.Event(), None
        v = QVBoxLayout(self); intro = QLabel(self.t("intro")); intro.setWordWrap(True); v.addWidget(intro)
        self.list = QListWidget()
        for it in items:
            li = QListWidgetItem(it["label"].split(" — ")[0]); li.setFlags(li.flags() | Qt.ItemIsUserCheckable); li.setCheckState(Qt.Checked if current and Path(str(it["path"])).resolve() == Path(str(current)).resolve() else Qt.Unchecked); li.setData(Qt.UserRole, it["path"]); self.list.addItem(li)
        v.addWidget(self.list, 1)
        row = QHBoxLayout(); self.b_all = QPushButton(self.t("all")); self.b_none = QPushButton(self.t("none")); self.vary = QCheckBox(self.t("vary")); self.vary.setChecked(True)
        self.b_all.clicked.connect(lambda: self._set_all(Qt.Checked)); self.b_none.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        for x in (self.b_all, self.b_none, self.vary): row.addWidget(x)
        row.addStretch(1); v.addLayout(row)
        self.bar = QProgressBar(); self.bar.setVisible(False); self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(140); v.addWidget(self.bar); v.addWidget(self.log)
        row2 = QHBoxLayout(); self.b_go = QPushButton(self.t("go")); self.b_go.setObjectName("primary"); self.b_cancel = QPushButton(self.t("cancel")); self.b_close = QPushButton(self.t("close"))
        self.b_go.clicked.connect(self.start); self.b_cancel.clicked.connect(self.cancel_flag.set); self.b_close.clicked.connect(self.close); self.b_cancel.setEnabled(False)
        row2.addStretch(1)
        for x in (self.b_go, self.b_cancel, self.b_close): row2.addWidget(x)
        v.addLayout(row2); self.sig = _Sig(); self.sig.progress.connect(self._progress); self.sig.finished.connect(self._finished)

    def _set_all(self, st):
        for i in range(self.list.count()): self.list.item(i).setCheckState(st)

    def selected(self):
        return [(self.list.item(i).text(), self.list.item(i).data(Qt.UserRole)) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]

    def start(self):
        parts = self.selected()
        if not parts: QMessageBox.information(self, self.t("title"), self.t("none_sel")); return
        d = QFileDialog.getExistingDirectory(self, self.t("pick"))
        if not d: return
        self.out = Path(d) / f"camouflage_{self.base_spec.camo_style}"; self.cancel_flag.clear(); self.bar.setRange(0, len(parts)); self.bar.setValue(0); self.bar.setVisible(True)
        self.b_go.setEnabled(False); self.b_cancel.setEnabled(True); self.log.clear(); vary = self.vary.isChecked()
        QThreadPool.globalInstance().start(_Job(lambda: self.sig.finished.emit(camo_batch.run(parts, self.base_spec, self.out, self.ctx, lambda i, n, m: self.sig.progress.emit(i, n, m), self.cancel_flag.is_set, vary))))

    def _progress(self, i, n, msg):
        self.bar.setValue(i); self.bar.setFormat(self.t("running").format(p=msg, i=min(i + 1, n), n=n) if msg else "")

    def _finished(self, results):
        self.b_go.setEnabled(True); self.b_cancel.setEnabled(False); self.bar.setVisible(False)
        n = {k: sum(1 for r in results if r["status"] == k) for k in ("ok", "skipped", "failed")}
        txt = self.t("done").format(ok=n["ok"], sk=n["skipped"], fl=n["failed"], d=self.out) + ("\n" + self.t("stopped") if self.cancel_flag.is_set() else "")
        self.log.setPlainText(txt + "\n\n" + "\n".join(f"[{r['status']}] {r['part']} — {r['message']}" for r in results if r["status"] != "ok"))
        self.results = results
