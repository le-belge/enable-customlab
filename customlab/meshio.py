"""Minimal mesh utilities: STL read/write, geometry checks, 3MF writer (multi-material).

3MF output follows the core spec (basematerials). It has NOT been validated in
Bambu Studio yet — see docs/FABRICATION_X1C.md.
"""
import struct
import zipfile

Tri = tuple  # ((x,y,z),(x,y,z),(x,y,z))


def write_stl(path, tris, name="customlab"):
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            n = normal(a, b, c)
            f.write(struct.pack("<12fH", *n, *a, *b, *c, 0))


def read_stl(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) >= 84 and 84 + struct.unpack("<I", data[80:84])[0] * 50 == len(data):
        n = struct.unpack("<I", data[80:84])[0]
        tris = []
        for i in range(n):
            v = struct.unpack("<12fH", data[84 + 50 * i:134 + 50 * i])
            tris.append((v[3:6], v[6:9], v[9:12]))
        return tris
    tris, cur = [], []
    for line in data.decode("ascii", "ignore").splitlines():
        p = line.split()
        if p[:1] == ["vertex"]:
            cur.append(tuple(float(x) for x in p[1:4]))
            if len(cur) == 3:
                tris.append(tuple(cur)); cur = []
    return tris


def normal(a, b, c):
    u = [b[i] - a[i] for i in range(3)]; v = [c[i] - a[i] for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    l = sum(x*x for x in n) ** .5 or 1.0
    return tuple(x / l for x in n)


def bbox(tris):
    pts = [p for t in tris for p in t]
    return tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))


def volume(tris):
    return sum(a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])
               for a, b, c in tris) / 6.0


def is_watertight(tris, nd=5):
    """Every undirected edge shared by exactly two triangles, with opposite orientation."""
    from collections import Counter
    key = lambda p: tuple(round(x, nd) for x in p)
    e = Counter()
    for a, b, c in tris:
        a, b, c = key(a), key(b), key(c)
        for u, v in ((a, b), (b, c), (c, a)):
            e[(u, v)] += 1
    return all(n == 1 and e.get((v, u)) == 1 for (u, v), n in e.items())


def write_3mf(path, objects, colors):
    """objects: list of (name, tris, material_index); colors: list of '#RRGGBB'."""
    verts_xml = []
    for i, (name, tris, mat) in enumerate(objects, start=1):
        index, vs, ts = {}, [], []
        for t in tris:
            ids = []
            for p in t:
                k = tuple(round(x, 6) for x in p)
                if k not in index:
                    index[k] = len(vs); vs.append(k)
                ids.append(index[k])
            ts.append(ids)
        v = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in vs)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in ts)
        verts_xml.append(f'<object id="{i+1}" name="{name}" type="model" pid="1" pindex="{mat}">'
                         f'<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh></object>')
    mats = "".join(f'<base name="m{i}" displaycolor="{c.upper()}FF"/>' for i, c in enumerate(colors))
    build = "".join(f'<item objectid="{i+2}"/>' for i in range(len(objects)))
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources><basematerials id="1">{mats}</basematerials>{"".join(verts_xml)}</resources>'
             f'<build>{build}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
