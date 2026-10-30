"""3D viewer: numpy z-buffer rasteriser (no OpenGL dependency) with orbit/zoom.

Every pixel shows the nearest triangle, so fine meshes (700k triangles) render without holes. Small triangles are rasterised in
bulk (vectorised), large ones one by one. Supersampling is used for light meshes; while orbiting, big meshes are decimated.
"""
import numpy as np
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer

BG = np.array([244, 245, 247], np.uint8)
HEAVY = 200000          # front-facing triangles above which supersampling is disabled
DRAG_MAX = 60000        # triangles rendered while orbiting


def rasterise(a, b, c, tid, W, H, chunk=120000):
    """a, b, c: (N,3) screen-space vertices (x, y in pixels, z = depth, larger = nearer). Returns (id_buffer int32, z_buffer)."""
    zbuf = np.full(W * H, -np.inf); idbuf = np.full(W * H, -1, np.int32); eps = 1e-9
    minx = np.minimum(np.minimum(a[:, 0], b[:, 0]), c[:, 0]); maxx = np.maximum(np.maximum(a[:, 0], b[:, 0]), c[:, 0])
    miny = np.minimum(np.minimum(a[:, 1], b[:, 1]), c[:, 1]); maxy = np.maximum(np.maximum(a[:, 1], b[:, 1]), c[:, 1])
    d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    vis = (np.abs(d) > 1e-12) & (maxx >= 0) & (minx <= W) & (maxy >= 0) & (miny <= H)
    small = vis & ((maxx - minx) <= 1.9) & ((maxy - miny) <= 1.9); large = vis & ~small
    # ---- small triangles: at most 3 x 3 pixel centres, all at once
    idx_small = np.nonzero(small)[0]
    for s in range(0, len(idx_small), chunk):
        k = idx_small[s:s + chunk]; A, B, C, D, T = a[k], b[k], c[k], d[k], tid[k]
        i0 = np.floor(minx[k] - 0.5).astype(np.int64); j0 = np.floor(miny[k] - 0.5).astype(np.int64)
        hit_i, hit_z, hit_t = [], [], []
        for di in range(3):
            for dj in range(3):
                i = i0 + di; j = j0 + dj; m = (i >= 0) & (i < W) & (j >= 0) & (j < H)
                U = i + 0.5; V = j + 0.5
                l1 = ((B[:, 1] - C[:, 1]) * (U - C[:, 0]) + (C[:, 0] - B[:, 0]) * (V - C[:, 1])) / D
                l2 = ((C[:, 1] - A[:, 1]) * (U - C[:, 0]) + (A[:, 0] - C[:, 0]) * (V - C[:, 1])) / D
                l3 = 1 - l1 - l2; m &= (l1 >= -eps) & (l2 >= -eps) & (l3 >= -eps)
                if m.any(): hit_i.append((j * W + i)[m]); hit_z.append((l1 * A[:, 2] + l2 * B[:, 2] + l3 * C[:, 2])[m]); hit_t.append(T[m])
        if not hit_i: continue
        fi = np.concatenate(hit_i); fz = np.concatenate(hit_z); ft = np.concatenate(hit_t)
        o = np.lexsort((fz, fi)); fi, fz, ft = fi[o], fz[o], ft[o]; last = np.r_[fi[1:] != fi[:-1], True]; fi, fz, ft = fi[last], fz[last], ft[last]
        better = fz > zbuf[fi]; zbuf[fi[better]] = fz[better]; idbuf[fi[better]] = ft[better]
    # ---- large triangles: one at a time (few of them)
    zb = zbuf.reshape(H, W); ib = idbuf.reshape(H, W)
    for k in np.nonzero(large)[0]:
        A, B, C, D = a[k], b[k], c[k], d[k]
        i0 = max(0, int(np.floor(minx[k] - 0.5))); i1 = min(W - 1, int(np.ceil(maxx[k] - 0.5))); j0 = max(0, int(np.floor(miny[k] - 0.5))); j1 = min(H - 1, int(np.ceil(maxy[k] - 0.5)))
        if i1 < i0 or j1 < j0: continue
        U = (np.arange(i0, i1 + 1) + 0.5)[None, :]; V = (np.arange(j0, j1 + 1) + 0.5)[:, None]
        l1 = ((B[1] - C[1]) * (U - C[0]) + (C[0] - B[0]) * (V - C[1])) / D; l2 = ((C[1] - A[1]) * (U - C[0]) + (A[0] - C[0]) * (V - C[1])) / D; l3 = 1 - l1 - l2
        z = l1 * A[2] + l2 * B[2] + l3 * C[2]; sub = zb[j0:j1 + 1, i0:i1 + 1]
        m = (l1 >= -eps) & (l2 >= -eps) & (l3 >= -eps) & (z > sub)
        if m.any(): sub[m] = z[m]; ib[j0:j1 + 1, i0:i1 + 1][m] = tid[k]
    return idbuf.reshape(H, W), zbuf.reshape(H, W)


