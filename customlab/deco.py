"""Decoration of REAL parts (STL at original size): text, SVG and raster motifs projected on the surface.

Method: the part is rasterised along a chosen projection axis into a height map (z-buffer of the outer
surface). A 2D mask (text / SVG / image, positioned and sized by the user) is turned into a solid that
follows the real surface: relief (shell added on top, embedded slightly so slicers merge it) or engraving
(cutter subtracted with OpenSCAD, only on closed/manifold parts). Original files are never modified.

EXPERIMENTAL. Depth caps and slope limits below are software heuristics, NOT documented e-NABLE rules.
Functional zones (joints, pin holes, cable channels, skin-contact surfaces) are NOT detected automatically:
the user must mark exclusion zones and a qualified volunteer must review the result.
"""
import hashlib
import json
import math
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from . import openscad
from . import bambu3mf
from .bambu3mf import write_bambu_3mf
from .licenseinfo import read_license_info
from .meshio import is_watertight, read_stl, write_stl

# rows: (u, v, w) = R @ (x, y, z); w points toward the viewer; all rotations are right-handed (det +1)
AXES = {
    "+z": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "-z": [[1, 0, 0], [0, -1, 0], [0, 0, -1]],
    "+x": [[0, 1, 0], [0, 0, 1], [1, 0, 0]], "-x": [[0, -1, 0], [0, 0, 1], [-1, 0, 0]],
    "+y": [[0, 0, 1], [1, 0, 0], [0, 1, 0]], "-y": [[0, 0, -1], [1, 0, 0], [0, -1, 0]],
}
MAX_RELIEF_MM, MAX_ENGRAVE_MM, MAX_INLAY_MM, MIN_DEPTH_MM = 2.0, 1.0, 1.5, 0.2
INLAY_TOP_OFFSET_MM = 0.10       # default: inlay top stands 0.10 mm above the sampled surface so it wins over the base in the slicer (tested on one logo: grey streaks gone)
INLAY_LEGACY_OFFSET_MM = -0.02   # value used before the setting existed (flush, nothing protrudes): applied to saved projects that lack the field
INLAY_OFFSET_RANGE = (-0.05, 0.30)   # accepted values of DecoSpec.inlay_offset_mm (app bound, not a manual value); outside → refused, never clamped
ENGRAVE_MAX_FRACTION_OF_THICKNESS = 0.3
SLOPE_WARN_DEG, SLOPE_REFUSE_DEG = 35.0, 60.0
EMBED_MM = 0.4
DISCLAIMER = ("Décoration EXPÉRIMENTALE. Zones fonctionnelles (articulations, trous de broches, passages de câbles, "
              "surfaces en contact avec la peau) non détectées automatiquement ; aucune validation physique ou clinique.")


class DecoError(ValueError):
    pass


@dataclass
class DecoSpec:
    kind: str = "text"            # text | svg | image
    text: str = ""
    path: str = ""                # svg / image file
    font_family: str = ""
    bold: bool = True
    size_mm: float = 20.0         # larger dimension of the artwork
    rotation_deg: float = 0.0
    u: float = 0.0                # centre in the projection plane (mm), as shown in the placement view
    v: float = 0.0
    depth_mm: float = 1.0
    mode: str = "relief"          # relief | engrave | inlay
    axis: str = "+z"
    invert_image: bool = False
    mirror_x: bool = False        # left-hand parts supplied as right-hand models (Kinetic): mirrored BEFORE decorating so text stays readable
    inlay_offset_mm: float = INLAY_TOP_OFFSET_MM   # inlay only: top relative to the surface (>0 stands proud so it wins over the base in the slicer)
    protect_margin_mm: float = 2.0  # automatic no-go margin around through-holes/slots (0 = off); steep rims get 1 mm
    res_mm: float = 0.15          # decoration grid (mm): 0.25 standard, 0.15 fine, 0.10 very fine (more triangles)
    smooth_source: bool = True    # raster images: smooth upscaling before thresholding (rounder edges from low-res logos)
    ncolors: int = 1              # SVG/image: 1 = single piece; 2-4 = one piece per colour (relief/inlay)
    camo_style: str = "fr"        # kind "camo": palette (see camo.PALETTES)
    camo_seed: int = 1            # kind "camo": same seed = same patches
    camo_scale_mm: float = 28.0   # kind "camo": size of the patches
    threshold: int = 128          # raster images: luminance below this is decorated (0-255)
    white_is_empty: bool = True   # SVG/image: near-white fills (logos drawn on white) are NOT decorated
    extra: tuple = ()             # further motifs (DecoSpec), sharing mode/depth/axis/quality of this one: several texts / logos on the same part
    thicken_thin: bool = False    # SVG/image: strokes thinner than MIN_FEATURE_MM are widened (by THICKEN_MM each side) so the slicer keeps them


@dataclass
class HeightMap:
    axis: str
    res: float
    u0: float
    v0: float
    H: np.ndarray                 # (nu, nv) node heights, NaN where the part has no surface
    thickness_w: float

    @property
    def shape(self): return self.H.shape


def _ensure_qt():
    from PySide6.QtWidgets import QApplication, QWidget   # a QApplication also serves widgets created later
    if QApplication.instance() is None:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        QApplication([])


def mirror_tris(tris):
    """Mirror X and reverse the winding so that the normals still point outward."""
    a = np.asarray(tris, float).reshape(-1, 3, 3).copy(); a[:, :, 0] *= -1; a = a[:, [0, 2, 1], :]
    return [tuple(map(tuple, t)) for t in a.tolist()]


def to_uvw(tris, axis):
    return np.asarray(tris, float).reshape(-1, 3) @ np.array(AXES[axis], float).T


def from_uvw(pts, axis):
    return np.asarray(pts, float) @ np.array(AXES[axis], float)


def _raster_loop(P, H, u0, v0, res, nu, nv):
    """Reference rasteriser: one triangle at a time (used for the few large triangles, and as the test oracle)."""
    for (a, b, c) in P:
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12: continue
        i0, i1 = int(max(0, math.floor((min(a[0], b[0], c[0]) - u0) / res))), int(min(nu - 1, math.ceil((max(a[0], b[0], c[0]) - u0) / res)))
        j0, j1 = int(max(0, math.floor((min(a[1], b[1], c[1]) - v0) / res))), int(min(nv - 1, math.ceil((max(a[1], b[1], c[1]) - v0) / res)))
        U = (u0 + np.arange(i0, i1 + 1) * res)[:, None]; V = (v0 + np.arange(j0, j1 + 1) * res)[None, :]
        l1 = ((b[1] - c[1]) * (U - c[0]) + (c[0] - b[0]) * (V - c[1])) / d
        l2 = ((c[1] - a[1]) * (U - c[0]) + (a[0] - c[0]) * (V - c[1])) / d
        l3 = 1 - l1 - l2
        eps = 1e-9
        inside = (l1 >= -eps) & (l2 >= -eps) & (l3 >= -eps)
        if not inside.any(): continue
        W = l1 * a[2] + l2 * b[2] + l3 * c[2]
        sub = H[i0:i1 + 1, j0:j1 + 1]
        H[i0:i1 + 1, j0:j1 + 1] = np.where(inside, np.maximum(sub, W), sub)


