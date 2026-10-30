"""Catalogue pictures: one rendering per device, made from the local STL files and cached as PNG (nothing third-party is embedded).

Each device lists the files to show (side by side, one common scale). A device whose files are absent gets no picture and the card
shows a neutral placeholder instead. Rendering runs in a worker thread (pure numpy; no widget is touched there).
"""
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PySide6.QtGui import QImage

from . import cache
from . import paths
from .meshio import read_stl

ROOT = Path(__file__).resolve().parent.parent
HOME = lambda: Path(os.environ.get("CUSTOMLAB_HOME") or Path.home() / ".customlab")
W, H = 480, 300
BG = np.array([244, 245, 247], np.uint8)

# device -> glob patterns (relative to the project root or the user's folder), in display order; (yaw, pitch) of the view
SPECS = {
    "phoenix_hand": {"files": ["customlab/bundled_parts/phoenix_jesimon_100pct/left/files/*Palm*.stl", "customlab/bundled_parts/phoenix_jesimon_100pct/left/files/*Gauntlet*.stl"], "view": (0.6, -0.5)},
    "kinetic_hand": {"files": ["sources/kinetic_hand/stl/Kinetic Hand/Digital Fitment/*.stl"], "view": (0.0, -1.2)},
    "kinetic_arm": {"files": ["sources/kinetic_arm/stl/UpArmCov100.STL", "sources/kinetic_arm/stl/TypeB-Forearm100.STL", "sources/kinetic_arm/stl/PalmRH100.STL"], "view": (0.5, -0.5)},
    "unlimbited_arm": {"files": ["@generated/unlimbited_arm_*/Cuff_left.stl", "@generated/unlimbited_arm_*/Forearm_left.stl"], "view": (0.6, -0.5)},
}


def _resolve(pattern):
    if pattern.startswith("@generated/"): base, pat = HOME() / "generated", pattern[len("@generated/"):]
    elif pattern.startswith("sources/"): base, pat = paths.sources_dir(), pattern[len("sources/"):]
    else: base, pat = paths.resource_dir(), pattern
    found = sorted(base.glob(pat)) if base.exists() else []
    return found[0] if found else None


def sources(pid):
    spec = SPECS.get(pid)
    if not spec: return []
    files = [_resolve(p) for p in spec["files"]]; return [f for f in files if f]


def _png(pid): return HOME() / "cache" / f"thumb_{pid}.png"


def _stamp(files): return "|".join(f"{f}:{f.stat().st_size}:{f.stat().st_mtime_ns}" for f in files)


def cached(pid):
    """Path of an up-to-date picture, or None."""
    files = sources(pid); p = _png(pid); s = p.with_suffix(".txt")
    if files and p.is_file() and s.is_file() and s.read_text() == _stamp(files): return p
    return None


def render(pid):
    """(Re)make the picture of one device; returns its path or None if its files are absent."""
    files = sources(pid)
    if not files: return None
    parts, x = [], 0.0
    for f in files:
        t = np.asarray(read_stl(f), float).reshape(-1, 3, 3); p = t.reshape(-1, 3); t = t - (p.max(0) + p.min(0)) / 2
        w = float(np.ptp(t[:, :, 0])); t[:, :, 0] += x + w / 2; x += w * 1.08; parts.append(t)
    p = _png(pid); _draw(np.concatenate(parts), SPECS[pid]["view"], W, H, p); p.with_suffix(".txt").write_text(_stamp(files)); return p


def _draw(tris, view, w, h, out_png, zoom=1.1):
    """Shaded picture with a transparent background, saved as PNG (pure numpy + QImage: safe in a worker thread)."""
    pts = tris.reshape(-1, 3); centre = (pts.max(0) + pts.min(0)) / 2; radius = float(np.linalg.norm(pts - centre, axis=1).max()) or 1.0
    o = SimpleNamespace(tris=tris, yaw=view[0], pitch=view[1], zoom=zoom, radius=radius, centre=centre, hl=np.zeros(len(tris), bool), hlc=np.zeros((len(tris), 3)), use_hlc=False, dragging=False)
    from .viewer import MeshView
    img = MeshView.render_image(o, w, h); diff = np.abs(img.astype(int) - BG).max(2); alpha = np.clip(diff * 10, 0, 255).astype(np.uint8)
    rgba = np.dstack([img, alpha]); qi = QImage(np.ascontiguousarray(rgba).data, w, h, w * 4, QImage.Format_RGBA8888).copy()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True); qi.save(str(out_png))


# ---- one picture per part (library drop-down)
def part_png(path): return HOME() / "cache" / f"pt2_{cache.key(path)}.png"


def part_cached(path):
    p = part_png(path); return p if p.is_file() else None


def part_render(path, w=320, h=240):
    p = part_png(path); _draw(np.asarray(read_stl(path), float).reshape(-1, 3, 3), (0.6, -0.5), w, h, p, zoom=1.3); return p


def ensure(pid):
    """Cached picture, made if needed."""
    return cached(pid) or render(pid)
