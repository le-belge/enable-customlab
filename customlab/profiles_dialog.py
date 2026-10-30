"""Beneficiary profiles (pseudonymised): successive measurements, saved customisations, comparison, history.

Only an alias is stored (no name/address/photo). Each record keeps the full project state so a new version of the
device can be regenerated when the measurements change (growth follow-up).
"""
import os
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QTextEdit, QVBoxLayout)

from .store import Store

TD = {
 "fr": {"title": "Profils bénéficiaires (pseudonymes)", "notice": "Utilisez un pseudonyme : aucune donnée identifiante n'est demandée ni stockée. Les données restent sur cet ordinateur.",
        "new": "Nouveau profil…", "alias": "Pseudonyme du bénéficiaire :", "delete": "Supprimer le profil…", "save": "Enregistrer le projet actuel dans ce profil",
        "reload": "Recharger la sélection", "compare": "Comparer deux prises (sélectionner 2 lignes)", "made": "Marquer fabriquée / non fabriquée",
        "cols": ["Date", "Appareil", "Côté", "Mesures", "Statut", "Fabriquée"], "yes": "oui", "no": "non", "nothing": "Rien à enregistrer : le dimensionnement n'est pas calculé (mesures manquantes, hors plage ou appareil indisponible).",
        "pick": "Sélectionnez d'abord un profil.", "pick2": "Sélectionnez exactement deux lignes.", "confirm": "Supprimer ce profil et tout son historique ? Cette action est définitive.",
        "diff": "Mesure · avant → après (écart)", "problems": "Éléments introuvables"},
 "en": {"title": "Beneficiary profiles (pseudonyms)", "notice": "Use a pseudonym: no identifying data is requested or stored. Data stays on this computer.",
        "new": "New profile…", "alias": "Beneficiary pseudonym:", "delete": "Delete profile…", "save": "Save the current project in this profile",
        "reload": "Reload the selection", "compare": "Compare two sessions (select 2 rows)", "made": "Mark made / not made",
        "cols": ["Date", "Device", "Side", "Measures", "Status", "Made"], "yes": "yes", "no": "no", "nothing": "Nothing to save: sizing is not computed (missing measurements, out of range or device unavailable).",
        "pick": "Select a profile first.", "pick2": "Select exactly two rows.", "confirm": "Delete this profile and its whole history? This cannot be undone.",
        "diff": "Measure · before → after (change)", "problems": "Items not found"},
}


def beneficiaries_store():
    return Store(Path(os.environ.get("CUSTOMLAB_HOME") or Path.home() / ".customlab") / "beneficiaries")


