"""Disk cache of the slow, deterministic part of loading a part: the proposed viewing axis and the height maps.

Keyed by the STL's resolved path, size and modification time (+ mirroring, axis, resolution): a changed file never hits an old
entry. Entries live in <CUSTOMLAB_HOME or ~/.customlab>/cache and the oldest are dropped beyond MAX_MB. Disabled in synchronous
(test) mode unless CUSTOMLAB_CACHE=1, so tests never touch the user's folder.
"""
import hashlib, json, os, tempfile
from pathlib import Path

import numpy as np

from .deco import HeightMap

MAX_MB = 400


def enabled(): return os.environ.get("CUSTOMLAB_SYNC") != "1" or os.environ.get("CUSTOMLAB_CACHE") == "1"


def _dir():
    d = Path(os.environ.get("CUSTOMLAB_HOME") or Path.home() / ".customlab") / "cache"; d.mkdir(parents=True, exist_ok=True); return d


def key(path, *extra):
    st = os.stat(path); return hashlib.sha1(f"{Path(path).resolve()}|{st.st_size}|{st.st_mtime_ns}|{extra}".encode()).hexdigest()[:24]


def _write(name, writer):
    d = _dir(); fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp"); os.close(fd)
    try: writer(tmp); os.replace(tmp, d / name)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    _prune(d)


def _prune(d):
    files = sorted((f for f in d.iterdir() if f.is_file()), key=lambda f: f.stat().st_mtime); total = sum(f.stat().st_size for f in files)
    while files and total > MAX_MB * 1e6: f = files.pop(0); total -= f.stat().st_size; f.unlink(missing_ok=True)


def _save_hm(t, hm):
    with open(t, "wb") as f: np.savez(f, axis=hm.axis, res=hm.res, u0=hm.u0, v0=hm.v0, H=hm.H, tw=hm.thickness_w)


def get_axis(path, mirror):
    if not enabled(): return None
    try: return json.loads((_dir() / f"ax_{key(path, mirror)}.json").read_text())
    except (OSError, ValueError): return None


def put_axis(path, mirror, axis, scores):
    if enabled():
        try: _write(f"ax_{key(path, mirror)}.json", lambda t: Path(t).write_text(json.dumps({"axis": axis, "scores": scores})))
        except OSError: pass


def get_hm(path, mirror, axis, res):
    if not enabled(): return None
    f = _dir() / f"hm_{key(path, mirror, axis, res)}.npz"
    try:
        with np.load(f) as z: return HeightMap(str(z["axis"]), float(z["res"]), float(z["u0"]), float(z["v0"]), z["H"], float(z["tw"]))
    except (OSError, ValueError, KeyError): return None


def put_hm(path, mirror, axis, res, hm):
    if enabled():
        try: _write(f"hm_{key(path, mirror, axis, res)}.npz", lambda t: _save_hm(t, hm))
        except OSError: pass
