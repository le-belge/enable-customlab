"""Non-regression tests for audit findings 2 and 3 (3 November 2026).

3: in a multicolour export, the STL of colour 1 must be at the requested scale (it used to be rewritten at 100 %).
2: supplied parts that are not watertight (Phoenix Palm / Fingers) are detected on loading, engraving is greyed out,
   the export sheet says "source_watertight": false, and OpenSCAD / manifold errors are explained in plain language.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["CUSTOMLAB_SYNC"] = "1"
import numpy as np

from customlab import deco, export_all, messages as M
from customlab.meshio import bbox, read_stl, write_stl
from tests.test_deco import slab

BUNDLED = Path(deco.__file__).parent / "bundled_parts" / "phoenix_jesimon_100pct" / "left" / "files"


def _bundled(word):
    return next(iter(sorted(BUNDLED.glob(f"*{word}*.stl"))), None)


def _two_colour_png(folder):
    from PySide6.QtGui import QColor, QImage
    deco._ensure_qt(); im = QImage(200, 200, QImage.Format_RGB32); im.fill(QColor("white"))
    for x in range(20, 100):
        for y in range(20, 180): im.setPixelColor(x, y, QColor(16, 72, 127))
    for x in range(110, 180):
        for y in range(20, 180): im.setPixelColor(x, y, QColor(207, 39, 51))
    f = Path(folder) / "logo.png"; im.save(str(f), "PNG"); return f


class Colour1Scale(unittest.TestCase):
    """Finding 3: every colour STL keeps the requested scale, colour 1 included."""
    def test_each_colour_stl_is_at_the_export_scale(self):
        with tempfile.TemporaryDirectory() as d:
            part = Path(d) / "s.stl"; slab(part); png = _two_colour_png(d); hm = deco.build_heightmap(read_stl(part), "+z", 0.25)
            for mode in ("relief", "inlay"):
                s = deco.DecoSpec(kind="image", path=str(png), size_mm=30, u=30, v=30, depth_mm=1.0, mode=mode, ncolors=2)
                r = deco.apply_decoration(part, s, hm=hm); self.assertEqual(r.errors, []); self.assertEqual(len(r.layers), 2)
                out = deco.export_result(r, part, s, Path(d) / f"out_{mode}", scale_percent=150)
                for n, L in enumerate(r.layers, start=2):
                    f = next(out.parent.glob(f"*_{n}_EXPERIMENTAL_*.stl"))
                    lo, hi = (np.array(x) for x in bbox(read_stl(f))); lo0, hi0 = (np.array(x) for x in bbox(L["triangles"]))
                    np.testing.assert_allclose(lo, lo0 * 1.5, atol=1e-3, err_msg=f"{mode} colour {n - 1}")
                    np.testing.assert_allclose(hi, hi0 * 1.5, atol=1e-3, err_msg=f"{mode} colour {n - 1}")
                meta = json.loads((out.parent / (out.stem + ".json")).read_text(encoding="utf-8"))
                self.assertEqual(meta["triangles"], len(r.layers[0]["triangles"]))


class SourceWatertight(unittest.TestCase):
    """Finding 2: original-file defects are reported (never repaired)."""
    def test_export_sheet_and_guide_flag_a_non_watertight_source(self):
        with tempfile.TemporaryDirectory() as d:
            good = Path(d) / "src" / "good.stl"; good.parent.mkdir(); slab(good)
            bad = Path(d) / "src" / "bad.stl"; write_stl(bad, read_stl(good)[:-1])          # one face missing: open mesh
            s = deco.DecoSpec(kind="text", text="L", size_mm=20, u=30, v=30, depth_mm=1.0, mode="relief")
            for part, expected in ((good, True), (bad, False)):
                r = deco.apply_decoration(part, s); self.assertEqual(r.errors, [])
                out = deco.export_result(r, part, s, Path(d) / part.stem)
                meta = json.loads((out.parent / (out.stem + ".json")).read_text(encoding="utf-8"))
                self.assertIs(meta["source_watertight"], expected)
                guide = next(out.parent.glob("*_LISEZ-MOI_Bambu.txt")).read_text(encoding="utf-8")
                self.assertEqual("Réparer le modèle" in guide, not expected)
                export_all._plain(part, Path(d) / ("plain_" + part.stem), False, 120, {})
                plain = json.loads(next((Path(d) / ("plain_" + part.stem)).glob("*.json")).read_text(encoding="utf-8"))
                self.assertIs(plain["source_watertight"], expected)
            self.assertEqual(read_stl(bad), read_stl(good)[:-1])                              # the source file is left untouched

    def test_messages_explain_openscad_and_manifold_errors(self):
        sev, fr, ok = M.localize("OpenSCAD failed: ERROR: CGAL error in CGAL_Nef_polyhedron3(): The given mesh is not closed / not 2-manifold", "fr")
        self.assertTrue(ok); self.assertEqual(sev, M.BLOCK); self.assertIn("Réparer le modèle", fr); self.assertIn("fichier d'origine", fr)
        sev, en, ok = M.localize("OpenSCAD failed: Parser error in line 3", "en")
        self.assertTrue(ok); self.assertEqual(sev, M.BLOCK); self.assertIn("OpenSCAD could not compute", en); self.assertIn("Parser error in line 3", en)
        sev, fr, _ = M.localize(deco.SOURCE_NOT_WATERTIGHT, "fr"); self.assertEqual(sev, M.CHECK); self.assertIn("clic droit > Réparer le modèle", fr)
        _, en, _ = M.localize(deco.SOURCE_NOT_WATERTIGHT, "en"); self.assertIn("Repair model", en)
        _, fr, _ = M.localize("Gravure impossible : cette pièce n'est pas étanche/manifold", "fr"); self.assertTrue(fr.startswith("Gravure impossible sur cette pièce"))   # older rule still wins

    @unittest.skipUnless(_bundled("Palm") and _bundled("Box"), "pièces Phoenix embarquées absentes")
    def test_loading_bundled_palm_and_fingers_greys_out_engraving(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from customlab.placement import CustomizePage
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": d}):
            c = CustomizePage("fr"); c.mode.setCurrentIndex(c.mode.findData("engrave"))
            for word in ("Palm", "Fingers"):
                c.set_part(str(_bundled(word)))
                self.assertFalse(c.source_watertight, word)
                self.assertFalse(c.mode.model().item(c.mode.findData("engrave")).isEnabled(), word)
                self.assertEqual(c.mode.currentData(), "relief")                              # engraving left for relief
                self.assertIn("Réparer le modèle", c.prov.text())
            c.retranslate("en"); self.assertFalse(c.mode.model().item(c.mode.findData("engrave")).isEnabled()); self.assertIn("Repair model", c.prov.text())
            c.set_part(str(_bundled("Box")))
            self.assertTrue(c.source_watertight); self.assertTrue(c.mode.model().item(c.mode.findData("engrave")).isEnabled())
            self.assertNotIn("Repair model", c.prov.text())


if __name__ == "__main__":
    unittest.main()
