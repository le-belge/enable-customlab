"""Procedural camouflage: organic patches in 3 colours over the usable surface of a part (our own pattern, no third-party artwork).

The pattern is a function of the world position (u, v in mm) and a seed, so the same seed gives the same patches at any resolution.
Palettes are STYLE presets ("inspired by"), not an official reproduction of any army's pattern. Layer 1..3 are the colours printed in
the part; the base colour is the part's own filament (filament 1).
"""
import numpy as np

PALETTES = {
    "fr": {"label": {"fr": "Français (style Centre Europe)", "en": "French (Central Europe style)"}, "base": ("#C2B280", {"fr": "sable", "en": "sand"}),
           "layers": [("#5B6236", 0.32), ("#6B4A2E", 0.24), ("#1E1E1C", 0.11)]},          # olive green, earth brown, black (share of the usable surface)
    "winter": {"label": {"fr": "Hiver (neige)", "en": "Winter (snow)"}, "base": ("#F2F4F5", {"fr": "blanc", "en": "white"}),
               "layers": [("#C5CBD0", 0.30), ("#8D969E", 0.16), ("#4B5259", 0.06)]},       # light grey, steel grey, charcoal
}


def _hash(ix, iy, seed):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ ((int(seed) * 83492791) & 0xFFFFFFFF)
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF) / 65535.0


def _value_noise(U, V, scale, seed):
    x, y = U / scale, V / scale; ix, iy = np.floor(x), np.floor(y); fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed); c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return (a * (1 - sx) + b * sx) * (1 - sy) + (c * (1 - sx) + d * sx) * sy


def _field(U, V, scale, seed):
    """Blobby noise with a little finer detail and a gentle domain warp, so the edges are ragged rather than round."""
    wu = U + 0.35 * scale * (_value_noise(U, V, scale * 1.7, seed + 90) - 0.5)
    wv = V + 0.35 * scale * (_value_noise(U, V, scale * 1.7, seed + 91) - 0.5)
    return _value_noise(wu, wv, scale, seed) + 0.5 * _value_noise(wu, wv, scale / 2.3, seed + 1) + 0.25 * _value_noise(wu, wv, scale / 5.0, seed + 2)


def layers(style, seed, scale_mm, valid, u0, v0, res, clean):
    """[(hex, rgb, mask)] for the cells of `valid` (shape (nu-1, nv-1), [i(u), j(v)]); `clean(mask)` removes slivers (opening)."""
    pal = PALETTES[style]; ii, jj = np.nonzero(valid)
    if not len(ii): return []
    U, V = u0 + (ii + 0.5) * res, v0 + (jj + 0.5) * res; n = len(ii); free = np.ones(n, bool); out = []
    for k, (hexc, share) in enumerate(pal["layers"]):
        f = _field(U, V, float(scale_mm) * (1.0 - 0.12 * k), int(seed) * 13 + k)
        cand = np.nonzero(free)[0]
        if not len(cand): break
        q = float(np.clip(1.0 - share * n / len(cand), 0.0, 0.999)); thr = np.quantile(f[cand], q)
        take = free & (f >= thr); free &= ~take
        m = np.zeros(valid.shape, bool); m[ii[take], jj[take]] = True; m = clean(m)
        if m.any(): out.append((hexc, tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5)), m))
    out.sort(key=lambda t: -int(t[2].sum())); return out
