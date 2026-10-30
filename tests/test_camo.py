import os
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("CUSTOMLAB_SYNC", "1")
from PySide6.QtWidgets import QApplication
from customlab import camo, camo_batch, deco
from customlab.meshio import read_stl
from tests.test_deco import slab


def spec(**kw): return deco.DecoSpec(**{**dict(kind="camo", mode="inlay", depth_mm=0.6, axis="+z", camo_style="fr", camo_seed=1, camo_scale_mm=20.0, res_mm=0.5, protect_margin_mm=2.0), **kw})


class CamoMasks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.f = Path(self.d.name) / "s.stl"; slab(self.f, w=80, l=80, t=6); self.hm = deco.build_heightmap(read_stl(self.f), "+z", 0.5)

    def tearDown(self): self.d.cleanup()

    def test_layers_are_disjoint_deterministic_and_share_the_palette(self):
        m1, l1 = deco.render_spec_masks(spec(), self.hm); m2, l2 = deco.render_spec_masks(spec(), self.hm)
        self.assertEqual([h for h, _, _ in l1], [h for h, _, _ in l2]); self.assertTrue(all(np.array_equal(a[2], b[2]) for a, b in zip(l1, l2)))
        self.assertEqual({h for h, _, _ in l1}, {"#5B6236", "#6B4A2E", "#1E1E1C"})
        total = sum(int(m.sum()) for _, _, m in l1); self.assertEqual(total, int(m1.sum()))                       # disjoint: sizes add up to the union
        valid = deco.camo_valid_mask(spec(), self.hm); self.assertFalse((m1 & ~valid).any())
        self.assertGreater(total / valid.sum(), 0.4); self.assertLess(total / valid.sum(), 0.8)                   # ~67 % of the surface is coloured, the rest is the base
        _, l3 = deco.render_spec_masks(spec(camo_seed=2), self.hm); self.assertFalse(all(np.array_equal(a[2], b[2]) for a, b in zip(l1, l3)))
        _, lw = deco.render_spec_masks(spec(camo_style="winter"), self.hm); self.assertEqual({h for h, _, _ in lw}, {"#C5CBD0", "#8D969E", "#4B5259"})

    def test_zones_protected_cells_and_edges_stay_clear(self):
        zone = (20.0, 20.0, 50.0, 50.0); m, _ = deco.render_spec_masks(spec(), self.hm, None, [zone])
        ii, jj = np.nonzero(m); cu = self.hm.u0 + (ii + 0.5) * self.hm.res; cv = self.hm.v0 + (jj + 0.5) * self.hm.res
        self.assertFalse(((cu >= 20) & (cu <= 50) & (cv >= 20) & (cv <= 50)).any())
        self.assertGreater(cu.min(), 0.9); self.assertLess(cu.max(), 79.1)                                          # 1 mm from the part's edge
        prot = np.zeros(m.shape, bool); prot[40:80, 40:80] = True; m2, _ = deco.render_spec_masks(spec(), self.hm, prot, ())
        self.assertFalse((m2 & prot).any())

    def test_engraving_is_refused_and_nothing_decorable_is_reported(self):
        with self.assertRaises(deco.DecoError): deco.render_spec_masks(spec(mode="engrave"), self.hm)
        prot = np.ones((self.hm.shape[0] - 1, self.hm.shape[1] - 1), bool)
        with self.assertRaises(deco.DecoError): deco.render_spec_masks(spec(), self.hm, prot, ())

    def test_full_pipeline_gives_one_piece_per_colour_and_a_bambu_file(self):
        r = deco.apply_decoration(self.f, spec()); self.assertEqual(r.errors, []); self.assertEqual(len(r.layers), 3)
        out = deco.export_result(r, self.f, spec(), Path(self.d.name) / "out")
        z = list(Path(out).parent.glob("*_Bambu_pret.3mf")); self.assertEqual(len(z), 1)
        with zipfile.ZipFile(z[0]) as zf: self.assertTrue(any(n.endswith(".model") for n in zf.namelist()))


class Batch(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_batch_exports_each_part_skips_refused_scales_and_writes_a_summary(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a, b = d / "a.stl", d / "b.stl"; slab(a, w=80, l=80, t=6); slab(b, w=90, l=70, t=6)
            ctx = {"mirror_for": lambda p: False, "scale_for": lambda p: (None, "Échelle 120 % hors de la plage documentée.") if Path(p).name == "b.stl" else (80.0, None), "extra": lambda: {"device": "test"}}
            seen = []; res = camo_batch.run([("A", a), ("B", b)], spec(), d / "out", ctx, progress=lambda i, n, m: seen.append((i, n, m)))
            self.assertEqual([(r["part"], r["status"]) for r in res], [("A", "ok"), ("B", "skipped")]); self.assertIn("hors de la plage", res[1]["message"])
            self.assertTrue(list((d / "out" / "a").glob("*_Bambu_pret.3mf"))); self.assertFalse((d / "out" / "b").exists())
            self.assertTrue((d / "out" / "RECAP_camouflage.txt").is_file()); self.assertIn("skipped", (d / "out" / "RECAP_camouflage.txt").read_text())
            self.assertEqual(seen[-1][0], 2)

    def test_variant_changes_per_part_and_cancel_stops(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a, b = d / "a.stl", d / "b.stl"; slab(a, w=80, l=80, t=6); slab(b, w=80, l=80, t=6)
            ctx = {"mirror_for": lambda p: False, "scale_for": lambda p: (None, None), "extra": lambda: {}}
            res = camo_batch.run([("A", a), ("B", b)], spec(camo_seed=5), d / "o1", ctx); self.assertIn("variante 5", res[0]["message"]); self.assertIn("variante 6", res[1]["message"])
            res = camo_batch.run([("A", a), ("B", b)], spec(), d / "o2", ctx, cancelled=lambda: True); self.assertEqual(res, [])


if __name__ == "__main__":
    unittest.main()


class FilamentConfig(unittest.TestCase):
    def test_3mf_declares_one_filament_per_piece_with_the_motif_colours(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); f = d / "s.stl"; slab(f, w=80, l=80, t=6); r = deco.apply_decoration(f, spec())
            out = deco.export_result(r, f, spec(), d / "o"); z = list((Path(out).parent).glob("*_Bambu_pret.3mf"))[0]
            with zipfile.ZipFile(z) as zf: cfg = json.loads(zf.read("Metadata/project_settings.config"))
            self.assertEqual(cfg["filament_colour"], ["#FFFFFF"] + [l["hex"] for l in r.layers]); self.assertEqual(len(cfg["filament_diameter"]), 4)
