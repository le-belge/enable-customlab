"""Bambu Studio flavoured 3MF: ONE object made of several parts, each with its own filament (extruder) slot.

Layout mirrors what Bambu Studio 02.08 writes itself (checked on a 3MF it produced): a parent <object> whose
<component>s point to one mesh file per part (3D/Objects/object_K.model); Metadata/model_settings.config lists the
parts and their `extruder`. Verified only by opening files in Bambu Studio 02.08.03.66 (see docs); other versions untested.
"""
import uuid
import zipfile
from xml.sax.saxutils import escape

NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
      'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')


def _mesh_xml(obj_id, tris):
    index, vs, ts = {}, [], []
    for t in tris:
        ids = []
        for pnt in t:
            k = (round(pnt[0], 5), round(pnt[1], 5), round(pnt[2], 5))
            if k not in index: index[k] = len(vs); vs.append(k)
            ids.append(index[k])
        ts.append(ids)
    v = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in vs)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in ts)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {NS}>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            f' <resources>\n  <object id="{obj_id}" p:UUID="{uuid.uuid4()}" type="model">\n   <mesh>\n    <vertices>{v}</vertices>\n    <triangles>{t}</triangles>\n   </mesh>\n  </object>\n </resources>\n <build/>\n</model>\n'), len(ts)


WITH_FILAMENT_CONFIG = True      # declare the filaments (count + colours) in Metadata/project_settings.config; opened successfully by the user in Bambu Studio on 2026-10-29 (version not noted)


def project_settings_json(colours):
    """Minimal project config: only the number of filaments and their colours; Bambu fills in every other key. Opening such a partial file in Bambu Studio
    worked for the user (2026-10-29); other versions are untested: see docs/BAMBU_FILAMENTS.md."""
    import json
    return json.dumps({"filament_colour": list(colours), "filament_diameter": ["1.75"] * len(colours), "from": "project"}, indent=2)


def write_bambu_3mf(path, parts, object_name="CustomLab", bed=(256.0, 256.0), filament_colours=None):
    """parts: list of {"name": str, "triangles": [...], "extruder": int>=1}. World coordinates are kept; the object is
    centred on the plate and dropped to z=0 through the build transform only."""
    if not parts: raise ValueError("no parts")
    pts = [p for part in parts for t in part["triangles"] for p in t]
    lo = [min(p[i] for p in pts) for i in range(3)]; hi = [max(p[i] for p in pts) for i in range(3)]
    tx, ty, tz = bed[0] / 2 - (lo[0] + hi[0]) / 2, bed[1] / 2 - (lo[1] + hi[1]) / 2, -lo[2]
    n = len(parts); obj_id = n + 1                               # parts are objects 1..n, the parent is n+1
    files, comps, pxml = {}, [], []
    for k, part in enumerate(parts, start=1):
        xml, faces = _mesh_xml(k, part["triangles"]); files[f"3D/Objects/object_{k}.model"] = xml
        comps.append(f'<component p:path="/3D/Objects/object_{k}.model" objectid="{k}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
        nm = escape(part["name"], {'"': "&quot;"})
        pxml.append(f'''    <part id="{k}" subtype="normal_part">
      <metadata key="name" value="{nm}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="extruder" value="{int(part["extruder"])}"/>
      <mesh_stat face_count="{faces}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>''')
    model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {NS}>\n'
             ' <metadata name="Application">CustomLab</metadata>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
             f' <metadata name="Title">{escape(object_name)}</metadata>\n <resources>\n  <object id="{obj_id}" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n    '
             + "\n    ".join(comps) + f'\n   </components>\n  </object>\n </resources>\n <build p:UUID="{uuid.uuid4()}">\n'
             f'  <item objectid="{obj_id}" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 {tx:.5f} {ty:.5f} {tz:.5f}" printable="1"/>\n </build>\n</model>\n')
    first_ext = int(parts[0]["extruder"])
    settings = (f'<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <object id="{obj_id}">\n    <metadata key="name" value="{escape(object_name)}"/>\n'
                f'    <metadata key="extruder" value="{first_ext}"/>\n' + "\n".join(pxml) + f'''
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
    <model_instance>
      <metadata key="object_id" value="{obj_id}"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="{obj_id * 7}"/>
    </model_instance>
  </plate>
  <assemble>
  </assemble>
</config>
''')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
          ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
          ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n</Types>\n')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')
    mrels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
             + "".join(f' <Relationship Target="/3D/Objects/object_{k}.model" Id="rel-{k}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n' for k in range(1, n + 1))
             + '</Relationships>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model); z.writestr("3D/_rels/3dmodel.model.rels", mrels)
        for name, xml in files.items(): z.writestr(name, xml)
        z.writestr("Metadata/model_settings.config", settings)
        if filament_colours: z.writestr("Metadata/project_settings.config", project_settings_json(filament_colours))
    return path
