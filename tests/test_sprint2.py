import tempfile
import unittest
from pathlib import Path

from customlab import kinetic_arm, openscad, phoenix
from customlab.meshio import bbox, read_stl, volume, write_stl
from customlab.meshscale import scale_stl_openscad, scale_stl_python
from customlab.profiles import SizingError, compute_phoenix_sizing, load_profile


class PhoenixFormula(unittest.TestCase):
    def test_official_worked_example(self):  # page example: 40 mm wrist -> 104.65 %
        self.assertAlmostEqual(phoenix.scale_percent(40), 104.6511, places=3)
        self.assertEqual(phoenix.compute(40).percent_used, 104.65)

    def test_boundaries_inclusive(self):
        self.assertEqual(phoenix.compute(38).percent_used, 100.0)       # (38+5)/43
        self.assertEqual(phoenix.compute(63.8).percent_used, 160.0)     # (63.8+5)/43
        self.assertEqual(phoenix.wrist_range_mm(), (38.0, 63.8))

    def test_out_of_range_never_clamped(self):
        for w in (37.9, 30, 64, 80):
            with self.assertRaises(phoenix.OutOfRange) as c:
                phoenix.compute(w)
            self.assertIn("nothing was adjusted", str(c.exception))
            with self.assertRaises(phoenix.OutOfRange):
                compute_phoenix_sizing("left", "Palm", w)

    def test_custom_margin_and_warnings(self):
        r = phoenix.compute(40, 8)
        self.assertAlmostEqual(r.percent, 111.63, places=2)
        self.assertTrue(any("recommended 5 mm" in w for w in r.warnings))
        self.assertTrue(any("jig" in w.lower() for w in phoenix.compute(40).warnings))

    def test_invalid_inputs(self):
        for a in ((0,), (-1,), (float("nan"),), (True,), (40, -1)):
            with self.assertRaises(ValueError):
                phoenix.compute(*a)

    def test_integrated_sizing(self):
        r = compute_phoenix_sizing("right", "Palm", 40)
        self.assertEqual(r.scad_defines["HandPerc"], 104.65)
        self.assertEqual(r.measurements["wrist_mm"], 40)
        self.assertEqual(r.status, "experimental")

    def test_profile_documents_method(self):
        p = load_profile("phoenix_hand")
        self.assertEqual(p["method"], "phoenix_wrist")
        self.assertIn("43", p["method_doc"])


class ArmRegression(unittest.TestCase):
    def test_arm_fixed_params_and_name_semantics(self):
        p = load_profile("unlimbited_arm")
        self.assertTrue(p["label_mapping_confirmed"])       # confirmed on the official SCAD: A = BicepCircum, B = ForearmLen, C = HandLen
        ids = {i["id"] for i in p["inputs"]}
        self.assertEqual(ids, {"HandLen", "ForearmLen", "BicepCircum"})
        self.assertIn("CuffLength", p["fixed_params"]); self.assertIn("PinHoleDia", p["fixed_params"])

    def test_kinetic_methods_found_in_manuals(self):
        self.assertEqual(load_profile("kinetic_arm")["status"], "experimental"); self.assertNotIn("blocking", load_profile("kinetic_arm"))        # methods: see test_kinetic_hand / test_kinetic_arm
        self.assertEqual(load_profile("kinetic_hand")["status"], "experimental")


class KineticArmChecks(unittest.TestCase):
    def test_residual_limb(self):
        self.assertTrue(kinetic_arm.residual_limb_check(100, 250)["ok"])   # 40 %
        self.assertFalse(kinetic_arm.residual_limb_check(20, 250)["ok"])   # 8 %
        self.assertFalse(kinetic_arm.residual_limb_check(200, 250)["ok"])  # 80 %
        self.assertTrue(kinetic_arm.residual_limb_check(37.5, 250)["ok"])  # exactly 15 %

    def test_scale(self):
        self.assertTrue(kinetic_arm.scale_check(50)["ok"]); self.assertTrue(kinetic_arm.scale_check(100)["ok"])
        self.assertFalse(kinetic_arm.scale_check(49)["ok"]); self.assertFalse(kinetic_arm.scale_check(101)["ok"])


def _cube_stl(path, a=10.0):
    v = [(x, y, z) for x in (0, a) for y in (0, a) for z in (0, a)]
    f = [(0,1,3),(0,3,2),(4,6,7),(4,7,5),(0,4,5),(0,5,1),(2,3,7),(2,7,6),(0,2,6),(0,6,4),(1,5,7),(1,7,3)]
    write_stl(path, [(v[i], v[j], v[k]) for i, j, k in f])


@unittest.skipUnless(openscad.find_openscad(), "OpenSCAD not installed")
class OpenSCADEndToEnd(unittest.TestCase):
    """End-to-end on a SYNTHETIC cube (not an official model)."""
    def test_scad_render_with_defines(self):
        with tempfile.TemporaryDirectory() as d:
            scad = Path(d) / "m.scad"; scad.write_text('side="left"; k=1; cube([10*k,10,10]);')
            out = openscad.render(scad, Path(d) / "o.stl", {"k": 2, "side": "right"})
            lo, hi = bbox(read_stl(out))
            self.assertAlmostEqual(hi[0] - lo[0], 20.0, places=3)

    def test_mesh_scale_matches_python_and_phoenix_percent(self):
        pct = phoenix.compute(40).percent_used
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "c.stl"; _cube_stl(src)
            a, b = Path(d) / "a.stl", Path(d) / "b.stl"
            scale_stl_openscad(src, a, pct); scale_stl_python(src, b, pct)
            va, vb = volume(read_stl(a)), volume(read_stl(b))
            self.assertAlmostEqual(va, 1000 * (pct / 100) ** 3, delta=0.5)
            self.assertAlmostEqual(va, vb, delta=0.5)
            lo, hi = bbox(read_stl(a)); self.assertAlmostEqual(hi[0] - lo[0], 10 * pct / 100, places=2)


if __name__ == "__main__":
    unittest.main()
