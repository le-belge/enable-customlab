import argparse
import json
import sys
from pathlib import Path

from . import openscad, paths
from .profiles import SizingError, compute_sizing, list_profiles
from .meshio import write_stl, write_3mf, volume, is_watertight, bbox


def main(argv=None):
    ap = argparse.ArgumentParser(prog="customlab")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("devices")
    s = sub.add_parser("size")
    s.add_argument("device"); s.add_argument("--side", required=True)
    s.add_argument("--part", required=True)
    s.add_argument("--set", action="append", default=[], metavar="ID=VALUE")
    s.add_argument("--scad", help="user-provided .scad file"); s.add_argument("--out")
    d = sub.add_parser("demo-svg")
    d.add_argument("svg"); d.add_argument("--mode", default="relief", choices=["relief", "engrave", "flush"])
    d.add_argument("--out-dir", default="out")
    v = sub.add_parser("validation-pack", help="synthetic STL/3MF files to test import in slicers")
    v.add_argument("--out-dir", default="validation_pack")
    w = sub.add_parser("phoenix-scale"); w.add_argument("wrist_mm", type=float); w.add_argument("--margin", type=float, default=5.0)
    a = ap.parse_args(argv)
    if a.cmd == "phoenix-scale":
        from . import phoenix
        try:
            r = phoenix.compute(a.wrist_mm, a.margin)
        except (phoenix.OutOfRange, ValueError) as e:
            print(f"ERROR: {e}", file=sys.stderr); return 2
        print(f"scale = {r.percent_used} %"); [print("WARNING:", x) for x in r.warnings]; return 0
    if a.cmd == "validation-pack":
        from .svgdeco import project_on_cylinder
        out = Path(a.out_dir); out.mkdir(exist_ok=True)
        panel, deco = project_on_cylinder((paths.resource_dir() / "examples/star.svg").read_text(), 45.0, 60.0, 70.0, 2.5)
        write_stl(out / "synthetic_panel.stl", panel); write_stl(out / "synthetic_decoration.stl", deco)
        write_3mf(out / "synthetic_two_colours.3mf", [("panel", panel, 0), ("decoration", deco, 1)], ["#C0C0C0", "#E03030"])
        (out / "CHECKLIST.md").write_text(
            "# Bambu Studio import validation (SYNTHETIC files, not an e-NABLE device)\n"
            "Fill in by hand. Nothing here is validated until you tick it.\n\n"
            "- [ ] synthetic_panel.stl imports; size ~60 x 70 mm (curved, 2.5 mm thick)\n"
            "- [ ] synthetic_two_colours.3mf imports as 2 objects / 2 filament colours (grey, red)\n"
            "- [ ] AMS filament mapping works; slicing succeeds; preview shows both colours\n"
            "- [ ] Same checks in OrcaSlicer / PrusaSlicer / Cura (3MF colours may not map: note it)\n"
            "Observations / Bambu Studio version:\n", encoding="utf-8")
        print(f"pack written to {out}/ — open the files in Bambu Studio and fill CHECKLIST.md"); return 0
    if a.cmd == "devices":
        for p in list_profiles():
            print(f"{p['id']:16} {p['status']:12} {p['name']}  [{p['license']['name']}]")
        return 0
    if a.cmd == "size":
        try:
            m = {k: float(v) for k, v in (x.split("=", 1) for x in a.set)}
            r = compute_sizing(a.device, a.side, a.part, m)
        except (SizingError, ValueError) as e:
            print(f"ERROR: {e}", file=sys.stderr); return 2
        print(json.dumps({"defines": r.scad_defines, "status": r.status, "warnings": r.warnings}, indent=2, ensure_ascii=False))
        if a.scad:
            try:
                print(openscad.render(a.scad, a.out or f"{a.device}_{a.part}.stl", r.scad_defines))
            except openscad.OpenSCADUnavailable as e:
                print(f"ERROR: {e}", file=sys.stderr); return 3
        return 0
    if a.cmd == "demo-svg":
        from .svgdeco import project_on_cylinder, SVGUnsupported
        out = Path(a.out_dir); out.mkdir(exist_ok=True)
        try:
            panel, deco = project_on_cylinder(Path(a.svg).read_text(), 45.0, 60.0, 70.0, 2.5, a.mode)
        except SVGUnsupported as e:
            print(f"ERROR: {e}", file=sys.stderr); return 2
        write_stl(out / "panel.stl", panel); write_stl(out / "decoration.stl", deco)
        write_3mf(out / "demo.3mf", [("panel", panel, 0), ("decoration", deco, 1)], ["#C0C0C0", "#E03030"])
        print(f"panel watertight={is_watertight(panel)} vol={volume(panel):.1f}mm3 | deco watertight={is_watertight(deco)} bbox={bbox(deco)}")
        print("EXPERIMENTAL demo on a generic panel. 3MF not validated in Bambu Studio.")
        return 0
