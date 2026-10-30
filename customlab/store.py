"""Local pseudonymised beneficiary profiles with measurement history.

Stores only an alias (free text chosen by the volunteer — advise a pseudonym),
measurements, device choice, fabrication history. No name/address/photo fields.
"""
import json
import uuid
from datetime import date
from pathlib import Path


class Store:
    def __init__(self, root):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, pid): return self.root / f"{pid}.json"

    def create(self, alias):
        pid = uuid.uuid4().hex[:12]
        self._save({"id": pid, "alias": alias, "records": []})
        return pid

    def load(self, pid): return json.loads(self._path(pid).read_text(encoding="utf-8"))

    def _save(self, d): self._path(d["id"]).write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_record(self, pid, sizing, customization=None, fabricated=False, on=None):
        d = self.load(pid)
        d["records"].append({
            "date": (on or date.today()).isoformat(),
            "device_id": sizing.device_id, "profile_version": sizing.profile_version,
            "side": sizing.side, "measurements": sizing.measurements,
            "status": sizing.status, "customization": customization or {},
            "fabricated": fabricated})
        self._save(d)
        return len(d["records"]) - 1

    def compare(self, pid, i, j):
        r = self.load(pid)["records"]
        a, b = r[i]["measurements"], r[j]["measurements"]
        return {k: {"from": a.get(k), "to": b.get(k),
                    "delta": (b[k] - a[k]) if k in a and k in b else None}
                for k in sorted(set(a) | set(b))}

    def delete(self, pid): self._path(pid).unlink()

    def list_profiles(self):
        out = []
        for f in sorted(self.root.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8")); out.append({"id": d["id"], "alias": d["alias"], "records": len(d["records"])})
        return sorted(out, key=lambda x: x["alias"].lower())

    def set_fabricated(self, pid, idx, flag=True):
        d = self.load(pid); d["records"][idx]["fabricated"] = bool(flag); self._save(d)
