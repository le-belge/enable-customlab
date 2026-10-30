"""SVG decoration demo: project flat polygons onto a curved panel.

SCOPE: demonstrator on a generic cylindrical patch (axis = Y), NOT on a real
e-NABLE part (real geometry/zones not yet available). Supports rect, circle,
polygon and path with M/L/H/V/Z (absolute+relative). Curves are NOT supported
and raise an error rather than being silently approximated.
"""
import math
import re
import xml.etree.ElementTree as ET


class SVGUnsupported(ValueError):
    pass


def _local(tag): return tag.rsplit("}", 1)[-1]


def parse_svg(text, circle_segments=32):
    """Return list of polygons [(x,y),...] in SVG units (y down), plus fill colours."""
    root = ET.fromstring(text)
    out = []
    for el in root.iter():
        t = _local(el.tag)
        a = el.attrib
        fill = a.get("fill", "#000000")
        if t == "rect":
            x, y, w, h = (float(a.get(k, 0)) for k in ("x", "y", "width", "height"))
            out.append(([(x, y), (x+w, y), (x+w, y+h), (x, y+h)], fill))
        elif t == "circle":
            cx, cy, r = (float(a[k]) for k in ("cx", "cy", "r"))
            out.append(([(cx + r*math.cos(2*math.pi*i/circle_segments), cy + r*math.sin(2*math.pi*i/circle_segments))
                         for i in range(circle_segments)], fill))
        elif t == "polygon":
            nums = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", a["points"])]
            out.append((list(zip(nums[0::2], nums[1::2])), fill))
        elif t == "path":
            for poly in _path(a["d"]):
                out.append((poly, fill))
        elif t in ("ellipse", "line", "polyline", "text", "image"):
            raise SVGUnsupported(f"<{t}> not supported (convert text/strokes to outlined paths)")
    return out


def _path(d):
    toks = re.findall(r"[MmLlHhVvZz]|-?\d*\.?\d+(?:e-?\d+)?|[A-Za-z]", d)
    polys, cur, pos, i, cmd = [], [], (0.0, 0.0), 0, None
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            if t not in "MmLlHhVvZz":
                raise SVGUnsupported(f"path command '{t}' not supported (curves need flattening)")
            cmd = t; i += 1
            if t in "Zz":
                if cur: polys.append(cur); cur = []
                continue
        n = 1 if cmd in "HhVv" else 2
        v = [float(x) for x in toks[i:i+n]]; i += n
        x, y = pos
        if cmd in "Mm": pos = (v[0] + (x if cmd == "m" else 0), v[1] + (y if cmd == "m" else 0)); cmd = "L" if cmd == "M" else "l"
        elif cmd in "Ll": pos = (v[0] + (x if cmd == "l" else 0), v[1] + (y if cmd == "l" else 0))
        elif cmd in "Hh": pos = (v[0] + (x if cmd == "h" else 0), y)
        elif cmd in "Vv": pos = (x, v[0] + (y if cmd == "v" else 0))
        if cur and len(cur) == 0: pass
        cur.append(pos)
    if len(cur) >= 3: polys.append(cur)
    return polys


def _area(p): return sum(p[i][0]*p[(i+1) % len(p)][1] - p[(i+1) % len(p)][0]*p[i][1] for i in range(len(p))) / 2


def triangulate(poly):
    """Ear clipping for simple polygons (no holes). Returns index triples, CCW."""
    idx = list(range(len(poly)))
    if _area(poly) < 0: idx.reverse()
    out = []
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    def inside(p, a, b, c): return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k-1], idx[k], idx[(k+1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if cross(a, b, c) <= 1e-12: continue
            if any(inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)): continue
            out.append((i0, i1, i2)); idx.pop(k); break
        else:
            raise SVGUnsupported("polygon not simple (self-intersection or holes unsupported)")
    out.append((idx[0], idx[1], idx[2]))
    return out


def project_on_cylinder(svg_text, radius, panel_w, panel_l, thickness, mode="relief",
                        depth=0.6, deco_size=None):
    """Return (panel_tris, deco_tris). Panel = cylindrical patch (axis Y) of radial thickness `thickness`.
    mode: 'relief' (raised by depth), 'engrave' (cut: deco volume to subtract), 'flush' (colour insert filling the panel skin).
    The SVG is fit-centered into panel_w x panel_l (mm). Surface point: z = sqrt(R^2 - x^2).
    """
    shapes = parse_svg(svg_text)
    if not shapes: raise SVGUnsupported("no drawable shape")
    pts = [p for s, _ in shapes for p in s]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = (deco_size or min(panel_w, panel_l) * 0.8) / max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    def surf(x, r_off):
        if abs(x) >= radius: raise SVGUnsupported("decoration exceeds cylinder width")
        return math.sqrt(radius**2 - x*x), x  # radial scale below
    def P(x, y, off):
        # point at lateral x, along y, radial offset `off` from the outer surface (positive outward)
        R = radius + off
        th = x / radius  # arc length -> angle (conformal in x)
        return (R*math.sin(th), y, R*math.cos(th))
    panel = []
    nx, ny = 24, 4
    xs = [(-panel_w/2) + panel_w*i/nx for i in range(nx+1)]
    ys = [(-panel_l/2) + panel_l*j/ny for j in range(ny+1)]
    for off_o, off_i, flip in ((0, 0, False),):
        pass
    for i in range(nx):
        for j in range(ny):
            q = lambda a, b, off: P(xs[a], ys[b], off)
            o = [q(i, j, 0), q(i+1, j, 0), q(i+1, j+1, 0), q(i, j+1, 0)]
            n = [q(i, j, -thickness), q(i+1, j, -thickness), q(i+1, j+1, -thickness), q(i, j+1, -thickness)]
            panel += [(o[0], o[1], o[2]), (o[0], o[2], o[3]), (n[0], n[2], n[1]), (n[0], n[3], n[2])]
    for j in range(ny):  # side walls x=±w/2
        for xi, fl in ((0, False), (nx, True)):
            a, b = P(xs[xi], ys[j], 0), P(xs[xi], ys[j+1], 0)
            c, d = P(xs[xi], ys[j+1], -thickness), P(xs[xi], ys[j], -thickness)
            panel += [(a, b, c), (a, c, d)] if not fl else [(a, c, b), (a, d, c)]
    for i in range(nx):  # end walls y=±l/2
        for yj, fl in ((0, False), (ny, True)):
            a, b = P(xs[i], ys[yj], 0), P(xs[i+1], ys[yj], 0)
            c, d = P(xs[i+1], ys[yj], -thickness), P(xs[i], ys[yj], -thickness)
            panel += [(a, c, b), (a, d, c)] if not fl else [(a, b, c), (a, c, d)]
    top, bot = {"relief": (depth, 0), "engrave": (0.001, -depth), "flush": (0, -depth)}[mode]
    deco = []
    for poly, _ in shapes:
        pp = [((x - cx) * k, -(y - cy) * k) for x, y in poly]
        if _area(pp) < 0: pp.reverse()
        tris = triangulate(pp)
        for i0, i1, i2 in tris:
            a, b, c = (pp[i0], pp[i1], pp[i2])
            deco.append((P(*a, top), P(*b, top), P(*c, top)))
            deco.append((P(*a, bot), P(*c, bot), P(*b, bot)))
        n = len(pp)
        for i in range(n):
            a, b = pp[i], pp[(i+1) % n]
            A, B, C, D = P(*a, bot), P(*b, bot), P(*b, top), P(*a, top)
            deco += [(A, B, C), (A, C, D)]
    return panel, deco
