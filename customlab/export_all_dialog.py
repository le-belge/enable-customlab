"""Dialog: export every part of the device at the export scale (worker thread, cancellable)."""
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
                               QTableWidget, QTextEdit, QVBoxLayout)

from . import errlog, export_all, materials, paths

TX = {"fr": {"title": "Exporter toutes les pièces", "intro": "Chaque pièce cochée est exportée dans son propre dossier, avec l'échelle d'export de l'appareil{sc}. La pièce personnalisée garde sa décoration ; les autres sortent non décorées (miroir appliqué pour une main gauche Kinetic).",
             "all": "Tout cocher", "none": "Aucune", "go": "Exporter…", "cancel": "Annuler", "close": "Fermer", "running": "En cours : {p} ({i}/{n})",
             "done": "Terminé : {ok} exportée(s), {sk} ignorée(s), {fl} en échec.\nDossier : {d}", "pick": "Choisir le dossier d'export", "none_sel": "Cochez au moins une pièce.", "stopped": "Arrêté.",
             "sc_on": " ({p:g} %)", "sc_off": " (échelle d'export non cochée : 100 %)", "deco": " — décorée", "quick_title": "Exporter tout, prêt pour Bambu", "quick_intro": "Toutes les pièces sont exportées à l'échelle calculée{sc}, chacune dans son dossier. La pièce personnalisée garde son motif et un fichier .3mf prêt pour Bambu Studio est créé.", "reveal": "Ouvrir le dossier", "bambu": "Ouvrir dans Bambu Studio (couleurs prêtes)", "crash": "Export interrompu",
             "printer": "Imprimante :", "col_part": "Pièce", "col_mat": "Matière", "col_col": "Couleur",
             "sum": "{n} filament(s) pour les pièces{m}", "sum_motif": " + {k} couleur(s) du motif", "mat_note": "Matières proposées d'après le nom des fichiers (TPU si « TPU », « flex » ou « souple ») : vérifiez dans le manuel de l'appareil."},
      "en": {"title": "Export all parts", "intro": "Each ticked part is exported in its own folder at the device's export scale{sc}. The customised part keeps its decoration; the others are exported undecorated (mirrored for a left Kinetic hand).",
             "all": "Tick all", "none": "None", "go": "Export…", "cancel": "Cancel", "close": "Close", "running": "Working: {p} ({i}/{n})",
             "done": "Done: {ok} exported, {sk} skipped, {fl} failed.\nFolder: {d}", "pick": "Choose the export folder", "none_sel": "Tick at least one part.", "stopped": "Stopped.",
             "sc_on": " ({p:g} %)", "sc_off": " (export scale unticked: 100 %)", "deco": " — decorated", "quick_title": "Export everything, ready for Bambu", "quick_intro": "All parts are exported at the computed scale{sc}, each in its own folder. The customised part keeps its motif and a .3mf file ready for Bambu Studio is created.", "reveal": "Open the folder", "bambu": "Open in Bambu Studio (colours ready)", "crash": "Export interrupted",
             "printer": "Printer:", "col_part": "Part", "col_mat": "Material", "col_col": "Colour",
             "sum": "{n} filament(s) for the parts{m}", "sum_motif": " + {k} motif colour(s)", "mat_note": "Materials suggested from the file names (TPU for \"TPU\", \"flex\" or \"souple\"): check the device's manual."}}


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
        self.list.setMaximumHeight(110); v.addWidget(self.list); self.list.setVisible(not quick)
        self.lang = lang; self._build_materials(v, items, quick)
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

    def _build_materials(self, v, items, quick):
        """Printer + one material and colour per part (advanced mode); the simple mode keeps the suggestions and the last printer."""
        row = QHBoxLayout(); row.addWidget(QLabel(self.t("printer"))); self.printer = QComboBox()
        for k, p in materials.PRINTERS.items(): self.printer.addItem(p[self.lang], k)
        self.printer.setCurrentIndex(max(0, self.printer.findData(paths.get_setting("printer", materials.DEFAULT_PRINTER)))); row.addWidget(self.printer, 1); v.addLayout(row)
        self.mat = QTableWidget(len(items), 3); self.mat.setHorizontalHeaderLabels([self.t("col_part"), self.t("col_mat"), self.t("col_col")])
        self.mat.verticalHeader().setVisible(False); self.mat.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.mat_paths = []
        for r, it in enumerate(items):
            self.mat.setCellWidget(r, 0, QLabel(it["label"].split(" — ")[0])); m = QComboBox(); c = QComboBox()
            for k in materials.MATERIALS: m.addItem(k, k)
            for k, (fr, en, h) in materials.COLOURS.items(): c.addItem(fr if self.lang == "fr" else en, k)
            sug = materials.suggest_material(Path(str(it["path"])).name); m.setCurrentIndex(m.findData(sug)); c.setCurrentIndex(c.findData(materials.DEFAULT_COLOUR[sug]))
            m.currentIndexChanged.connect(self._refresh_plan); c.currentIndexChanged.connect(self._refresh_plan)
            self.mat.setCellWidget(r, 1, m); self.mat.setCellWidget(r, 2, c); self.mat_paths.append(it["path"])
        self.mat.setMinimumHeight(min(260, 34 + 30 * len(items))); self.mat.setVisible(not quick); v.addWidget(self.mat, 1)
        self.note = QLabel(self.t("mat_note")); self.note.setWordWrap(True); self.note.setVisible(not quick); v.addWidget(self.note)
        self.summary = QLabel(); self.summary.setWordWrap(True); v.addWidget(self.summary)
        self.printer.currentIndexChanged.connect(self._refresh_plan); self.list.itemChanged.connect(self._refresh_plan); self._refresh_plan()

    def choices(self):
        """{resolved part path: (material, colour key)} from the table."""
        return {str(Path(str(p)).resolve()): (self.mat.cellWidget(r, 1).currentData(), self.mat.cellWidget(r, 2).currentData()) for r, p in enumerate(self.mat_paths)}

    def _motif_count(self):
        if not self.decorated: return 0
        s = self.decorated[1]; return max(1, int(getattr(s, "ncolors", 1) or 1)) if getattr(s, "mode", "") in ("relief", "inlay") else 0

    def plan(self):
        """Filament plan of the ticked parts (the motif colours are only counted: their exact colours are known after the export)."""
        ticked = {str(Path(str(p)).resolve()) for _, p in self.selected()}; ch = self.choices()
        its = [{"label": k, "material": m, "colour": c} for k, (m, c) in ch.items() if k in ticked]
        return materials.plan(its, self.printer.currentData(), self.lang), self._motif_count()

    def _refresh_plan(self, *_):
        if not hasattr(self, "summary"): return
        pl, k = self.plan(); slots = materials.PRINTERS[self.printer.currentData()]["slots"]; n = len(pl.filaments) + k
        txt = self.t("sum").format(n=len(pl.filaments), m=self.t("sum_motif").format(k=k) if k else "")
        errs = list(pl.errors) + ([f"{n} > {slots}"] if slots is not None and n > slots and not pl.errors else [])
        note = materials.PRINTERS[self.printer.currentData()]["note_" + self.lang]
        self.summary.setText(txt + (f"<br><span style='color:#b00020'>⚠ {'<br>⚠ '.join(errs)}</span>" if errs else "") + (f"<br><i>{note}</i>" if note else ""))

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
        self.ctx = dict(self.ctx, printer=self.printer.currentData(), materials=self.choices(), lang=self.lang)
        try: paths.save_setting("printer", self.printer.currentData())
        except OSError: pass
        self.out = Path(d) / ("export_toutes_les_pieces" + self.ctx.get("folder_suffix", "")); self.cancel_flag.clear(); self.bar.setRange(0, len(parts)); self.bar.setValue(0); self.bar.setVisible(True)
        self.b_go.setEnabled(False); self.b_cancel.setEnabled(True); self.log.clear()
        QThreadPool.globalInstance().start(_Job(lambda: self._work(parts)))

    def _work(self, parts):
        """Worker thread. Whatever happens (e.g. destination not writable), `finished` is emitted so the dialog never stays stuck."""
        try: results = export_all.run(parts, self.decorated, self.out, self.ctx, lambda i, n, m: self.sig.progress.emit(i, n, m), self.cancel_flag.is_set)
        except Exception as e:
            try: errlog.get_logger().exception("Export de toutes les pièces interrompu (%s)", self.out)
            except Exception: pass
            results = [{"part": self.t("crash"), "file": "", "status": "failed", "message": f"{type(e).__name__}: {e}"[:300], "folder": None}]
        self.sig.finished.emit(results)

    def _progress(self, i, n, msg):
        self.bar.setValue(i); self.bar.setFormat(self.t("running").format(p=msg, i=min(i + 1, n), n=n) if msg else "")

    def _finished(self, results):
        self.b_go.setEnabled(True); self.b_cancel.setEnabled(False); self.bar.setVisible(False)
        n = {k: sum(1 for r in results if r["status"] == k and r.get("kind") != "device") for k in ("ok", "skipped", "failed")}   # parts only
        txt = self.t("done").format(ok=n["ok"], sk=n["skipped"], fl=n["failed"], d=self.out) + ("\n" + self.t("stopped") if self.cancel_flag.is_set() else "")
        self.log.setPlainText(txt + "\n\n" + "\n".join(f"[{r['status']}] {r['part']} — {r['message']}" for r in results if r["status"] != "ok" or r.get("kind") == "device"))
        self.results = results; self.b_reveal.setVisible(n["ok"] > 0)
        dev = sorted(Path(self.out).glob("APPAREIL_Bambu_pret*.3mf")) if self.out else []          # whole device first, else the customised part
        self.bambu_file = dev[0] if dev else (next(iter(sorted(Path(self.out).rglob("*_Bambu_pret.3mf"))), None) if self.out else None); self.b_bambu.setVisible(self.bambu_file is not None)
