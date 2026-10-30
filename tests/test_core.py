import tempfile
import unittest
from pathlib import Path

from customlab import openscad
from customlab.meshio import is_watertight, read_stl, write_3mf, write_stl, volume
from customlab.profiles import SizingError, compute_sizing, list_profiles
from customlab.store import Store
from customlab.svgdeco import SVGUnsupported, project_on_cylinder, triangulate

SQUARE = '<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="10" height="10"/></svg>'
STAR = (Path(__file__).parent.parent / "examples/star.svg").read_text()


class Sizing(unittest.TestCase):
    def test_phoenix_ok(self):
        r = compute_sizing("phoenix_hand", "left", "Palm", {"scale_percent": 120})
        self.assertEqual(r.scad_defines, {"HandPerc": 120, "LeftRight": "Left", "part": "Palm"})
        self.assertEqual(r.status, "experimental")
        self.assertTrue(any("EXPERIMENTAL" in w for w in r.warnings))

    def test_phoenix_documented_range(self):
        for v in (99, 161):
            with self.assertRaises(SizingError):
                compute_sizing("phoenix_hand", "right", "Palm", {"scale_percent": v})

    def test_arm_defines_and_fixed_params_not_overridden(self):
        r = compute_sizing("unlimbited_arm", "right", "Cuff", {"HandLen": 170, "ForearmLen": 230, "BicepCircum": 250})
        self.assertEqual(r.scad_defines["LeftRight"], "Right")
        self.assertNotIn("CuffLength", r.scad_defines); self.assertNotIn("PinHoleDia", r.scad_defines)
        self.assertFalse(any("mapping" in w for w in r.warnings))          # mapping now confirmed on the official SCAD
        self.assertEqual(r.derived["HandPerc"], 126)                       # round(170 / 135 * 100)

    def test_rejects_invalid(self):
        bad = [("unlimbited_arm", "right", "Cuff", {"HandLen": 0, "ForearmLen": 1, "BicepCircum": 1}),
               ("unlimbited_arm", "right", "Cuff", {"HandLen": 1, "ForearmLen": 1}),
               ("unlimbited_arm", "right", "Cuff", {"HandLen": 1, "ForearmLen": 1, "BicepCircum": 1, "X": 2}),
               ("unlimbited_arm", "up", "Cuff", {"HandLen": 1, "ForearmLen": 1, "BicepCircum": 1}),
               ("unlimbited_arm", "right", "Bogus", {"HandLen": 1, "ForearmLen": 1, "BicepCircum": 1}),
               ("phoenix_hand", "left", "Palm", {"scale_percent": float("nan")}),
               ("kinetic_hand", "left", "Palm", {}), ("kinetic_arm", "left", "Palm", {})]
        for args in bad:
            with self.assertRaises(SizingError, msg=str(args)):
                compute_sizing(*args)

    def test_all_four_profiles_present_and_no_verified(self):
        ps = list_profiles()
        self.assertEqual({p["id"] for p in ps}, {"phoenix_hand", "unlimbited_arm", "kinetic_hand", "kinetic_arm"})
        self.assertFalse(any(p["status"] == "verified" for p in ps))


class OpenSCAD(unittest.TestCase):
    def test_command(self):
        c = openscad.build_command("openscad", "a.scad", "o.stl", {"scale": 120, "side": "left", "k": 1.5})
        self.assertEqual(c, ["openscad", "-o", "o.stl", "-D", "scale=120", "-D", 'side="left"', "-D", "k=1.5", "a.scad"])

    def test_missing_binary_is_explicit(self):
        orig = openscad.find_openscad; openscad.find_openscad = lambda: None
        try:
            with self.assertRaises(openscad.OpenSCADUnavailable):
                openscad.render("a.scad", "o.stl", {})
        finally:
            openscad.find_openscad = orig


class Store_(unittest.TestCase):
    def test_history_and_compare(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(d); pid = s.create("alias-1")
            m = lambda v: compute_sizing("unlimbited_arm", "left", "Cuff", {"HandLen": v, "ForearmLen": 200, "BicepCircum": 220})
            s.add_record(pid, m(150)); s.add_record(pid, m(160), {"svg": "star"}, fabricated=True)
            c = s.compare(pid, 0, 1)
            self.assertEqual(c["HandLen"]["delta"], 10); self.assertEqual(c["ForearmLen"]["delta"], 0)
            rec = s.load(pid)["records"][1]
            self.assertEqual(rec["profile_version"], compute_sizing("unlimbited_arm", "left", "Cuff", {"HandLen": 150, "ForearmLen": 200, "BicepCircum": 220}).profile_version)
            self.assertEqual(set(s.load(pid)), {"id", "alias", "records"})


class SVG(unittest.TestCase):
    def test_triangulate_concave(self):
        poly = [(0, 0), (4, 0), (4, 4), (2, 1), (0, 4)]
        t = triangulate(poly); self.assertEqual(len(t), 3)

    def test_curves_rejected(self):
        with self.assertRaises(SVGUnsupported):
            project_on_cylinder('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0 C 1 1 2 2 3 3 Z"/></svg>', 45, 60, 70, 2.5)

    def test_projection_watertight_all_modes(self):
        for mode in ("relief", "engrave", "flush"):
            panel, deco = project_on_cylinder(STAR, 45.0, 60.0, 70.0, 2.5, mode)
            self.assertTrue(is_watertight(panel), mode)
            self.assertTrue(is_watertight(deco), mode)
            self.assertGreater(volume(deco), 0); self.assertGreater(volume(panel), 0)

    def test_relief_follows_curvature(self):
        _, deco = project_on_cylinder(SQUARE, 45.0, 60.0, 70.0, 2.5, "relief", depth=1.0, deco_size=40)
        import math
        for tri in deco:
            for x, y, z in tri:
                r = math.hypot(x, z)
                self.assertTrue(44.99 <= r <= 46.01, r)  # between surface and surface+depth


class Mesh(unittest.TestCase):
    def test_stl_roundtrip_and_3mf(self):
        panel, deco = project_on_cylinder(SQUARE, 45.0, 60.0, 70.0, 2.5)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.stl"; write_stl(p, panel)
            self.assertEqual(len(read_stl(p)), len(panel))
            write_3mf(Path(d) / "a.3mf", [("p", panel, 0), ("d", deco, 1)], ["#FFFFFF", "#FF0000"])
            import zipfile, xml.dom.minidom as md
            z = zipfile.ZipFile(Path(d) / "a.3mf")
            md.parseString(z.read("3D/3dmodel.model"))
            self.assertIn("[Content_Types].xml", z.namelist())


if __name__ == "__main__":
    unittest.main()