def _raster_small(P, H, u0, v0, res, nu, nv, span=3, chunk=150000):
    """Vectorised rasteriser for triangles covering at most `span` x `span` nodes (fine meshes: hundreds of thousands of them).
    Same maths as _raster_loop; per-node maxima are reduced with a sort instead of a Python loop."""
    eps = 1e-9; Hf = H.reshape(-1)
    for s in range(0, len(P), chunk):
        T = P[s:s + chunk]; a, b, c = T[:, 0], T[:, 1], T[:, 2]
        d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1]); ok = np.abs(d) >= 1e-12
        a, b, c, d = a[ok], b[ok], c[ok], d[ok]
        i0 = np.clip(np.floor((np.minimum(np.minimum(a[:, 0], b[:, 0]), c[:, 0]) - u0) / res), 0, nu - 1).astype(np.int64)
        i1 = np.clip(np.ceil((np.maximum(np.maximum(a[:, 0], b[:, 0]), c[:, 0]) - u0) / res), 0, nu - 1).astype(np.int64)
        j0 = np.clip(np.floor((np.minimum(np.minimum(a[:, 1], b[:, 1]), c[:, 1]) - v0) / res), 0, nv - 1).astype(np.int64)
        j1 = np.clip(np.ceil((np.maximum(np.maximum(a[:, 1], b[:, 1]), c[:, 1]) - v0) / res), 0, nv - 1).astype(np.int64)
        idxs, vals = [], []
        for di in range(span):
            for dj in range(span):
                i = i0 + di; j = j0 + dj; m = (i <= i1) & (j <= j1)
                if not m.any(): continue
                U = u0 + i * res; V = v0 + j * res
                l1 = ((b[:, 1] - c[:, 1]) * (U - c[:, 0]) + (c[:, 0] - b[:, 0]) * (V - c[:, 1])) / d
                l2 = ((c[:, 1] - a[:, 1]) * (U - c[:, 0]) + (a[:, 0] - c[:, 0]) * (V - c[:, 1])) / d
                l3 = 1 - l1 - l2; m &= (l1 >= -eps) & (l2 >= -eps) & (l3 >= -eps)
                if m.any(): idxs.append((i * nv + j)[m]); vals.append((l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2])[m])
        if not idxs: continue
        idx = np.concatenate(idxs); val = np.concatenate(vals); o = np.lexsort((val, idx)); idx, val = idx[o], val[o]
        last = np.r_[idx[1:] != idx[:-1], True]; f = idx[last]; Hf[f] = np.maximum(Hf[f], val[last])