class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(360, 320)
        self.tris = None            # (n,3,3)
        self.yaw, self.pitch, self.zoom = 0.6, -0.5, 1.0
        self._last = None; self.message = ""; self.dragging = False; self.hl = None; self.hlc = None; self.use_hlc = False; self.overlay = False
        self._cache = None; self._draft_key = None; self._timer = QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(180); self._timer.timeout.connect(self.update)

    def set_triangles(self, tris, n_highlight=0, overlay=False, hl_colors=None):
        a = np.asarray(tris, dtype=float).reshape(-1, 3, 3) if len(tris) else None
        hl = np.zeros(len(a), bool) if a is not None else None
        col = np.zeros((len(a), 3)) if a is not None else None
        if hl is not None and n_highlight:
            hl[-n_highlight:] = True                                           # decoration shells are appended last
            if hl_colors is not None and len(hl_colors) == n_highlight: col[-n_highlight:] = np.asarray(hl_colors, float)
        self.tris = a; self.hl = hl; self.hlc = col; self.use_hlc = hl_colors is not None; self.overlay = overlay; self.dragging = False; self._cache = None; self._draft_key = None
        if a is not None:
            pts = a.reshape(-1, 3); self.centre = (pts.max(0) + pts.min(0)) / 2
            self.radius = float(np.linalg.norm(pts - self.centre, axis=1).max()) or 1.0
        self.update()

    def face_front(self): self.yaw, self.pitch = 0.25, -0.4; self.update()

    def mousePressEvent(self, e): self._last = e.position(); self.dragging = True

    def mouseMoveEvent(self, e):
        if self._last is not None:
            d = e.position() - self._last; self._last = e.position()
            self.yaw += d.x() * 0.01; self.pitch = max(-1.5, min(1.5, self.pitch + d.y() * 0.01)); self.update()

    def mouseReleaseEvent(self, e): self._last = None; self.dragging = False; self.update()

    def wheelEvent(self, e):
        self.zoom *= 1.1 if e.angleDelta().y() > 0 else 1 / 1.1; self.update()

    def render_image(self, W, H, draft=False):
        """Returns an (H, W, 3) uint8 image of the current view."""
        cy, sy, cp, sp = np.cos(self.yaw), np.sin(self.yaw), np.cos(self.pitch), np.sin(self.pitch)
        R = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        v = (self.tris - self.centre) @ R.T
        n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
        front = (n[:, 2] > -0.02) | self.hl                                   # back-face culling; decoration shells always kept
        ids = np.nonzero(front)[0]
        if (self.dragging or draft) and len(ids) > DRAG_MAX:
            keep = ids[~self.hl[ids]]; keep = keep[::int(np.ceil(len(keep) / DRAG_MAX))]; ids = np.sort(np.concatenate([keep, ids[self.hl[ids]]]))
        ss = 1 if (self.dragging or draft or len(ids) > HEAVY) else 2
        s = min(W, H) / 2.2 / self.radius * self.zoom * ss; Wp, Hp = W * ss, H * ss
        V = v[ids]; X = Wp / 2 + V[:, :, 0] * s; Y = Hp / 2 - V[:, :, 1] * s; Z = V[:, :, 2]
        P = np.stack([X, Y, Z], axis=2)
        shade = np.clip(np.abs(n[ids] @ np.array([0.3, -0.5, 0.8])), 0, 1) * 0.7 + 0.3; g = shade * 210
        colors = np.stack([g, g * 0.9 + 20, np.where(g > 200, 255, g + 40)], axis=1)
        hl = self.hl[ids]
        if hl.any():
            if self.use_hlc: colors[hl] = self.hlc[ids][hl] * (0.55 + 0.45 * shade[hl])[:, None]
            else: colors[hl] = np.stack([np.minimum(255, g[hl] + 40), g[hl] / 4, g[hl] / 4], axis=1)
        colors = np.clip(colors, 0, 255).astype(np.uint8)
        idb, _ = rasterise(P[:, 0], P[:, 1], P[:, 2], np.arange(len(ids), dtype=np.int32), Wp, Hp)
        img = np.where((idb >= 0)[..., None], colors[np.maximum(idb, 0)], BG)
        if ss == 2: img = img.reshape(H, 2, W, 2, 3).mean(axis=(1, 3)).astype(np.uint8)            # 2x2 box filter = anti-aliasing
        return np.ascontiguousarray(img)

    def paintEvent(self, _):
        p = QPainter(self); p.fillRect(self.rect(), QColor("#eaf4f9"))
        if self.tris is None:
            p.setPen(QColor("#667")); p.drawText(self.rect(), Qt.AlignCenter, self.message or "—"); return
        W, H = max(2, self.width()), max(2, self.height()); key = (W, H, self.yaw, self.pitch, self.zoom)
        if self._cache is not None and self._cache[0] == key: img = self._cache[1]
        elif len(self.tris) > DRAG_MAX and self._draft_key != key:
            img = self.render_image(W, H, draft=True); self._draft_key = key; self._timer.start()     # heavy mesh: quick decimated frame now, full one once idle
        else: img = self.render_image(W, H); self._cache = (key, img)
        p.drawImage(0, 0, QImage(img.data, W, H, W * 3, QImage.Format_RGB888).copy())
