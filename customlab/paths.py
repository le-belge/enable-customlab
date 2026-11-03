"""Where things live: bundled resources (next to the code, or inside the frozen app) and the user's own folders.

The user's source files (SCAD / STL downloaded from the official pages) are never bundled: they go in the "sources" folder, whose
location is chosen in the app (menu Aide > Fichiers sources) and remembered in <home>/settings.json.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))


def resource_dir():
    """Folder holding docs/, examples/, tools/ : the project root, or the unpacked frozen app."""
    return Path(getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parent.parent)


def home():
    return Path(os.environ.get("CUSTOMLAB_HOME") or Path.home() / ".customlab")


def write_text_atomic(path, text):
    """Write a UTF-8 text file all at once: a crash or a full disk leaves the old file, never a truncated one (temp file + os.replace)."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(text); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try: os.remove(tmp)
        except OSError: pass
        raise


def _read_settings():
    """-> dict, {} when absent, None when present but unreadable."""
    f = home() / "settings.json"
    if not f.exists(): return {}
    try: d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError): return None
    return d if isinstance(d, dict) else None


def _settings(): return _read_settings() or {}


def save_setting(key, value):
    f = home() / "settings.json"; d = _read_settings()
    if d is None:                                   # unreadable: keep it aside as settings.json.bak instead of silently dropping every other setting
        from . import errlog
        bak = f.with_name(f.name + ".bak")
        try: os.replace(f, bak); errlog.warning(f"Réglages illisibles mis de côté : {bak}")
        except OSError as e: errlog.warning(f"Réglages illisibles, mise de côté impossible : {e!r}")
        d = {}
    d[key] = value; write_text_atomic(f, json.dumps(d, indent=2, ensure_ascii=False))


def get_setting(key, default=None):
    return _settings().get(key, default)


def sources_dir():
    """User's sources folder: $CUSTOMLAB_SOURCES, else the folder chosen in the app, else <project>/sources (development), else <home>/sources."""
    env = os.environ.get("CUSTOMLAB_SOURCES")
    if env: return Path(env)
    chosen = get_setting("sources_dir")
    if chosen: return Path(chosen)
    dev = resource_dir() / "sources"
    if not FROZEN and dev.is_dir(): return dev
    return home() / "sources"


def resolve(rel):
    """Path of a profile/spec entry: 'sources/...' lives in the user's sources folder, anything else next to the code."""
    rel = str(rel)
    if rel.startswith("sources/"): return sources_dir() / rel[len("sources/"):]
    return resource_dir() / rel


def find_file(name, subfolder=None):
    """A file of the given name anywhere under the sources folder (first under <subfolder>, then everywhere), case-insensitive; None if absent."""
    root = sources_dir(); low = name.lower()
    for base in ([root / subfolder] if subfolder else []) + [root]:
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.name.lower() == low and p.is_file(): return p
    return None