def build_heightmap(tris, axis="+z", res=0.25, margin=2.0) -> HeightMap:
    if axis not in AXES: raise DecoError(f"unknown axis {axis}")
    P = to_uvw(tris, axis).reshape(-1, 3, 3)
    lo, hi = P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0)
    u0, v0 = lo[0] - margin, lo[1] - margin
    nu, nv = int(math.ceil((hi[0] - lo[0] + 2 * margin) / res)) + 1, int(math.ceil((hi[1] - lo[1] + 2 * margin) / res)) + 1
    H = np.full((nu, nv), -np.inf)
    span_u = (P[:, :, 0].max(1) - P[:, :, 0].min(1)) / res; span_v = (P[:, :, 1].max(1) - P[:, :, 1].min(1)) / res
    sp = np.maximum(span_u, span_v); done = np.zeros(len(P), bool)
    for lim, k in ((1.9, 3), (4.9, 6), (10.9, 12), (22.9, 24)):          # buckets: at most k x k nodes, vectorised per bucket
        m = (sp <= lim) & ~done
        if m.any(): _raster_small(P[m], H, u0, v0, res, nu, nv, span=k, chunk=max(2000, 150000 * 9 // (k * k))); done |= m
    if (~done).any(): _raster_loop(P[~done], H, u0, v0, res, nu, nv)
    H[np.isinf(H)] = np.nan
    return HeightMap(axis, res, u0, v0, H, float(hi[2] - lo[2]))


def suggest_axis(tris, res=1.0, max_tris=150000):
    """Viewing axis whose visible surface is flattest/largest (slope < 25 deg). Parts are supplied in print orientation, so the face
    to decorate is not always the +z one. Only axes whose silhouette covers at least 60 % of the largest one are considered (no edge-on view); preference order +z, -z, +y, -y, +x, -x among axes within 80 % of the best score."""
    T = np.asarray(tris, float).reshape(-1, 3, 3)
    if len(T) > max_tris: T = T[::int(np.ceil(len(T) / max_tris))]                     # regular decimation: enough for a 1 mm map
    scores = {}; area = {}; depth = {}
    for ax in AXES:
        hm = build_heightmap(T, ax, res); ok = ~np.isnan(hm.H); area[ax] = int(ok.sum()); depth[ax] = float(np.mean((hm.H[ok] - hm.H[ok].min()) / (np.ptp(hm.H[ok]) + 1e-9))) if ok.any() else 0.0; cell_ok = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
        gu, gv = np.gradient(np.where(ok, hm.H, 0.0), hm.res); slope = np.degrees(np.arctan(np.hypot(gu, gv)))[:-1, :-1]
        scores[ax] = int(((slope < 25.0) & cell_ok).sum() * res * res)
    wide = {a for a in AXES if area[a] >= 0.6 * max(area.values())}                    # an edge-on view (thin silhouette) is never proposed
    best = max(scores[a] for a in wide)
    if best <= 0: return "+z", scores
    cand = [a for a in ("+z", "-z", "+y", "-y", "+x", "-x") if a in wide and scores[a] >= 0.8 * best]
    first = cand[0]
    if first[1] in "xy":                                                    # print orientation: +z/-z keep their order; side faces of a shell: the view whose surface lies nearest the viewer on average is the outer one, not the inside of a shell
        opp = ("-" if first[0] == "+" else "+") + first[1]
        first = max([a for a in cand if a[1] in "xy"] + ([opp] if opp in wide else []), key=lambda a: depth[a])      # an opposite face counts too: flatness scores of the two sides are noisy
    return first, scores


# ---------------------------------------------------------------- artwork -> mask

def _prepare_raster(src, target_px, smooth=True):
    """Low-resolution raster -> smoothly upscaled (up to 3x the target pixel count) and lightly blurred, premultiplied ARGB."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    im = src.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    if not smooth: return im
    longest = max(im.width(), im.height())
    k = max(1.0, min(3.0 * target_px / longest, 2400.0 / longest))
    if k > 1.05:
        im = im.scaled(int(im.width() * k), int(im.height() * k), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    a = np.frombuffer(im.constBits(), np.uint8).reshape(im.height(), im.bytesPerLine() // 4, 4)[:, :im.width(), :].astype(np.float32)
    pad = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge"); acc = np.zeros_like(a)
    for di in range(3):
        for dj in range(3): acc += pad[di:di + a.shape[0], dj:dj + a.shape[1]]
    out = np.ascontiguousarray((acc / 9.0).astype(np.uint8))                    # 3x3 box blur on premultiplied BGRA
    return QImage(out.data, out.shape[1], out.shape[0], out.shape[1] * 4, QImage.Format_ARGB32_Premultiplied).copy()


def _artwork_mask_image(spec: DecoSpec, target_px=300):
    """SVG / raster -> ARGB image whose alpha is the decoration mask, cropped to the drawn content."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter
    max_px = int(min(2400, max(900, 4 * target_px)))
    if spec.kind == "svg":
        from PySide6.QtSvg import QSvgRenderer
        r = QSvgRenderer(spec.path)
        if not r.isValid(): raise DecoError("invalid SVG")
        sz = r.defaultSize(); w, h = (sz.width(), sz.height()) if sz.isValid() and sz.width() > 0 else (100, 100)
        k = max_px / max(w, h); im = QImage(max(1, int(w * k)), max(1, int(h * k)), QImage.Format_ARGB32); im.fill(0)
        q = QPainter(im); q.setRenderHint(QPainter.Antialiasing); r.render(q, QRectF(0, 0, im.width(), im.height())); q.end()
        a = np.frombuffer(im.constBits(), np.uint8).reshape(im.height(), im.bytesPerLine() // 4, 4)[:, :im.width(), :]
        m = a[..., 3] > 127
        if spec.white_is_empty:
            lum = (a[..., 2].astype(int) * 299 + a[..., 1].astype(int) * 587 + a[..., 0].astype(int) * 114) // 1000   # BGRA
            m = m & (lum < 200)
    else:
        src = QImage(spec.path)
        if src.isNull(): raise DecoError("cannot read image")
        im = _prepare_raster(src, target_px, spec.smooth_source)
        a = np.frombuffer(im.constBits(), np.uint8).reshape(im.height(), im.bytesPerLine() // 4, 4)[:, :im.width(), :].astype(float)
        a[..., :3] = a[..., :3] * 255.0 / np.maximum(a[..., 3], 1)[..., None]            # un-premultiply (BGR)
        a = a.astype(int)
        lum = (a[..., 2] * 299 + a[..., 1] * 587 + a[..., 0] * 114) // 1000          # BGRA byte order
        m = (a[..., 3] > 127) & (lum < spec.threshold) if not src.hasAlphaChannel() or a[..., 3].min() > 127 else (a[..., 3] > 127)
        if spec.white_is_empty: m = m & (lum < 200)
        if spec.invert_image: m = (a[..., 3] > 127) & ~m
    ys, xs = np.nonzero(m)
    if not len(xs): raise DecoError("artwork has no drawable content")
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    out = np.zeros(m.shape + (4,), np.uint8); out[m] = 255
    out = np.ascontiguousarray(out)
    return QImage(out.data, m.shape[1], m.shape[0], m.shape[1] * 4, QImage.Format_ARGB32).copy()

def render_mask(spec: DecoSpec, hm: HeightMap) -> np.ndarray:
    """Boolean mask of CELLS, shape (nu-1, nv-1), indexed [i(u), j(v)]."""
    _ensure_qt()
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QTransform
    nu, nv = hm.shape; ncu, ncv = nu - 1, nv - 1
    img = QImage(ncu, ncv, QImage.Format_ARGB32); img.fill(0)
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)
    cx = (spec.u - hm.u0) / hm.res                       # pixel coords: x = u, y = down = -v
    cy = (hm.v0 + ncv * hm.res - spec.v) / hm.res
    p.translate(cx, cy); p.rotate(-spec.rotation_deg)
    S = spec.size_mm / hm.res
    if spec.kind == "text":
        if not spec.text.strip(): raise DecoError("empty text")
        f = QFont(spec.font_family or QFont().family()); f.setPixelSize(200); f.setBold(spec.bold)
        path = QPainterPath(); path.addText(0, 0, f, spec.text)
        b = path.boundingRect()
        if b.width() <= 0 or b.height() <= 0: raise DecoError("text has no outline")
        k = S / max(b.width(), b.height()); p.scale(k, k); p.translate(-b.center().x(), -b.center().y())
        p.fillPath(path, QColor(255, 255, 255))
    elif spec.kind in ("svg", "image"):
        art = _artwork_mask_image(spec, int(spec.size_mm / hm.res))      # white pixels (alpha = mask), page margins removed
        k = S / max(art.width(), art.height()); p.scale(k, k); p.translate(-art.width() / 2, -art.height() / 2)
        p.drawImage(0, 0, art)
    else:
        raise DecoError(f"unknown kind {spec.kind}")
    p.end()
    a = np.frombuffer(img.constBits(), np.uint8).reshape(ncv, img.bytesPerLine() // 4, 4)[:, :ncu, :]
    m = a[..., 3] > 127
    return m[::-1, :].T.copy()                            # rows were top-down (v descending) -> [i(u), j(v)]


def _fix_checkerboards(S):
    S = S.copy()
    while True:
        A = S[:-1, :-1] & S[1:, 1:] & ~S[1:, :-1] & ~S[:-1, 1:]
        B = ~S[:-1, :-1] & ~S[1:, 1:] & S[1:, :-1] & S[:-1, 1:]
        if not A.any() and not B.any(): return S
        S[1:, :-1] |= A; S[:-1, :-1] |= B


# ---------------------------------------------------------------- colour separation
def _artwork_color_image(spec: DecoSpec, target_px=300):
    """SVG / raster -> premultiplied ARGB image keeping colours, background (transparent or near-white) removed, cropped."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter
    max_px = int(min(2400, max(900, 4 * target_px)))
    if spec.kind == "svg":
        from PySide6.QtSvg import QSvgRenderer
        r = QSvgRenderer(spec.path)
        if not r.isValid(): raise DecoError("invalid SVG")
        sz = r.defaultSize(); w, h = (sz.width(), sz.height()) if sz.isValid() and sz.width() > 0 else (100, 100)
        k = max_px / max(w, h); im = QImage(max(1, int(w * k)), max(1, int(h * k)), QImage.Format_ARGB32_Premultiplied); im.fill(0)
        q = QPainter(im); q.setRenderHint(QPainter.Antialiasing); r.render(q, QRectF(0, 0, im.width(), im.height())); q.end()
    else:
        src = QImage(spec.path)
        if src.isNull(): raise DecoError("cannot read image")
        im = _prepare_raster(src, target_px, spec.smooth_source)
    arr = np.frombuffer(im.constBits(), np.uint8).reshape(im.height(), im.bytesPerLine() // 4, 4)[:, :im.width(), :].astype(float)
    a = arr[..., 3]; rgb = arr[..., :3] * 255.0 / np.maximum(a, 1)[..., None]            # BGR, un-premultiplied
    content = a > 127
    if spec.white_is_empty: content &= ~(rgb.min(axis=2) > 215)
    ys, xs = np.nonzero(content)
    if not len(xs): raise DecoError("artwork has no drawable content")
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    out = np.where(content[sl][..., None], arr[sl], 0).astype(np.uint8)
    out = np.ascontiguousarray(out)
    return QImage(out.data, out.shape[1], out.shape[0], out.shape[1] * 4, QImage.Format_ARGB32_Premultiplied).copy()


def suggest_colours(spec: DecoSpec, max_k=4, min_share=0.04):
    """Number of distinct colours of the artwork (1..max_k) so that a multi-colour logo is exported with one filament per colour without any setting.
    Colours are grouped on a coarse grid; groups under min_share of the visible pixels (anti-aliasing, noise) are ignored. 1 when it cannot be read."""
    try:
        im = _artwork_color_image(spec)
        arr = np.frombuffer(im.constBits(), np.uint8).reshape(im.height(), im.bytesPerLine() // 4, 4)[:, :im.width(), :].astype(float)
    except Exception: return 1
    a = arr[..., 3]; vis = a > 127
    if not vis.any(): return 1
    rgb = arr[..., :3][vis] * 255.0 / np.maximum(a[vis], 1)[:, None]
    q = (rgb // 48).astype(int); keys, counts = np.unique(q[:, 0] * 100 + q[:, 1] * 10 + q[:, 2], return_counts=True)
    return int(max(1, min(max_k, (counts >= min_share * len(rgb)).sum())))


def _kmeans(X, k, iters=15, seed=0):
    rng = np.random.default_rng(seed); n = len(X)
    sub = X if n <= 20000 else X[rng.choice(n, 20000, replace=False)]
    cent = [sub[rng.integers(len(sub))]]
    for _ in range(1, k):
        d = np.min(((sub[:, None, :] - np.array(cent)[None]) ** 2).sum(2), axis=1)
        if d.sum() == 0: break
        cent.append(sub[rng.choice(len(sub), p=d / d.sum())])
    cent = np.array(cent, float)
    for _ in range(iters):
        lab = ((X[:, None, :] - cent[None]) ** 2).sum(2).argmin(1)
        for j in range(len(cent)):
            if (lab == j).any(): cent[j] = X[lab == j].mean(0)
    return ((X[:, None, :] - cent[None]) ** 2).sum(2).argmin(1), cent


def render_color_layers(spec: DecoSpec, hm: "HeightMap"):
    """[(hex, rgb, cell_mask)] sorted by size; masks are disjoint; their union is the artwork (cells indexed [i(u), j(v)])."""
    _ensure_qt()
    from PySide6.QtGui import QImage, QPainter
    nu, nv = hm.shape; ncu, ncv = nu - 1, nv - 1
    art = _artwork_color_image(spec, int(spec.size_mm / hm.res))
    img = QImage(ncu, ncv, QImage.Format_ARGB32_Premultiplied); img.fill(0)
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.translate((spec.u - hm.u0) / hm.res, (hm.v0 + ncv * hm.res - spec.v) / hm.res); p.rotate(-spec.rotation_deg)
    k = (spec.size_mm / hm.res) / max(art.width(), art.height()); p.scale(k, k); p.translate(-art.width() / 2, -art.height() / 2)
    p.drawImage(0, 0, art); p.end()
    arr = np.frombuffer(img.constBits(), np.uint8).reshape(ncv, img.bytesPerLine() // 4, 4)[:, :ncu, :].astype(float)
    a = arr[..., 3]; rgb = (arr[..., 2::-1] * 255.0 / np.maximum(a, 1)[..., None])        # RGB
    cont = a > 127
    if not cont.any(): raise DecoError("artwork outside the placement area")
    n = max(1, min(4, int(spec.ncolors)))
    X = rgb[cont]
    if n == 1:
        lab, cent = np.zeros(len(X), int), X.mean(0, keepdims=True)
        drop = np.zeros(1, bool)
    else:
        # one extra cluster absorbs the near-white / anti-aliased light pixels, which are EMPTY rather than a colour
        lab, cent = _kmeans(X, n + 1 if spec.white_is_empty else n)
        mx, mn = cent.max(1), cent.min(1)
        lum = cent @ np.array([0.299, 0.587, 0.114]); sat = (mx - mn) / np.maximum(mx, 1)
        drop = (lum > 150) & (sat < 0.35) if spec.white_is_empty else np.zeros(len(cent), bool)
        if drop.all(): drop[np.argmin(lum)] = False
    counts = np.bincount(lab, minlength=len(cent))
    keep = [j for j in np.argsort(-counts) if not drop[j] and counts[j] >= max(30, 0.005 * len(X))][:n] or [int(np.argmax(np.where(drop, -1, counts)))]
    d2 = ((X[:, None, :] - cent[keep][None]) ** 2).sum(2)
    newlab = d2.argmin(1)
    gone = drop[lab]                                             # pixels of the white/blend cluster stay empty
    newlab = np.where(gone, -1, newlab)
    L = np.full(cont.shape, -1, int); L[cont] = newlab
    layers = []
    for jj, j in enumerate(keep):
        m = (L == jj)[::-1, :].T.copy()
        if m.any():
            c = tuple(int(round(x)) for x in cent[j]); layers.append(("#%02X%02X%02X" % c, c, m))
    layers = _merge_fringes(layers, hm.res)
    layers.sort(key=lambda t: -int(t[2].sum()))
    return layers


def _merge_fringes(layers, res):
    """Anti-aliasing turns the border of a dark shape into 1-2 cell thin lines of a lighter intermediate colour (dotted outline in another filament). Such thin cells touching a DARKER layer join that layer: nothing is deleted, free-standing thin strokes stay as they are."""
    if len(layers) < 2: return layers
    lum = [0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for _, c, _ in layers]; masks = [m.copy() for _, _, m in layers]
    near = [_dilate_mm(m, 2 * res, res) for m in masks]
    for i, m in enumerate(layers):
        mi = masks[i]; eroded = ~_dilate_mm(~mi, MIN_FEATURE_MM / 2, res); thin = mi & ~_dilate_mm(eroded, MIN_FEATURE_MM / 2, res)
        for j in sorted((j for j in range(len(layers)) if lum[j] < lum[i] - 20), key=lambda j: lum[j]):
            mv = thin & near[j] & masks[i]
            if mv.any(): masks[i] = masks[i] & ~mv; masks[j] = masks[j] | mv; thin = thin & ~mv
    return [(h, c, masks[k]) for k, (h, c, _) in enumerate(layers) if masks[k].any()]


def camo_valid_mask(spec: DecoSpec, hm: "HeightMap", protected=None, zones=()):
    """Cells a camouflage may cover: on the part, off the automatic protected zones and the drawn ones, gentle slope, 1 mm from any edge."""
    ok = ~np.isnan(hm.H); cell_ok = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
    H = np.where(ok, hm.H, 0.0); gu, gv = np.gradient(H, hm.res); slope = np.degrees(np.arctan(np.hypot(gu, gv)))[:-1, :-1]
    bad = ~cell_ok | (slope > SLOPE_WARN_DEG)
    if protected is not None: bad = bad | protected
    ii, jj = np.mgrid[0:cell_ok.shape[0], 0:cell_ok.shape[1]]; cu = hm.u0 + (ii + 0.5) * hm.res; cv = hm.v0 + (jj + 0.5) * hm.res
    for a, b, c, d in zones: bad = bad | ((cu >= min(a, c)) & (cu <= max(a, c)) & (cv >= min(b, d)) & (cv <= max(b, d)))
    return cell_ok & ~_dilate_mm(bad, CAMO_EDGE_MM, hm.res)


def render_camo(spec: DecoSpec, hm: "HeightMap", protected=None, zones=()):
    from . import camo
    if spec.mode not in ("relief", "inlay"): raise DecoError("Camouflage : choisir Relief ou Incrustation (la gravure sur toute la pièce n'est pas proposée).")
    if spec.camo_style not in camo.PALETTES: raise DecoError(f"unknown camouflage {spec.camo_style}")
    k = max(2, int(round(MIN_FEATURE_MM / hm.res)))
    clean = lambda m: _dilate(_erode(m, k), k)                                    # opening: no sliver narrower than the nozzle can print
    ly = camo.layers(spec.camo_style, spec.camo_seed, max(8.0, spec.camo_scale_mm), camo_valid_mask(spec, hm, protected, zones), hm.u0, hm.v0, hm.res, clean)
    if not ly: raise DecoError("Camouflage : aucune surface décorable sur cette face (zones protégées, pentes ou bords).")
    union = np.zeros_like(ly[0][2])
    for _, _, m in ly: union |= m
    return union, ly


THICKEN_MM = 0.3           # each side (rounded to whole grid cells): a 0.4 mm stroke becomes ~1 mm


def thicken_thin(m, res, taken=None, min_mm=None, grow_mm=THICKEN_MM):
    """m with its strokes thinner than min_mm (default MIN_FEATURE_MM) widened by grow_mm on each side; never into cells of `taken` (other colours)."""
    min_mm = MIN_FEATURE_MM if min_mm is None else min_mm
    half = min_mm / 2
    eroded = ~_dilate_mm(~m, half, res); opened = _dilate_mm(eroded, half, res)
    thin = m & ~opened
    if not thin.any(): return m
    grown = _dilate_mm(thin, max(grow_mm, res), res)
    if taken is not None: grown &= ~taken
    return m | grown


MOTIF_COLOURS = ("#0B2F4B", "#DC2823", "#285591", "#F2B705")      # labels of single-colour motifs when several are combined (the filament is chosen in the slicer)
MAX_PIECES = 4


def _spec_dict(spec):
    from dataclasses import asdict
    return asdict(spec)


def spec_empty(s):
    return (s.kind == "text" and not s.text.strip()) or (s.kind in ("svg", "image") and not s.path)


def render_spec_masks(spec: DecoSpec, hm: "HeightMap", protected=None, zones=()):
    """(union_mask, layers|None) of the spec and of its extra motifs. A later motif wins where two overlap. Several motifs = one piece per colour (relief/inlay)."""
    from dataclasses import replace
    parts = [replace(x, extra=()) for x in (spec,) + tuple(spec.extra) if not spec_empty(x)]
    if not spec.extra: return _render_one(spec, hm, protected, zones)
    if not parts: raise DecoError("empty text")
    if len(parts) == 1: return _render_one(parts[0], hm, protected, zones)       # the other motifs are still empty
    if any(x.kind == "camo" for x in parts): raise DecoError("Camouflage : un seul motif possible (retirer les autres motifs).")
    rendered = [_render_one(x, hm, protected, zones) for x in parts]
    if spec.mode == "engrave":
        union = rendered[0][0].copy()
        for m, _ in rendered[1:]: union |= m
        return union, None
    groups = []; k = 0                                                     # [(hex, rgb, mask)] per motif, in order
    for m, ly in rendered:
        if ly: groups.append(list(ly))
        else:
            h = MOTIF_COLOURS[k % len(MOTIF_COLOURS)]; k += 1; groups.append([(h, tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)), m)])
    later = np.zeros_like(rendered[0][0]); out = []
    for g in reversed(groups):                                             # later motifs take priority over earlier ones
        cur = np.zeros_like(later)
        for h, c, m in g:
            m2 = m & ~later
            if m2.any(): out.append((h, c, m2))
            cur |= m
        later |= cur
    out.reverse()
    if not out: raise DecoError("artwork outside the placement area")
    if len(out) > MAX_PIECES: raise DecoError(f"Trop de couleurs : {len(out)} pièces demandées pour {MAX_PIECES} filaments au maximum (réduire le nombre de couleurs ou de motifs).")
    union = np.zeros_like(out[0][2])
    for _, _, m in out: union |= m
    return union, out


def _forbidden_cells(hm, protected, zones, shape):
    """Cells the motif must not enter (automatic protection, drawn zones): thickening never grows into them."""
    bad = np.zeros(shape, bool) if protected is None else protected.copy()
    ii, jj = np.mgrid[0:shape[0], 0:shape[1]]; cu = hm.u0 + (ii + 0.5) * hm.res; cv = hm.v0 + (jj + 0.5) * hm.res
    for a, b, c, d in zones: bad |= (cu >= min(a, c)) & (cu <= max(a, c)) & (cv >= min(b, d)) & (cv <= max(b, d))
    return bad


def _render_one(spec: DecoSpec, hm: "HeightMap", protected=None, zones=()):
    """(union_mask, layers|None). Colour separation only for svg/image with ncolors > 1 and mode relief/inlay; camouflage always has layers."""
    if spec.kind == "camo": return render_camo(spec, hm, protected, zones)
    if spec.kind in ("svg", "image") and spec.ncolors > 1 and spec.mode in ("relief", "inlay"):
        layers = render_color_layers(spec, hm)
        if spec.thicken_thin:
            masks = [m for _, _, m in layers]; new = []; forbid = _forbidden_cells(hm, protected, zones, masks[0].shape)
            for i, (h, c, m) in enumerate(layers):
                others = forbid.copy()
                for j, o in enumerate(masks):
                    if j != i: others |= o
                new.append((h, c, thicken_thin(m, hm.res, others)))
                masks[i] = new[-1][2]
            layers = new
        union = np.zeros_like(layers[0][2])
        for _, _, m in layers: union |= m
        return union, layers
    m = render_mask(spec, hm)
    return (thicken_thin(m, hm.res, _forbidden_cells(hm, protected, zones, m.shape)) if (spec.thicken_thin and spec.kind in ("svg", "image")) else m), None


# ---------------------------------------------------------------- automatic protected zones
PROTECT_STEEP_DEG, PROTECT_STEEP_MARGIN_MM = 55.0, 1.0


def _dil(m, cross):
    out = m.copy()
    out[1:, :] |= m[:-1, :]; out[:-1, :] |= m[1:, :]; out[:, 1:] |= m[:, :-1]; out[:, :-1] |= m[:, 1:]
    if not cross:
        out[1:, 1:] |= m[:-1, :-1]; out[:-1, :-1] |= m[1:, 1:]; out[1:, :-1] |= m[:-1, 1:]; out[:-1, 1:] |= m[1:, :-1]
    return out


def _dilate_mm(m, mm, res):
    for i in range(int(round(mm / res))): m = _dil(m, i % 2 == 0)       # alternating cross/square ~ round
    return m


def auto_protected_mask(hm: "HeightMap", margin_mm=2.0):
    """Cells (nu-1, nv-1) that must not be decorated: through-holes/slots + margin, steep rims + 1 mm.
    Holes = cells without surface that are NOT connected to the outside of the part. This is a geometric aid only:
    it cannot know which other zones are functional."""
    ok = ~np.isnan(hm.H); cell_ok = ok[:-1, :-1] & ok[1:, :-1] & ok[:-1, 1:] & ok[1:, 1:]
    empty = ~cell_ok
    ext = np.zeros_like(empty); ext[0, :] = empty[0, :]; ext[-1, :] = empty[-1, :]; ext[:, 0] = empty[:, 0]; ext[:, -1] = empty[:, -1]
    while True:
        new = ext | (_dil(ext, True) & empty)
        if (new == ext).all(): break
        ext = new
    holes = empty & ~ext
    prot = _dilate_mm(holes, margin_mm, hm.res) if margin_mm > 0 else holes.copy()
    H = np.where(ok, hm.H, 0.0); gu, gv = np.gradient(H, hm.res)
    steep = (np.degrees(np.arctan(np.hypot(gu, gv)))[:-1, :-1] > PROTECT_STEEP_DEG) & cell_ok
    if margin_mm > 0: prot |= _dilate_mm(steep, PROTECT_STEEP_MARGIN_MM, hm.res)
    return prot


# ---------------------------------------------------------------- checks
CAMO_EDGE_MM = 1.0       # camouflage stays this far from edges, holes and protected zones
MIN_FEATURE_MM = 0.8      # 2 x a 0.4 mm nozzle: heuristic, not an e-NABLE rule


def _erode(m, k):
    out = m.copy()
    for di in range(k):
        for dj in range(k):
            sh = np.zeros_like(m); sh[: m.shape[0] - di, : m.shape[1] - dj] = m[di:, dj:]; out &= sh
    return out


def _dilate(m, k):
    out = np.zeros_like(m)
    for di in range(k):
        for dj in range(k):
            out[di:, dj:] |= m[: m.shape[0] - di, : m.shape[1] - dj]
    return out


def thin_feature_report(mask, res, min_mm=MIN_FEATURE_MM):
    """Share of the decoration narrower than min_mm (opening of the mask) and of the GAPS narrower than min_mm (closing)."""
    k = max(2, int(round(min_mm / res)))
    opened = _dilate(_erode(mask, k), k)
    thin = float((mask & ~opened).sum()) / max(1, int(mask.sum()))
    pad = np.pad(mask, k)
    closed = _erode(_dilate(pad, k), k)[k:-k, k:-k] if k else mask
    gaps = float((closed & ~mask).sum()) / max(1, int(mask.sum()))
    return {"thin_fraction": thin, "narrow_gap_fraction": gaps, "min_mm": min_mm}
def check_placement(hm: HeightMap, mask, zones=(), depth_mm=0.6, mode="relief", protected=None):
    """Returns (errors, warnings, info). Errors forbid generation; nothing is ever clamped silently."""
    errors, warns = [], []
    nu, nv = hm.shape
    if mask is None or not mask.any(): return ["Décoration vide ou hors de la zone affichée."], [], {}
    corner_ok = ~np.isnan(hm.H)
    cell_ok = corner_ok[:-1, :-1] & corner_ok[1:, :-1] & corner_ok[:-1, 1:] & corner_ok[1:, 1:]
    off = int((mask & ~cell_ok).sum())
    if off: errors.append(f"{off} cellules de la décoration dépassent de la pièce ou survolent le vide : réduire/déplacer le motif.")
    if protected is not None and (mask & protected).any():
        errors.append(f"La décoration entre dans la zone protégée automatiquement (trou/fente + marge de sécurité, bord pentu) : {int((mask & protected).sum())} cellules.")
    cap = {"relief": MAX_RELIEF_MM, "engrave": MAX_ENGRAVE_MM, "inlay": MAX_INLAY_MM}[mode]
    if depth_mm < MIN_DEPTH_MM or depth_mm > cap:
        errors.append(f"Profondeur {depth_mm:g} mm hors limites logicielles {MIN_DEPTH_MM}-{cap} mm ({mode}) — limites heuristiques, non issues d'e-NABLE.")
    if mode in ("engrave", "inlay") and depth_mm > ENGRAVE_MAX_FRACTION_OF_THICKNESS * hm.thickness_w:
        errors.append(f"{'Gravure' if mode == 'engrave' else 'Incrustation'} {depth_mm:g} mm > {ENGRAVE_MAX_FRACTION_OF_THICKNESS*100:.0f} % de l'épaisseur de la pièce selon cet axe ({hm.thickness_w:.1f} mm).")
    # exclusion zones (u0,v0,u1,v1) in mm
    ii, jj = np.nonzero(mask)
    cu = hm.u0 + (ii + 0.5) * hm.res; cv = hm.v0 + (jj + 0.5) * hm.res
    for k, (a, b, c, d) in enumerate(zones):
        hit = int(((cu >= min(a, c)) & (cu <= max(a, c)) & (cv >= min(b, d)) & (cv <= max(b, d))).sum())
        if hit: errors.append(f"La décoration entre dans la zone interdite n°{k + 1} ({hit} cellules).")
    H = np.where(corner_ok, hm.H, 0.0)
    gu, gv = np.gradient(H, hm.res)
    slope = np.degrees(np.arctan(np.hypot(gu, gv)))[:-1, :-1]
    smax = float(slope[mask & cell_ok].max()) if (mask & cell_ok).any() else 0.0
    if smax > SLOPE_REFUSE_DEG: errors.append(f"Pente locale {smax:.0f}° > {SLOPE_REFUSE_DEG:.0f}° sous le motif (bord/paroi) : le motif serait déformé.")
    elif smax > SLOPE_WARN_DEG: warns.append(f"Pente locale jusqu'à {smax:.0f}° sous le motif : rendu déformé possible.")
    tf = thin_feature_report(mask, hm.res)
    if tf["thin_fraction"] > 0.02:
        warns.append(f"{tf['thin_fraction']*100:.0f} % du motif est plus fin que {MIN_FEATURE_MM:g} mm (buse 0,4) : traits fins possiblement non imprimés ; agrandir le motif ou le simplifier.")
    if tf["narrow_gap_fraction"] > 0.02:
        warns.append(f"Des fentes/espaces plus étroits que {MIN_FEATURE_MM:g} mm (≈ {tf['narrow_gap_fraction']*100:.0f} % de la surface du motif) risquent de se refermer à l'impression.")
    warns.append("Zones fonctionnelles non détectées automatiquement : vérifier à la main qu'aucune articulation, trou de broche, passage de câble ou surface de contact n'est touché.")
    return errors, warns, {"cells": int(mask.sum()), "max_slope_deg": smax}


# ---------------------------------------------------------------- solid
def build_solid(hm: HeightMap, mask, top_off, bot_off):
    """Closed shells following the surface for the cells in mask. Offsets are along w, relative to the surface."""
    S = _fix_checkerboards(mask)
    nu, nv = hm.shape
    iu = hm.u0 + np.arange(nu) * hm.res; iv = hm.v0 + np.arange(nv) * hm.res
    def node(i, j, off): return (iu[i], iv[j], hm.H[i, j] + off)
    P = np.pad(S, 1)                       # neighbour lookup with empty border
    tris = []
    ci, cj = np.nonzero(S)
    for i, j in zip(ci, cj):
        t = [node(i, j, top_off), node(i + 1, j, top_off), node(i + 1, j + 1, top_off), node(i, j + 1, top_off)]
        b = [node(i, j, bot_off), node(i + 1, j, bot_off), node(i + 1, j + 1, bot_off), node(i, j + 1, bot_off)]
        tris += [(t[0], t[1], t[2]), (t[0], t[2], t[3]), (b[0], b[2], b[1]), (b[0], b[3], b[2])]
        # walls toward empty neighbours: (di,dj, tri pair)
        if not P[i, j + 1]:       # -u neighbour (i-1)
            tris += [(t[0], t[3], b[3]), (t[0], b[3], b[0])]
        if not P[i + 2, j + 1]:   # +u
            tris += [(t[1], b[2], t[2]), (t[1], b[1], b[2])]
        if not P[i + 1, j]:       # -v
            tris += [(t[0], b[1], t[1]), (t[0], b[0], b[1])]
        if not P[i + 1, j + 2]:   # +v
            tris += [(t[3], t[2], b[2]), (t[3], b[2], b[3])]
    return np.array(tris, float).reshape(-1, 3, 3) if tris else np.zeros((0, 3, 3))


@dataclass
class DecoResult:
    triangles: list                 # final part (original + decoration / engraved)
    deco_triangles: list
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    info: dict = field(default_factory=dict)
    preview_triangles: list = field(default_factory=list)   # what the 3D preview shows (inlay: part + thin top skin)
    preview_highlight: int = 0                                # number of trailing preview triangles to colour
    preview_colors: list = field(default_factory=list)       # RGB per highlighted preview triangle (colour separation)
    layers: list = field(default_factory=list)               # [{'hex','rgb','cells','triangles'}] one piece per colour


def apply_decoration(part_path, spec: DecoSpec, zones=(), hm: HeightMap = None, res=None) -> DecoResult:
    tris = read_stl(part_path)
    if spec.mirror_x: tris = mirror_tris(tris)
    if hm is None or hm.axis != spec.axis:                      # a given height map (and its resolution) is authoritative
        hm = build_heightmap(tris, spec.axis, res or spec.res_mm)
    if spec.mode == "inlay" and not INLAY_OFFSET_RANGE[0] <= spec.inlay_offset_mm <= INLAY_OFFSET_RANGE[1]:
        raise DecoError(f"Dépassement de l'incrustation hors plage ({INLAY_OFFSET_RANGE[0]} à {INLAY_OFFSET_RANGE[1]} mm) : {spec.inlay_offset_mm} mm refusé.")
    protected = auto_protected_mask(hm, spec.protect_margin_mm) if spec.protect_margin_mm > 0 else None
    mask, color_layers = render_spec_masks(spec, hm, protected, zones)
    errors, warns, info = check_placement(hm, mask, zones, spec.depth_mm, spec.mode, protected)
    if spec.mode == "engrave" and not is_watertight(tris):
        errors.append("Gravure impossible : cette pièce n'est pas étanche/manifold (soustraction non fiable). Utiliser le relief.")
    if errors: return DecoResult(tris, [], errors, warns, info)
    if color_layers and spec.mode in ("inlay", "relief"):
        top, bot = (spec.inlay_offset_mm, -spec.depth_mm) if spec.mode == "inlay" else (spec.depth_mm, -EMBED_MM)
        layers, deco, skin, skin_col = [], [], [], []
        for hexc, rgbc, m in color_layers:
            t = [tuple(map(tuple, from_uvw(x, spec.axis))) for x in build_solid(hm, m, top, bot)]
            layers.append({"hex": hexc, "rgb": rgbc, "cells": int(m.sum()), "triangles": t}); deco += t
            if spec.mode == "inlay":
                sk = [tuple(map(tuple, from_uvw(x, spec.axis))) for x in build_solid(hm, m, 0.06, 0.04)]
                skin += sk; skin_col += [rgbc] * len(sk)
        info["solid_triangles"] = len(deco); info["layers"] = [(l["hex"], l["cells"]) for l in layers]
        if spec.mode == "inlay":
            warns.append("Incrustation en couleurs : charger la pièce d'origine puis CHAQUE pièce de couleur comme pièces d'un même objet ; un filament par couleur ; blanc = reste en filament de la base (non vérifié à l'impression).")
            return DecoResult(list(tris), deco, [], warns, info, list(tris) + skin, len(skin), skin_col, layers)
        warns.append("Relief en couleurs : une pièce par couleur, à charger avec la pièce d'origine ; un filament par couleur.")
        return DecoResult(list(tris) + deco, deco, [], warns, info, [], len(deco), [c for l in layers for c in [l["rgb"]] * len(l["triangles"])], layers)
    if spec.mode == "inlay":
        solid = build_solid(hm, mask, spec.inlay_offset_mm, -spec.depth_mm)
        deco = [tuple(map(tuple, from_uvw(t, spec.axis))) for t in solid]
        skin = [tuple(map(tuple, from_uvw(t, spec.axis))) for t in build_solid(hm, mask, 0.06, 0.04)]   # preview only
        warns.append("Incrustation : à charger avec la pièce d'origine comme deux PIÈCES D'UN MÊME OBJET ; affecter un autre filament à la pièce incrustation. Affleurant à ~0,03 mm près (non vérifié à l'impression)." if spec.inlay_offset_mm <= 0 else f"Incrustation : à charger avec la pièce d'origine comme deux PIÈCES D'UN MÊME OBJET ; affecter un autre filament à la pièce incrustation. Dépasse de {spec.inlay_offset_mm:g} mm au-dessus de la surface (non vérifié à l'impression).")
        info["solid_triangles"] = len(deco)
        return DecoResult(list(tris), deco, [], warns, info, list(tris) + skin, len(skin))
    if spec.mode == "relief":
        solid = build_solid(hm, mask, spec.depth_mm, -EMBED_MM)
        deco = [tuple(map(tuple, from_uvw(t, spec.axis))) for t in solid]
        final = list(tris) + deco
    else:
        solid = build_solid(hm, mask, 0.5, -spec.depth_mm)
        deco = [tuple(map(tuple, from_uvw(t, spec.axis))) for t in solid]
        with tempfile.TemporaryDirectory() as d:
            cutter = Path(d) / "c.stl"; write_stl(cutter, deco)
            scad = Path(d) / "e.scad"
            src_stl = Path(part_path).resolve()
            if spec.mirror_x: src_stl = Path(d) / "m.stl"; write_stl(src_stl, tris)                 # engrave the mirrored part, not the file on disk
            scad.write_text(f'difference(){{import("{src_stl.as_posix()}");import("{cutter.as_posix()}");}}\n')
            final = read_stl(openscad.render(scad, Path(d) / "o.stl", {}))
    info["solid_triangles"] = len(deco)
    return DecoResult(final, deco, [], warns, info)


# ---------------------------------------------------------------- export
def export_result(result: DecoResult, part_path, spec: DecoSpec, out_dir, zones=(), scale_percent=None, extra=None):
    """Writes <stem>_EXPERIMENTAL_deco.stl + sidecar JSON + ATTRIBUTION.txt in out_dir (never beside the original)."""
    if result.errors: raise DecoError("; ".join(result.errors))
    src = Path(part_path).resolve(); out = Path(out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    if out == src.parent: raise DecoError("Le dossier d'export ne peut pas être celui de l'original.")
    tris = result.triangles
    if scale_percent not in (None, 100, 100.0) and spec.mode != "inlay":
        k = scale_percent / 100.0; tris = [tuple(tuple(c * k for c in p) for p in t) for t in tris]
    if result.layers:
        base = f"{src.stem[:40]}_1_base_unmodified.stl"
        k = 1.0 if scale_percent in (None, 100, 100.0) else scale_percent / 100.0
        sc = lambda T: [tuple(tuple(c * k for c in p) for p in t) for t in T] if k != 1.0 else T
        write_stl(out / base, sc(result.triangles if spec.mode == "inlay" else (mirror_tris(read_stl(src)) if spec.mirror_x else list(read_stl(src)))))
        piece_files = []
        for n, L in enumerate(result.layers, start=2):
            fn = f"{src.stem[:40]}_{n}_EXPERIMENTAL_{'incrustation' if spec.mode == 'inlay' else 'relief'}_{L['hex'][1:]}.stl"
            write_stl(out / fn, sc(L["triangles"])); piece_files.append({"file": fn, "color": L["hex"], "cells": L["cells"], "suggested_filament": n - 1})
        name = piece_files[0]["file"]; tris = result.layers[0]["triangles"]
    elif spec.mode == "inlay" and result.deco_triangles:
        name = f"{src.stem[:40]}_2_EXPERIMENTAL_incrustation.stl"        # inlay volume only; sorts AFTER the base
        base = f"{src.stem[:40]}_1_base_unmodified.stl"
        tris, btris = result.deco_triangles, result.triangles            # base = identical to the original geometry
        if scale_percent not in (None, 100, 100.0):
            k = scale_percent / 100.0
            tris = [tuple(tuple(c * k for c in p) for p in t) for t in tris]
            btris = [tuple(tuple(c * k for c in p) for p in t) for t in btris]
        write_stl(out / base, btris)
    else:
        name = f"{src.stem[:40]}_" + ("EXPERIMENTAL_deco" if result.deco_triangles else "copy_unmodified") + ".stl"
    write_stl(out / name, tris)
    bambu_name, guide_name, pieces_info = None, None, []
    if spec.mode in ("inlay", "relief") and result.deco_triangles:
        base_tris = list(result.triangles) if spec.mode == "inlay" else (mirror_tris(read_stl(src)) if spec.mirror_x else list(read_stl(src)))
        k = 1.0 if scale_percent in (None, 100, 100.0) else scale_percent / 100.0
        sc = (lambda T: [tuple(tuple(c * k for c in p) for p in t) for t in T]) if k != 1.0 else (lambda T: T)
        parts = [{"name": "Base (pièce d'origine, inchangée)", "triangles": sc(base_tris), "extruder": 1}]
        if result.layers:
            for n, L in enumerate(result.layers, start=2):
                parts.append({"name": f"Couleur {n - 1} {L['hex']}", "triangles": sc(L["triangles"]), "extruder": n})
                pieces_info.append((n, L["hex"], L["cells"]))
        else:
            parts.append({"name": "Décoration", "triangles": sc(result.deco_triangles), "extruder": 2}); pieces_info.append((2, None, None))
        bambu_name = f"{src.stem[:40]}_Bambu_pret.3mf"
        cols = ((["#FFFFFF"] + [L["hex"] for L in result.layers]) if result.layers else None) if bambu3mf.WITH_FILAMENT_CONFIG else None
        write_bambu_3mf(out / bambu_name, parts, object_name=src.stem[:40], filament_colours=cols)
        guide_name = f"{src.stem[:40]}_LISEZ-MOI_Bambu.txt"
        lines = ["CustomLab — pièce décorée EXPÉRIMENTALE : mode d'emploi pour Bambu Studio", "",
                 f"1. Double-cliquez sur {bambu_name} (ou Fichier > Ouvrir dans Bambu Studio).",
                 "   Il contient la pièce d'origine et la décoration comme PIÈCES d'un même objet, avec les filaments déjà assignés.", "",
                 "2. Vérifiez l'onglet « Objets » : filament par pièce :", f"   - Base (pièce d'origine) -> filament 1  (couleur du fond, y compris les parties blanches/vides du motif)"]
        for n, h, cells in pieces_info:
            lines.append(f"   - {'Couleur ' + str(n - 1) + ' ' + h if h else 'Décoration'} -> filament {n}" + (f"  ({cells} cellules)" if cells else ""))
        if len(pieces_info) + 1 > 4: lines.append("   Attention : plus de 4 filaments — ajoutez des filaments au projet dans Bambu Studio avant de trancher.")
        lines += ["", "3. Associez chaque filament du projet à la bonne bobine/couleur (AMS), puis tranchez.",
                  "   Chaque changement de couleur purge de la matière : prévoyez du temps et du déchet en plus.", "",
                  "Les autres fichiers .stl du dossier sont les mêmes pièces séparées (pour un autre trancheur).", "",
                  DISCLAIMER, "Aucune impression ni validation physique n'a été faite pour cette pièce."]
        (out / guide_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    lic = read_license_info(src)
    side = {"generated": datetime.now().isoformat(timespec="seconds"), "status": "EXPERIMENTAL",
            "disclaimer": DISCLAIMER, "source_file": str(src), "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
            "source_license": lic, "spec": _spec_dict(spec), "exclusion_zones_mm": [list(z) for z in zones],
            "scale_percent_applied": scale_percent, "triangles": len(tris), "warnings": result.warnings,
            "color_pieces": piece_files if result.layers else None, "bambu_3mf": bambu_name, "guide": guide_name,
            "how_to_use": ("Charger <1_base_unmodified> puis <2_incrustation> ensemble comme pièces d'un même objet ; l'incrustation doit être la DERNIÈRE pièce de la liste (hypothèse non vérifiée : la dernière pièce l'emporte dans le volume commun) et avoir un filament différent." if spec.mode == "inlay" else None), **(extra or {})}
    (out / (Path(name).stem + ".json")).write_text(json.dumps(side, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["Pièce dérivée EXPÉRIMENTALE — voir le fichier JSON associé.", DISCLAIMER, ""]
    if lic.get("known"):
        lines += [f"Source : {lic['title']} par {lic['author']}", f"Licence de la source : {lic['license']} {lic.get('license_url') or ''}",
                  f"Dérivé de : {lic.get('derived_from')}"]
        if lic["non_commercial"]: lines.append("USAGE NON COMMERCIAL UNIQUEMENT. Ne pas redistribuer sans respecter la licence (attribution).")
        if lic.get("share_alike"): lines.append("PARTAGE DANS LES MÊMES CONDITIONS : cette pièce dérivée ne peut être partagée que sous la même licence que la source.")
    else:
        lines.append("Provenance/licence du fichier source INCONNUES : ne pas redistribuer.")
    lines.append("Le motif ajouté (texte/image) relève de la responsabilité de l'utilisateur (droits des tiers).")
    (out / (Path(name).stem + "_ATTRIBUTION.txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / name