class BeneficiaryDialog(QDialog):
    def __init__(self, win, store=None):
        super().__init__(win); self.win = win; self.store = store or beneficiaries_store(); self.pid = None
        self.resize(900, 520); self.t = lambda k: TD[win.lang][k]
        self.setWindowTitle(self.t("title")); root = QVBoxLayout(self)
        self.notice = QLabel(self.t("notice")); self.notice.setWordWrap(True); self.notice.setStyleSheet("color:#0b314d"); root.addWidget(self.notice)
        body = QHBoxLayout(); root.addLayout(body, 1)
        left = QVBoxLayout(); self.list = QListWidget(); self.list.currentRowChanged.connect(self._select)
        self.b_new = QPushButton(self.t("new")); self.b_new.clicked.connect(lambda: self.new_profile()); self.b_del = QPushButton(self.t("delete")); self.b_del.clicked.connect(lambda: self.delete_profile(ask=True))
        for x in (self.list, self.b_new, self.b_del): left.addWidget(x)
        body.addLayout(left, 1)
        right = QVBoxLayout(); self.table = QTableWidget(0, 6); self.table.setHorizontalHeaderLabels(self.t("cols")); self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True); self.table.setColumnWidth(3, 300); self.table.setEditTriggers(QTableWidget.NoEditTriggers); right.addWidget(self.table, 1)
        row = QHBoxLayout(); self.b_save = QPushButton(self.t("save")); self.b_reload = QPushButton(self.t("reload")); self.b_cmp = QPushButton(self.t("compare")); self.b_made = QPushButton(self.t("made"))
        self.b_save.clicked.connect(lambda: self.save_current()); self.b_reload.clicked.connect(lambda: self.reload_selected()); self.b_cmp.clicked.connect(lambda: self.compare_selected()); self.b_made.clicked.connect(lambda: self.toggle_made())
        for x in (self.b_save, self.b_reload, self.b_cmp, self.b_made): row.addWidget(x)
        right.addLayout(row); self.out = QTextEdit(); self.out.setReadOnly(True); self.out.setMaximumHeight(120); right.addWidget(self.out)
        body.addLayout(right, 3); self.refresh_list()

    # ---- data
    def refresh_list(self, select=None):
        self.list.blockSignals(True); self.list.clear(); self.profiles = self.store.list_profiles()
        for p in self.profiles: self.list.addItem(f"{p['alias']}  ({p['records']})")
        self.list.blockSignals(False)
        idx = next((i for i, p in enumerate(self.profiles) if p["id"] == (select or self.pid)), -1)
        self.list.setCurrentRow(idx)
        if idx < 0: self.pid = None; self._fill_table()

    def _select(self, row):
        self.pid = self.profiles[row]["id"] if 0 <= row < len(self.profiles) else None; self._fill_table()

    def records(self): return self.store.load(self.pid)["records"] if self.pid else []

    def _fill_table(self):
        recs = self.records(); self.table.setRowCount(len(recs))
        for i, r in enumerate(recs):
            m = ", ".join(f"{k}={v:g}" if isinstance(v, (int, float)) else f"{k}={v}" for k, v in r["measurements"].items())
            vals = [r["date"], r["device_id"], r["side"], m, r["status"], self.t("yes") if r["fabricated"] else self.t("no")]
            for j, v in enumerate(vals): self.table.setItem(i, j, QTableWidgetItem(str(v)))

    def selected_rows(self): return sorted({i.row() for i in self.table.selectedIndexes()})

    # ---- actions (callable without exec for tests)
    def new_profile(self, alias=None):
        if alias is None:
            alias, ok = QInputDialog.getText(self, self.t("title"), self.t("alias"))
            if not ok: return None
        alias = (alias or "").strip()
        if not alias: return None
        pid = self.store.create(alias); self.refresh_list(select=pid); return pid

    def delete_profile(self, ask=True):
        if not self.pid: return False
        if ask and QMessageBox.question(self, self.t("title"), self.t("confirm")) != QMessageBox.Yes: return False
        self.store.delete(self.pid); self.pid = None; self.refresh_list(); return True

    def save_current(self):
        if not self.pid: self.out.setPlainText(self.t("pick")); return None
        if self.win.sizing is None: self.out.setPlainText(self.t("nothing")); return None
        idx = self.store.add_record(self.pid, self.win.sizing, customization={"state": self.win.state_dict()}, fabricated=False)
        self.refresh_list(); self.table.selectRow(idx); return idx

    def reload_selected(self, row=None):
        rows = [row] if row is not None else self.selected_rows()
        if len(rows) != 1: self.out.setPlainText(self.t("pick2").replace("deux lignes", "une ligne").replace("two rows", "one row")); return None
        state = self.records()[rows[0]]["customization"].get("state")
        problems = self.win.load_state(state) if state else []
        if problems: self.out.setPlainText(self.t("problems") + " :\n" + "\n".join(problems))
        return problems

    def compare_selected(self, rows=None):
        rows = rows or self.selected_rows()
        if len(rows) != 2 or not self.pid: self.out.setPlainText(self.t("pick2")); return None
        d = self.store.compare(self.pid, rows[0], rows[1]); lines = [self.t("diff")]
        for k, v in d.items():
            if v["from"] is None or v["to"] is None: lines.append(f"{k} : {v['from']} → {v['to']}"); continue
            pct = f" ({v['delta'] / v['from'] * 100:+.1f} %)" if v["from"] else ""
            unit = " mm" if (k.endswith("mm") or k in ("HandLen", "ForearmLen", "BicepCircum")) else (" points de %" if "percent" in k else "")
            lines.append(f"{k} : {v['from']:g} → {v['to']:g}  ({v['delta']:+g}{unit}{pct})")
        text = "\n".join(lines); self.out.setPlainText(text); return text

    def toggle_made(self, row=None):
        rows = [row] if row is not None else self.selected_rows()
        if len(rows) != 1 or not self.pid: return None
        cur = self.records()[rows[0]]["fabricated"]; self.store.set_fabricated(self.pid, rows[0], not cur); self._fill_table(); return not cur
