"""Checks against the OFFICIAL Team UnLimbited SCAD (thing:1674320), supplied locally by the user (not embedded).

Skipped when sources/phoenix_scad/... or OpenSCAD is absent. These tests are what justify applying the e-NABLE France scale
to the Phoenix STL files: the SCAD scales every part uniformly (HandPerc/100) and the right hand is its X mirror.
"""
import glob
import tempfile
import unittest
from pathlib import Path

import numpy as np

from customlab import openscad
from customlab.meshio import read_stl, volume
from customlab.meshscale import scale_stl_python

ROOT = Path(__file__).parent.parent
SCAD = ROOT / "sources/phoenix_scad/thing_1674320/files/UnLimbitedPhoenix.scad"
JES = ROOT / "customlab/bundled_parts/phoenix_jesimon_100pct"
KEYS = {"Palm": "Palm2017", "Box": "Box2017", "TPins": "TPins2017", "Fingers": "Fingers2017", "Phalanx": "Phalanx2017", "Pins": "_Pins2017"}


def vertex_set_gap(a, b):
    """Largest distance from a vertex of one mesh to the nearest vertex of the other (both ways): insensitive to triangle count,
    which differs when OpenSCAD drops degenerate triangles after scaling."""
    A = np.unique(np.round(np.array(a).reshape(-1, 3), 4), axis=0); B = np.unique(np.round(np.array(b).reshape(-1, 3), 4), axis=0)
    def one_way(P, Q):
        worst = 0.0
        for i in range(0, len(P), 500): worst = max(worst, float(np.sqrt(((P[i:i + 500, None, :] - Q[None]) ** 2).sum(2)).min(1).max()))
        return worst
    return max(one_way(A, B), one_way(B, A))


def max_vertex_gap(a, b):
    A = np.array(a).reshape(-1, 3); B = np.array(b).reshape(-1, 3)
    if len(A) != len(B): return float("inf")
    return float(np.abs(A[np.lexsort(A.T[::-1])] - B[np.lexsort(B.T[::-1])]).max())


@unittest.skipUnless(SCAD.is_file() and openscad.find_openscad(), "official SCAD or OpenSCAD not available locally")
class OfficialScad(unittest.TestCase):
    def render(self, part, side, perc):
        d = tempfile.mkdtemp(prefix="scadtest_")
        return read_stl(openscad.render(SCAD, Path(d) / "o.stl", {"part": part, "LeftRight": side, "HandPerc": perc}, timeout=300))

    def jes(self, part, side): return glob.glob(str(JES / side.lower() / "files" / f"*{KEYS[part]}*.stl"))[0]

    def test_scad_at_100_equals_the_customizer_files(self):
        for part in KEYS:
            for side in ("Left", "Right"):
                gap = max_vertex_gap(self.render(part, side, 100), read_stl(self.jes(part, side)))
                self.assertLess(gap, 5e-4, (part, side, gap))

    def test_uniform_stl_scaling_equals_the_scad_at_other_scales(self):
        for part in ("Fingers", "Phalanx", "Pins", "Box"):
            d = tempfile.mkdtemp(); out = Path(d) / "s.stl"; scale_stl_python(self.jes(part, "Left"), out, 137.5)
            got = self.render(part, "Left", 137.5); ref = read_stl(out)
            self.assertLess(vertex_set_gap(got, ref), 5e-3, part); self.assertAlmostEqual(volume(got), volume(ref), delta=1e-4 * abs(volume(ref)))

    def test_right_hand_is_the_x_mirror(self):
        L = np.array(self.render("Palm", "Left", 110)).reshape(-1, 3); R = np.array(self.render("Palm", "Right", 110)).reshape(-1, 3)
        self.assertLess(float(np.abs(np.sort(L * [-1, 1, 1], axis=0) - np.sort(R, axis=0)).max()), 5e-4)

    def test_sizing_defines_are_the_real_scad_parameters(self):
        from customlab.profiles import compute_phoenix_sizing
        r = compute_phoenix_sizing("right", "Palm", 40); self.assertEqual(set(r.scad_defines), {"HandPerc", "LeftRight", "part"})
        got = read_stl(openscad.render(SCAD, Path(tempfile.mkdtemp()) / "o.stl", r.scad_defines, timeout=300))
        ref = self.render("Palm", "Right", 104.65); self.assertAlmostEqual(volume(got), volume(ref), places=1)


if __name__ == "__main__":
    unittest.main()
