"""GPU 3D viewer (QOpenGLWidget, OpenGL 3.3 core): same interface as viewer.MeshView, smooth with meshes of several 100k triangles.

make_view() returns this widget on a real display and the numpy rasteriser (viewer.MeshView) where OpenGL is not wanted or
available (offscreen platform = tests, CUSTOMLAB_GL=0).
"""
import os
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QSurfaceFormat, QVector3D
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLFunctions_3_3_Core, QOpenGLShader, QOpenGLShaderProgram, QOpenGLVertexArrayObject
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication

MAX_TRIS = 1_200_000
VERT = """#version 330 core
in vec3 pos; in vec3 nrm; in vec4 col;
uniform vec3 r0, r1, r2, centre; uniform vec3 scl;
out vec3 vcol; out float vshade; flat out int vmode;
void main() {
    vec3 p = pos - centre; vec3 v = vec3(dot(r0, p), dot(r1, p), dot(r2, p)); vec3 n = vec3(dot(r0, nrm), dot(r1, nrm), dot(r2, nrm));
    gl_Position = vec4(v.x * scl.x, v.y * scl.y, -v.z * scl.z, 1.0);
    vshade = clamp(abs(dot(n, normalize(vec3(0.3, -0.5, 0.8)))), 0.0, 1.0) * 0.7 + 0.3; vcol = col.rgb; vmode = int(col.a + 0.5);
}"""
FRAG = """#version 330 core
in vec3 vcol; in float vshade; flat in int vmode; out vec4 outc;
void main() {
    float g = vshade * 210.0 / 255.0; vec3 c;
    if (vmode == 1) c = vcol * (0.55 + 0.45 * vshade);
    else if (vmode == 2) c = vec3(min(1.0, g + 40.0 / 255.0), g / 4.0, g / 4.0);
    else c = vec3(g, g * 0.9 + 20.0 / 255.0, g > 200.0 / 255.0 ? 1.0 : g + 40.0 / 255.0);
    outc = vec4(clamp(c, 0.0, 1.0), 1.0);
}"""


def use_gl():
    return os.environ.get("CUSTOMLAB_GL") != "0" and QApplication.platformName() not in ("offscreen", "minimal")


def set_default_format():
    """Call before the QApplication is created (macOS only gives a 3.3 core context when asked for it up front)."""
    f = QSurfaceFormat(); f.setVersion(3, 3); f.setProfile(QSurfaceFormat.CoreProfile); f.setDepthBufferSize(24); f.setSamples(4); QSurfaceFormat.setDefaultFormat(f)


