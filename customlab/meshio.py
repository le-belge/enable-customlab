"""Minimal mesh utilities: STL read/write, geometry checks, 3MF writer (multi-material).

3MF output follows the core spec (basematerials). It has NOT been validated in
Bambu Studio yet — see docs/FABRICATION_X1C.md.
"""
import struct
import zipfile
from pathlib import Path

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


# ---------------------------------------------------------------- 3MF reading
_NS3 = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
_NSP = "{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}"


def _m3(s):
    """3MF transform "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32" (row vectors: p' = p . M + t) -> (3x3 rows, t)."""
    v = [float(x) for x in s.split()] if s else [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
    return [v[0:3], v[3:6], v[6:9]], v[9:12]


def _compose(a, b):
    """Transform a then b."""
    (ra, ta), (rb, tb) = a, b
    r = [[sum(ra[i][k] * rb[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    t = [sum(ta[k] * rb[k][j] for k in range(3)) + tb[j] for j in range(3)]
    return r, t


def read_3mf(path):
    """Objects placed on the build plate of a 3MF file: [(name, triangles)] in plate coordinates (mm). Follows components, including
    those stored in other model files (Bambu Studio / production extension). Colours and materials are ignored."""
    import posixpath
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(path); names = set(z.namelist()); docs = {}

    def doc(p):
        p = p.lstrip("/")
        if p not in docs:
            if p not in names: raise ValueError(f"3MF : fichier interne absent ({p})")
            docs[p] = ET.fromstring(z.read(p))
        return docs[p]

    root = "3D/3dmodel.model"
    if "_rels/.rels" in names:
        rel = ET.fromstring(z.read("_rels/.rels"))
        for r in rel:
            if r.get("Type", "").endswith("/3dmodel"): root = r.get("Target", root).lstrip("/"); break

    def obj(p, oid):
        for o in doc(p).iter(_NS3 + "object"):
            if o.get("id") == oid: return o
        raise ValueError(f"3MF : objet {oid} introuvable dans {p}")

    def tris_of(p, oid, tr, depth=0):
        if depth > 16: raise ValueError("3MF : composants imbriqués trop profondément")
        o = obj(p, oid); out = []; mesh = o.find(_NS3 + "mesh")
        if mesh is not None:
            vs = [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in mesh.find(_NS3 + "vertices")]
            (r, t) = tr; w = [tuple(sum(x[k] * r[k][j] for k in range(3)) + t[j] for j in range(3)) for x in vs]
            for f in mesh.find(_NS3 + "triangles"): out.append((w[int(f.get("v1"))], w[int(f.get("v2"))], w[int(f.get("v3"))]))
        comps = o.find(_NS3 + "components")
        if comps is not None:
            for c in comps:
                sub = c.get(_NSP + "path") or p
                out += tris_of(sub.lstrip("/"), c.get("objectid"), _compose(_m3(c.get("transform")), tr), depth + 1)
        return out

    bambu_names = {}                                                     # Bambu Studio keeps object names in Metadata/model_settings.config
    if "Metadata/model_settings.config" in names:
        try:
            for o in ET.fromstring(z.read("Metadata/model_settings.config")).iter("object"):
                n = next((m.get("value") for m in o.iter("metadata") if m.get("key") == "name"), None)
                if n: bambu_names[o.get("id")] = n
        except ET.ParseError: pass
    objects = []
    for k, it in enumerate(doc(root).iter(_NS3 + "item"), start=1):
        oid = it.get("objectid"); o = obj(root, oid); t = tris_of(root, oid, _m3(it.get("transform")))
        if t: objects.append((o.get("name") or bambu_names.get(oid) or f"objet {k}", t))
    if not objects: raise ValueError("3MF : aucun objet sur le plateau")
    return objects


def stl_from_3mf(path, out_root, pick=None):
    """Converts a 3MF to an STL the app can work on: out_root/<stem>_<hash>/<stem>.stl (the original is never touched). pick: index of the
    object to keep, None = all objects merged. README.txt + LICENSE.txt found beside the 3MF (or in a parent folder) are copied so the
    licence is still recognised. Returns (stl path, number of objects in the file)."""
    import hashlib
    import shutil
    src = Path(path); objs = read_3mf(src); chosen = objs if pick is None else [objs[pick]]
    tris = [t for _, ts in chosen for t in ts]
    tag = hashlib.sha256(src.read_bytes()).hexdigest()[:10] + ("" if pick is None else f"_o{pick + 1}")
    stem = src.stem if pick is None else f"{src.stem}_{chosen[0][0]}"
    stem = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in stem)[:60]
    folder = Path(out_root) / f"{stem}_{tag}"; folder.mkdir(parents=True, exist_ok=True); out = folder / f"{stem}.stl"
    if not out.is_file(): write_stl(out, tris)
    for d in [src.parent, *list(src.parents)[:6]]:
        if (d / "README.txt").is_file() and (d / "LICENSE.txt").is_file():
            for n in ("README.txt", "LICENSE.txt"): shutil.copyfile(d / n, folder / n)
            break
    return out, len(objs)
