import os
import tempfile
import unittest
from pathlib import Path

from customlab import armgen, openscad
from customlab.licenseinfo import read_license_info
from customlab.meshio import bbox, read_stl
from customlab.profiles import compute_sizing, load_profile

PROF = load_profile("unlimbited_arm")
HAVE = armgen.scad_path(PROF) is not None and openscad.find_openscad() is not None


class ArmSizing(unittest.TestCase):
    OK = {"HandLen": 150, "ForearmLen": 200, "BicepCircum": 220}

    def test_official_ranges_enforced_never_clamped(self):
        for name, bad in (("HandLen", 134), ("HandLen", 231), ("ForearmLen", 119), ("ForearmLen", 316), ("BicepCircum", 109), ("BicepCircum", 351)):
            from customlab.profiles import SizingError
            with self.assertRaises(SizingError, msg=f"{name}={bad}"): compute_sizing("unlimbited_arm", "left", "Cuff", {**self.OK, name: bad})
        for name, edge in (("HandLen", 135), ("HandLen", 230), ("ForearmLen", 120), ("ForearmLen", 315), ("BicepCircum", 110), ("BicepCircum", 350)):
            compute_sizing("unlimbited_arm", "left", "Cuff", {**self.OK, name: edge})

    def test_real_scad_parameters_and_side_values(self):
        r = compute_sizing("unlimbited_arm", "right", "Forearm", self.OK)
        self.assertEqual(r.scad_defines, {"BicepCircum": 220, "ForearmLen": 200, "HandLen": 150, "LeftRight": "Right", "part": "Forearm"})
        self.assertNotIn("CuffLength", r.scad_defines); self.assertNotIn("PinHoleDia", r.scad_defines)
        self.assertEqual([i["letter"] for i in PROF["inputs"]], ["A", "B", "C"]); self.assertEqual([i["id"] for i in PROF["inputs"]], ["BicepCircum", "ForearmLen", "HandLen"])

    def test_hand_scale_derived_like_the_scad(self):
        for hl, want in ((135, 100), (150, 111), (230, 170), (140, 104), (136, 101)):
            self.assertEqual(compute_sizing("unlimbited_arm", "left", "Palm", {**self.OK, "HandLen": hl}).derived["HandPerc"], want, hl)
        self.assertEqual(compute_sizing("unlimbited_arm", "left", "Palm", {**self.OK, "HandLen": 135.3}).derived["HandPerc"], 100)


@unittest.skipUnless(HAVE, "official arm SCAD or OpenSCAD not available locally")
class ArmGeneration(unittest.TestCase):
    def test_generate_cache_and_provenance(self):
        d = tempfile.mkdtemp(prefix="armcache_"); defs = compute_sizing("unlimbited_arm", "left", "Pins", ArmSizing.OK).scad_defines
        path, cached = armgen.generate_part("unlimbited_arm", defs, cache_dir=d); self.assertFalse(cached); self.assertTrue(path.is_file())
        w = lambda p: (lambda lo, hi: hi[0] - lo[0])(*bbox(read_stl(p)))
        p135, _ = armgen.generate_part("unlimbited_arm", {**defs, "HandLen": 135}, cache_dir=d)                   # HandPerc = 100 %
        self.assertAlmostEqual(w(path) / w(p135), 1.11, delta=0.005)                                              # HandPerc = 111 % -> pins scale by 1.11
        lic = read_license_info(path); self.assertTrue(lic["known"]); self.assertTrue(lic["non_commercial"]); self.assertTrue(lic["share_alike"]); self.assertEqual(lic["author"], "Team_UnLimbited")
        real = openscad.render; openscad.render = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must come from the cache"))
        try: path2, cached2 = armgen.generate_part("unlimbited_arm", defs, cache_dir=d)
        finally: openscad.render = real
        self.assertTrue(cached2); self.assertEqual(path, path2)
        other, _ = armgen.generate_part("unlimbited_arm", {**defs, "HandLen": 160}, cache_dir=d); self.assertNotEqual(other.parent, path.parent)   # other measures -> other cache entry

    def test_left_and_right_palms_are_mirrors(self):
        import numpy as np
        d = tempfile.mkdtemp(prefix="armcache_"); L = armgen.generate_part("unlimbited_arm", compute_sizing("unlimbited_arm", "left", "Palm", ArmSizing.OK).scad_defines, cache_dir=d)[0]
        R = armgen.generate_part("unlimbited_arm", compute_sizing("unlimbited_arm", "right", "Palm", ArmSizing.OK).scad_defines, cache_dir=d)[0]
        a = np.array(read_stl(L)).reshape(-1, 3) * [-1, 1, 1]; b = np.array(read_stl(R)).reshape(-1, 3)
        self.assertLess(float(np.abs(np.sort(a, axis=0) - np.sort(b, axis=0)).max()), 5e-4)

    def test_missing_scad_gives_a_clear_error(self):
        real = armgen.scad_path; armgen.scad_path = lambda prof: None
        try:
            with self.assertRaises(RuntimeError) as cm: armgen.generate_part("unlimbited_arm", {"part": "Palm"}, cache_dir=tempfile.mkdtemp())
        finally: armgen.scad_path = real
        self.assertIn("SCAD", str(cm.exception)); self.assertIn("Thingiverse", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