class GLMeshView(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(360, 320)
        self.tris = None; self.yaw, self.pitch, self.zoom = 0.6, -0.5, 1.0; self._last = None; self.message = ""; self.dragging = False
        self.overlay = False; self.radius = 1.0; self.centre = np.zeros(3); self._data = None; self._n = 0; self._ready = False; self._err = ""

    # ---- same interface as MeshView
    def set_triangles(self, tris, n_highlight=0, overlay=False, hl_colors=None):
        a = np.asarray(tris, dtype=np.float32).reshape(-1, 3, 3) if len(tris) else None
        self.overlay = overlay; self.dragging = False
        if a is None: self.tris = None; self._data = None; self._n = 0; self.update(); return
        if len(a) > MAX_TRIS and not n_highlight: a = a[::int(np.ceil(len(a) / MAX_TRIS))]
        n = np.cross(a[:, 1] - a[:, 0], a[:, 2] - a[:, 0]); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
        col = np.zeros((len(a), 4), np.float32)
        if n_highlight:
            col[-n_highlight:, 3] = 2
            if hl_colors is not None and len(hl_colors) == n_highlight: col[-n_highlight:, :3] = np.asarray(hl_colors, np.float32) / 255.0; col[-n_highlight:, 3] = 1
        d = np.empty((len(a), 3, 10), np.float32); d[:, :, 0:3] = a; d[:, :, 3:6] = n[:, None, :]; d[:, :, 6:10] = col[:, None, :]
        self.tris = a; self._data = d.reshape(-1, 10); self._n = len(self._data); self._dirty = True
        pts = a.reshape(-1, 3); self.centre = ((pts.max(0) + pts.min(0)) / 2).astype(np.float64)
        self.radius = float(np.linalg.norm(pts - self.centre, axis=1).max()) or 1.0; self.update()

    def face_front(self): self.yaw, self.pitch = 0.25, -0.4; self.update()

    def mousePressEvent(self, e): self._last = e.position(); self.dragging = True

    def mouseMoveEvent(self, e):
        if self._last is not None:
            d = e.position() - self._last; self._last = e.position()
            self.yaw += d.x() * 0.01; self.pitch = max(-1.5, min(1.5, self.pitch + d.y() * 0.01)); self.update()

    def mouseReleaseEvent(self, e): self._last = None; self.dragging = False; self.update()

    def wheelEvent(self, e): self.zoom *= 1.1 if e.angleDelta().y() > 0 else 1 / 1.1; self.update()

    # ---- OpenGL
    def initializeGL(self):
        try:
            self.gl = QOpenGLFunctions_3_3_Core(); self.gl.initializeOpenGLFunctions()
            self.prog = QOpenGLShaderProgram(self)
            if not (self.prog.addShaderFromSourceCode(QOpenGLShader.Vertex, VERT) and self.prog.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAG) and self.prog.link()):
                raise RuntimeError(self.prog.log())
            self.vao = QOpenGLVertexArrayObject(self); self.vao.create(); self.buf = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer); self.buf.create()
            self._ready = True; self._dirty = self._data is not None
        except Exception as e: self._err = str(e)[:200]

    def _upload(self):
        self.vao.bind(); self.buf.bind(); raw = np.ascontiguousarray(self._data).tobytes(); self.buf.allocate(raw, len(raw)); self.prog.bind()
        for name, off, k in (("pos", 0, 3), ("nrm", 12, 3), ("col", 24, 4)):
            loc = self.prog.attributeLocation(name); self.prog.enableAttributeArray(loc); self.prog.setAttributeBuffer(loc, 0x1406, off, k, 40)
        self.vao.release(); self._dirty = False

    def paintGL(self):
        if not self._ready:
            p = QPainter(self); p.fillRect(self.rect(), QColor("#f4f5f7")); p.setPen(QColor("#a33")); p.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, "OpenGL indisponible (CUSTOMLAB_GL=0 pour l'aperçu logiciel)\n" + self._err); return
        gl = self.gl; gl.glClearColor(244 / 255, 245 / 255, 247 / 255, 1.0); gl.glClear(0x4100)
        if self._data is None or not self._n:
            p = QPainter(self); p.setPen(QColor("#667")); p.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self.message or "—"); return
        if self._dirty: self._upload()
        W, H = max(2, self.width()), max(2, self.height()); s = min(W, H) / 2.2 / self.radius * self.zoom
        cy, sy, cp, sp = np.cos(self.yaw), np.sin(self.yaw), np.cos(self.pitch), np.sin(self.pitch)
        R = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        gl.glEnable(0x0B71); gl.glDepthFunc(0x0201)
        self.prog.bind()
        for i in range(3): self.prog.setUniformValue(f"r{i}", QVector3D(*map(float, R[i])))
        self.prog.setUniformValue("centre", QVector3D(*map(float, self.centre))); self.prog.setUniformValue("scl", QVector3D(2 * s / W, 2 * s / H, 1.0 / (self.radius * 1.6 * max(self.zoom, 0.3))))
        self.vao.bind(); gl.glDrawArrays(0x0004, 0, self._n); self.vao.release(); self.prog.release()


def make_view():
    from .viewer import MeshView
    return GLMeshView() if use_gl() else MeshView()
