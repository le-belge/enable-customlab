import tempfile
import unittest
from pathlib import Path

import numpy as np

from customlab import deco, export_all
from customlab.meshio import read_stl
from tests.test_deco import slab


def extent(p): return np.ptp(np.asarray(read_stl(p), float).reshape(-1, 3), axis=0)


class ExportAll(unittest.TestCase):
    def test_every_part_at_the_same_scale_the_customised_one_decorated_refused_scale_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a, b, c = d / "a.stl", d / "b.stl", d / "c.stl"
            slab(a, w=80, l=80, t=6); slab(b, w=90, l=70, t=6); slab(c, w=50, l=50, t=6)
            ctx = {"mirror_for": lambda p: False, "extra": lambda: {"device": "test"},
                   "scale_for": lambda p: (None, "Échelle 30 % hors de la plage documentée.") if Path(p).name == "c.stl" else (60.0, None)}
            spec = deco.DecoSpec(kind="text", text="A", mode="relief", depth_mm=0.6, axis="+z", size_mm=20, u=40.0, v=40.0, res_mm=0.5, protect_margin_mm=0)
            res = export_all.run([("A", a), ("B", b), ("C", c)], (a, spec, []), d / "out", ctx)
            self.assertEqual([r["status"] for r in res], ["ok", "ok", "skipped"]); self.assertIn("décorée", res[0]["message"]); self.assertIn("non décorée", res[1]["message"])
            pa = next((d / "out" / "a").glob("*_EXPERIMENTAL_deco.stl")); self.assertAlmostEqual(extent(pa)[0], 48.0, delta=0.2)     # 80 mm x 60 %
            pb = next((d / "out" / "b").glob("b_60pct.stl")); self.assertAlmostEqual(extent(pb)[0], 54.0, delta=0.2)                    # 90 mm x 60 %
            self.assertTrue(list((d / "out" / "b").glob("*_ATTRIBUTION.txt"))); self.assertFalse((d / "out" / "c").exists())
            self.assertIn("skipped", (d / "out" / "RECAP_export.txt").read_text())


if __name__ == "__main__": unittest.main()
