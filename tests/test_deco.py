import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np

from customlab import deco, openscad
from customlab.licenseinfo import read_license_info
from customlab.meshio import bbox, is_watertight, read_stl, volume, write_stl

ROOT = Path(__file__).parent.parent
JES = ROOT / "sources/phoenix_nih_linked_100pct_20261022/left"
STAR = ROOT / "examples/star.svg"


def slab(path, w=60.0, l=60.0, t=5.0, ramp=0.0):
    """Closed box 'part' (watertight). ramp tilts the top face (w grows with u)."""
    v = {(x, y, z): (x * w, y * l, z * t + (x * ramp if z else 0)) for x in (0, 1) for y in (0, 1) for z in (0, 1)}
    V = lambda x, y, z: v[(x, y, z)]
    f = [((0,0,0),(0,1,0),(1,1,0)),((0,0,0),(1,1,0),(1,0,0)),((0,0,1),(1,0,1),(1,1,1)),((0,0,1),(1,1,1),(0,1,1)),
         ((0,0,0),(1,0,0),(1,0,1)),((0,0,0),(1,0,1),(0,0,1)),((1,0,0),(1,1,0),(1,1,1)),((1,0,0),(1,1,1),(1,0,1)),
         ((1,1,0),(0,1,0),(0,1,1)),((1,1,0),(0,1,1),(1,1,1)),((0,1,0),(0,0,0),(0,0,1)),((0,1,0),(0,0,1),(0,1,1))]
    write_stl(path, [tuple(V(*p) for p in tri) for tri in f])


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Core(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.part = Path(self.d.name) / "slab.stl"; slab(self.part)
        self.tris = read_stl(self.part); self.hm = deco.build_heightmap(self.tris, "+z", 0.25)

    def tearDown(self): self.d.cleanup()

    def test_heightmap_flat_top(self):
        ok = ~np.isnan(self.hm.H)
        self.assertTrue(np.allclose(self.hm.H[ok], 5.0, atol=1e-6)); self.assertAlmostEqual(self.hm.thickness_w, 5.0)

    def test_axis_rotations_are_right_handed(self):
        for a, R in deco.AXES.items(): self.assertAlmostEqual(np.linalg.det(np.array(R, float)), 1.0)

    def test_text_relief_on_slab(self):
        s = deco.DecoSpec(kind="text", text="Léo", size_mm=30, u=30, v=30, depth_mm=0.6)
        r = deco.apply_decoration(self.part, s, hm=self.hm)
        self.assertEqual(r.errors, []); self.assertTrue(is_watertight(r.deco_triangles))
        lo, hi = bbox(r.deco_triangles); self.assertAlmostEqual(hi[2], 5.6, places=3); self.assertAlmostEqual(lo[2], 4.6, places=3)
        self.assertGreater(volume(r.deco_triangles), 5)
        self.assertEqual(len(r.triangles), len(self.tris) + len(r.deco_triangles))

    def test_size_and_position_respected(self):
        s = deco.DecoSpec(kind="svg", path=str(STAR), size_mm=24, u=20, v=40, depth_mm=0.5)
        r = deco.apply_decoration(self.part, s, hm=self.hm); self.assertEqual(r.errors, [])
        lo, hi = bbox(r.deco_triangles)
        self.assertAlmostEqual((lo[0] + hi[0]) / 2, 20, delta=0.5); self.assertAlmostEqual((lo[1] + hi[1]) / 2, 40, delta=0.5)
        self.assertAlmostEqual(max(hi[0] - lo[0], hi[1] - lo[1]), 24, delta=0.6)

    def test_text_is_readable_not_mirrored(self):
        # 'L' must have its vertical bar on the left and foot at the bottom when viewed from +z
        s = deco.DecoSpec(kind="text", text="L", size_mm=30, u=30, v=30, depth_mm=0.6, bold=True)
        m = deco.render_mask(s, self.hm)
        ii, jj = np.nonzero(m); cu = ii.mean(); cv = jj.mean(); h = m.shape
        left_half = m[: int(cu), :].sum(); right_half = m[int(cu):, :].sum()
        bottom = m[:, : int(cv)].sum(); top = m[:, int(cv):].sum()
        self.assertGreater(left_half, right_half); self.assertGreater(bottom, top)

    def test_off_part_is_refused_not_clamped(self):
        s = deco.DecoSpec(kind="text", text="Léo", size_mm=30, u=55, v=30, depth_mm=0.6)
        r = deco.apply_decoration(self.part, s, hm=self.hm)
        self.assertTrue(r.errors); self.assertEqual(r.deco_triangles, [])

    def test_depth_limits_refused(self):
        for mode, d in (("relief", 2.5), ("relief", 0.05), ("engrave", 1.5)):
            r = deco.apply_decoration(self.part, deco.DecoSpec(kind="text", text="A", size_mm=10, u=30, v=30, depth_mm=d, mode=mode), hm=self.hm)
            self.assertTrue(any("Profondeur" in e or "Gravure" in e for e in r.errors), (mode, d))

    def test_exclusion_zone_blocks(self):
        s = deco.DecoSpec(kind="text", text="Léo", size_mm=20, u=30, v=30, depth_mm=0.6)
        r = deco.apply_decoration(self.part, s, zones=[(25, 25, 35, 35)], hm=self.hm)
        self.assertTrue(any("zone interdite" in e for e in r.errors))
        r = deco.apply_decoration(self.part, s, zones=[(0, 0, 8, 8)], hm=self.hm); self.assertEqual(r.errors, [])

    def test_steep_slope_refused(self):
        p = Path(self.d.name) / "ramp.stl"; slab(p, ramp=120.0)       # ~63 deg top
        r = deco.apply_decoration(p, deco.DecoSpec(kind="text", text="A", size_mm=10, u=30, v=30), res=0.25)
        self.assertTrue(any("Pente" in e for e in r.errors))

    def test_image_threshold(self):
        from PySide6.QtGui import QColor, QGuiApplication, QImage
        deco._ensure_qt(); im = QImage(40, 40, QImage.Format_RGB32); im.fill(QColor("white"))
        for x in range(10, 30):
            for y in range(10, 30): im.setPixelColor(x, y, QColor("black"))
        f = Path(self.d.name) / "sq.png"; im.save(str(f))
        r = deco.apply_decoration(self.part, deco.DecoSpec(kind="image", path=str(f), size_mm=20, u=30, v=30, depth_mm=0.6), hm=self.hm)
        self.assertEqual(r.errors, []); lo, hi = bbox(r.deco_triangles)
        self.assertAlmostEqual(hi[0] - lo[0], 20, delta=0.6)       # size = drawn content (black square), white page ignored
        self.assertAlmostEqual(volume(r.deco_triangles), 20 * 20 * (0.6 + 0.4), delta=12)  # relief + embedded part

    def test_engrave_refused_on_open_mesh(self):
        t = self.tris[:-2]; p = Path(self.d.name) / "open.stl"; write_stl(p, t)
        r = deco.apply_decoration(p, deco.DecoSpec(kind="text", text="A", size_mm=10, u=30, v=30, mode="engrave", depth_mm=0.5))
        self.assertTrue(any("étanche" in e for e in r.errors) or r.errors)

    @unittest.skipUnless(openscad.find_openscad(), "OpenSCAD missing")
    def test_engrave_removes_volume(self):
        s = deco.DecoSpec(kind="text", text="Léo", size_mm=30, u=30, v=30, depth_mm=0.8, mode="engrave")
        r = deco.apply_decoration(self.part, s, hm=self.hm); self.assertEqual(r.errors, [])
        v0, v1 = volume(self.tris), volume(r.triangles)
        self.assertLess(v1, v0); self.assertAlmostEqual(v0 - v1, 0.8 * (r.info["cells"] * 0.25 ** 2), delta=0.08 * (v0 - v1))
        self.assertTrue(is_watertight(r.triangles))


class Export(unittest.TestCase):
    def test_export_keeps_original_and_writes_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"; src.mkdir(); part = src / "p.stl"; slab(part)
            (src / "README.txt").write_text("Phoenix Hand (Left) - 100% Scale by jesimon is licensed under the Creative Commons - Attribution - Non-Commercial license.\n"
                                            "http://creativecommons.org/licenses/by-nc/3.0/\nCustomized version of http://www.thingiverse.com/thing:1674320\n")
            (src / "LICENSE.txt").write_text("x")
            before = sha(part); s = deco.DecoSpec(kind="text", text="Léo", size_mm=20, u=30, v=30)
            r = deco.apply_decoration(part, s)
            out = deco.export_result(r, part, s, Path(d) / "out", zones=[(0, 0, 5, 5)], scale_percent=None)
            self.assertEqual(sha(part), before); self.assertTrue(out.name.endswith("_EXPERIMENTAL_deco.stl"))
            meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(meta["source_license"]["license"], "Creative Commons - Attribution - Non-Commercial")
            self.assertTrue(meta["source_license"]["non_commercial"]); self.assertEqual(meta["source_sha256"], before)
            self.assertIn("EXPÉRIMENTALE", meta["disclaimer"].upper()) if False else self.assertIn("EXPÉRIMENTALE", meta["disclaimer"])
            self.assertIn("NON COMMERCIAL", (out.parent / (out.stem + "_ATTRIBUTION.txt")).read_text(encoding="utf-8"))
            self.assertEqual(len(read_stl(out)), len(r.triangles))
            with self.assertRaises(deco.DecoError): deco.export_result(r, part, s, src)            # never beside the original

    def test_scale_only_when_requested(self):
        with tempfile.TemporaryDirectory() as d:
            part = Path(d) / "p.stl"; slab(part); r = deco.apply_decoration(part, deco.DecoSpec(kind="text", text="A", size_mm=10, u=30, v=30))
            a = deco.export_result(r, part, deco.DecoSpec(), Path(d) / "o1"); b = deco.export_result(r, part, deco.DecoSpec(), Path(d) / "o2", scale_percent=110)
            self.assertAlmostEqual(bbox(read_stl(b))[1][0], 1.1 * bbox(read_stl(a))[1][0], places=3)

    def test_unknown_provenance_reported(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.stl"; slab(p); self.assertFalse(read_license_info(p)["known"])

    @unittest.skipUnless((JES / "LICENSE.txt").exists(), "jesimon archive not present")
    def test_real_archive_license(self):
        f = next((JES / "files").glob("*Palm*.stl")); i = read_license_info(f)
        self.assertEqual(i["license"], "Creative Commons - Attribution - Non-Commercial"); self.assertTrue(i["non_commercial"])
        self.assertEqual(i["author"], "jesimon"); self.assertIn("1674320", i["derived_from"])

    @unittest.skipUnless((JES / "LICENSE.txt").exists(), "jesimon archive not present")
    def test_real_palm_relief_original_untouched(self):
        f = next((JES / "files").glob("*Palm*.stl")); before = sha(f)
        hm = deco.build_heightmap(read_stl(f), "+z", 0.25)
        s = deco.DecoSpec(kind="text", text="Léo", size_mm=22, u=54.3, v=-116.5, depth_mm=0.5)
        r = deco.apply_decoration(f, s, hm=hm); self.assertEqual(r.errors, [])
        self.assertEqual(sha(f), before); self.assertTrue(is_watertight(r.deco_triangles))
        e = deco.apply_decoration(f, deco.DecoSpec(kind="text", text="Léo", size_mm=22, u=54.3, v=-116.5, mode="engrave"), hm=hm)
        self.assertTrue(any("étanche" in x for x in e.errors))      # Palm is not manifold -> engraving refused


class Library(unittest.TestCase):
    def test_scan_synthetic(self):
        from customlab import library
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "set" / "left" / "files"; a.mkdir(parents=True); slab(a / "unlimbitedphoenix_Palm20170317-1-x-0.stl")
            (Path(d) / "set" / "left" / "README.txt").write_text("T by Au is licensed under the Creative Commons - Attribution - Non-Commercial license.\nhttp://creativecommons.org/licenses/by-nc/3.0/\n")
            (Path(d) / "set" / "left" / "LICENSE.txt").write_text("x")
            items = library.scan(d); self.assertEqual(len(items), 1)
            self.assertEqual((items[0]["part"], items[0]["side"]), ("Palm", "left")); self.assertTrue(items[0]["license"]["non_commercial"])
            self.assertEqual(library.scan(Path(d) / "absent"), [])

    def test_bundled_parts_ship_with_their_licence(self):
        from customlab import library
        b = library.BUNDLED_ROOT / "phoenix_jesimon_100pct"
        for side in ("left", "right"):
            for n in ("LICENSE.txt", "README.txt", "SOURCES.txt"): self.assertTrue((b / side / n).is_file(), (side, n))
            self.assertEqual(len(list((b / side / "files").glob("*.stl"))), 8)
        self.assertIn("NON COMMERCIAL", (library.BUNDLED_ROOT / "NOTICE.txt").read_text(encoding="utf-8"))
        its = library.scan(library.BUNDLED_ROOT, bundled=True)
        self.assertEqual(len(its), 16); self.assertTrue(all(i["license"]["non_commercial"] and i["bundled"] for i in its))

    @unittest.skipUnless((JES / "LICENSE.txt").exists(), "jesimon archive not present")
    def test_scan_real_sources(self):
        from customlab import library
        items = [i for i in library.scan_all() if i["device"] == "phoenix_hand"]; self.assertEqual(len(items), 16)   # bundled + identical sources/ files listed once
        self.assertTrue(all(i["license"]["known"] and i["license"]["non_commercial"] for i in items))


if __name__ == "__main__":
    unittest.main()


class WhiteEmpty(unittest.TestCase):
    def test_white_shapes_are_holes_by_default(self):
        d = tempfile.TemporaryDirectory(); part = Path(d.name) / "s.stl"; slab(part); hm = deco.build_heightmap(read_stl(part), "+z", 0.25)
        svg = Path(d.name) / "w.svg"; svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#000"/><rect x="40" y="40" width="20" height="20" fill="#fff"/></svg>')
        a = deco.render_mask(deco.DecoSpec(kind="svg", path=str(svg), size_mm=30, u=30, v=30), hm)
        b = deco.render_mask(deco.DecoSpec(kind="svg", path=str(svg), size_mm=30, u=30, v=30, white_is_empty=False), hm)
        self.assertLess(a.sum(), b.sum()); self.assertAlmostEqual(b.sum() - a.sum(), (6.0 * 6.0) / 0.0625, delta=0.1 * (36 / 0.0625))   # 20 % of 30 mm = 6 mm square hole
        d.cleanup()


class Raster(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.part = Path(self.d.name) / "s.stl"; slab(self.part)
        self.hm = deco.build_heightmap(read_stl(self.part), "+z", 0.25)

    def tearDown(self): self.d.cleanup()

    def _img(self, name, fmt="PNG"):
        from PySide6.QtGui import QColor, QImage
        deco._ensure_qt(); im = QImage(100, 100, QImage.Format_RGB32); im.fill(QColor("white"))
        for x in range(10, 40):
            for y in range(10, 90): im.setPixelColor(x, y, QColor(0, 40, 120))          # dark blue bar (like a club colour)
        for x in range(60, 90):
            for y in range(10, 90): im.setPixelColor(x, y, QColor(200, 30, 40))         # red bar
        f = Path(self.d.name) / name; im.save(str(f), fmt, 90); return f

    def test_threshold_selects_colours(self):
        f = self._img("c.png")
        lo = deco.render_mask(deco.DecoSpec(kind="image", path=str(f), size_mm=30, u=30, v=30, threshold=60), self.hm).sum()    # blue only
        hi = deco.render_mask(deco.DecoSpec(kind="image", path=str(f), size_mm=30, u=30, v=30, threshold=200), self.hm).sum()   # blue + red
        self.assertGreater(hi, lo * 1.5); self.assertGreater(lo, 0)

    def test_jpeg_artifacts_do_not_break_the_mask(self):
        png, jpg = self._img("c.png", "PNG"), self._img("c.jpg", "JPEG")
        a = deco.render_mask(deco.DecoSpec(kind="image", path=str(png), size_mm=30, u=30, v=30, threshold=200), self.hm)
        b = deco.render_mask(deco.DecoSpec(kind="image", path=str(jpg), size_mm=30, u=30, v=30, threshold=200), self.hm)
        self.assertLess(abs(int(a.sum()) - int(b.sum())) / a.sum(), 0.05)
        r = deco.apply_decoration(self.part, deco.DecoSpec(kind="image", path=str(jpg), size_mm=30, u=30, v=30, threshold=200, depth_mm=1.0, mode="inlay"), hm=self.hm)
        self.assertEqual(r.errors, []); self.assertTrue(is_watertight(r.deco_triangles))


class ColourSeparation(unittest.TestCase):
    def setUp(self):
        from PySide6.QtGui import QColor, QImage
        deco._ensure_qt(); self.d = tempfile.TemporaryDirectory(); self.part = Path(self.d.name) / "s.stl"; slab(self.part)
        self.hm = deco.build_heightmap(read_stl(self.part), "+z", 0.25)
        im = QImage(200, 200, QImage.Format_RGB32); im.fill(QColor("white"))
        for x in range(20, 100):
            for y in range(20, 180): im.setPixelColor(x, y, QColor(16, 72, 127))        # blue
        for x in range(110, 180):
            for y in range(20, 180): im.setPixelColor(x, y, QColor(207, 39, 51))        # red
        for x in range(100, 110):
            for y in range(20, 180): im.setPixelColor(x, y, QColor(230, 235, 240))      # pale gap (white-ish)
        self.png = Path(self.d.name) / "logo.png"; im.save(str(self.png), "PNG"); self.jpg = Path(self.d.name) / "logo.jpg"; im.save(str(self.jpg), "JPEG", 80)

    def tearDown(self): self.d.cleanup()

    def spec(self, path, **k): return deco.DecoSpec(**{**dict(kind="image", path=str(path), size_mm=30, u=30, v=30, depth_mm=1.0, mode="inlay", ncolors=2), **k})

    def test_two_colours_disjoint_and_white_is_empty(self):
        for f in (self.png, self.jpg):
            union, layers = deco.render_spec_masks(self.spec(f), self.hm)
            self.assertEqual(len(layers), 2)
            rgbs = sorted(c for _, c, _ in layers); self.assertTrue(all(abs(x - y) <= 6 for x, y in zip(rgbs[0], (16, 72, 127))))   # blue
            self.assertTrue(all(abs(x - y) <= 6 for x, y in zip(rgbs[1], (207, 39, 51))))                                   # red
            a, b = layers[0][2], layers[1][2]; self.assertFalse((a & b).any())             # no overlap between pieces
            self.assertTrue(((a | b) == union).all())
            # the pale gap must not be filled: the two bars are separated by >= 8 cells
            ii = np.nonzero(a)[0]; jj = np.nonzero(b)[0]; self.assertGreater(abs(int(ii.mean()) - int(jj.mean())), 10)

    def test_pieces_are_watertight_and_flush(self):
        import dataclasses
        r = deco.apply_decoration(self.part, dataclasses.replace(self.spec(self.jpg), inlay_offset_mm=deco.INLAY_LEGACY_OFFSET_MM), hm=self.hm); self.assertEqual(r.errors, [])      # flush mode
        self.assertEqual(len(r.layers), 2)
        for L in r.layers:
            self.assertTrue(is_watertight(L["triangles"])); self.assertLessEqual(bbox(L["triangles"])[1][2], 5.0 + 1e-6)
        self.assertEqual(len(r.preview_colors), r.preview_highlight)

    def test_export_writes_base_plus_one_file_per_colour(self):
        s = self.spec(self.png); r = deco.apply_decoration(self.part, s, hm=self.hm)
        out = deco.export_result(r, self.part, s, Path(self.d.name) / "out"); files = sorted(p.name for p in out.parent.glob("*.stl"))
        self.assertEqual(len(files), 3); self.assertIn("_1_base_unmodified", files[0]); self.assertIn("_2_EXPERIMENTAL_incrustation_", files[1]); self.assertIn("_3_EXPERIMENTAL_incrustation_", files[2])
        meta = json.loads(next(out.parent.glob("*.json")).read_text(encoding="utf-8")); self.assertEqual(len(meta["color_pieces"]), 2)
        self.assertEqual([c["suggested_filament"] for c in meta["color_pieces"]], [1, 2])

    def test_one_colour_unchanged_behaviour(self):
        r = deco.apply_decoration(self.part, self.spec(self.png, ncolors=1), hm=self.hm); self.assertEqual(r.layers, [])


class Quality(unittest.TestCase):
    def test_smoothing_and_finer_grid_round_a_low_res_circle(self):
        from PySide6.QtGui import QColor, QImage, QPainter
        deco._ensure_qt(); d = tempfile.TemporaryDirectory(); part = Path(d.name) / "s.stl"; slab(part)
        im = QImage(60, 60, QImage.Format_RGB32); im.fill(QColor("white")); q = QPainter(im); q.setBrush(QColor("black")); q.setPen(QColor("black")); q.drawEllipse(3, 3, 54, 54); q.end()
        f = Path(d.name) / "c.png"; im.save(str(f))

        def rms(res, smooth):
            hm = deco.build_heightmap(read_stl(part), "+z", res)
            m = deco.render_mask(deco.DecoSpec(kind="image", path=str(f), size_mm=30, u=30, v=30, res_mm=res, smooth_source=smooth), hm)
            ii, jj = np.nonzero(m); cu = hm.u0 + (ii + 0.5) * hm.res; cv = hm.v0 + (jj + 0.5) * hm.res
            r = np.hypot(cu - cu.mean(), cv - cv.mean()); edge = r > r.max() - 0.6          # outer ring of boundary cells
            return float(np.std(r[edge])), float(m.sum() * hm.res ** 2)
        base, area0 = rms(0.25, False); fine, area1 = rms(0.15, True)
        self.assertLess(fine, base * 0.92, (base, fine))                   # measurably rounder boundary (already below nozzle width)
        self.assertAlmostEqual(area1, area0, delta=0.08 * area0)           # same shape size (no shrinking from smoothing)
        d.cleanup()

    def test_quality_levels_scale_triangle_count(self):
        d = tempfile.TemporaryDirectory(); part = Path(d.name) / "s.stl"; slab(part)
        n = {}
        for res in (0.25, 0.15):
            r = deco.apply_decoration(part, deco.DecoSpec(kind="svg", path=str(STAR), size_mm=24, u=30, v=30, depth_mm=1.0, mode="inlay", res_mm=res)); n[res] = len(r.deco_triangles)
        self.assertGreater(n[0.15], n[0.25] * 1.8); d.cleanup()


class AxisSuggestion(unittest.TestCase):
    def test_flat_face_is_found_on_any_axis(self):
        d = tempfile.mkdtemp(); f = Path(d) / "s.stl"; slab(f, w=60, l=40, t=5); t = read_stl(f)
        self.assertEqual(deco.suggest_axis(t)[0], "+z")                                             # large top face
        rot = [tuple((p[2], p[1], p[0]) for p in tri) for tri in t]                                    # swap x and z: the large faces now face +-x
        ax, sc = deco.suggest_axis(rot); self.assertIn(ax, ("+x", "-x")); self.assertGreater(sc[ax], 10 * sc["+z"])
        rot_y = [tuple((p[0], p[2], p[1]) for p in tri) for tri in t]; self.assertIn(deco.suggest_axis(rot_y)[0], ("+y", "-y"))

    def test_existing_phoenix_workflow_keeps_plus_z(self):
        if not (JES / "LICENSE.txt").exists(): self.skipTest("jesimon archive not present")
        for name in ("Palm", "Gauntlet"): self.assertEqual(deco.suggest_axis(read_stl(next((JES / "files").glob(f"*{name}*.stl"))))[0], "+z", name)

    def test_empty_scores_fall_back_to_plus_z(self):
        self.assertEqual(deco.suggest_axis([((0, 0, 0), (0, 0, 0), (0, 0, 0))])[0], "+z")


class Thin(unittest.TestCase):
    def test_thin_report(self):
        m = np.zeros((120, 120), bool); m[10:50, 10:50] = True            # 10 mm square at 0.25 mm: solid
        self.assertLess(deco.thin_feature_report(m, 0.25)["thin_fraction"], 0.01)
        m2 = np.zeros((120, 120), bool); m2[10:110:6, 10:110] = False; m2[10:12, 10:110] = True; m2[30:32, 10:110] = True   # 0.5 mm lines
        self.assertGreater(deco.thin_feature_report(m2, 0.25)["thin_fraction"], 0.9)
        m3 = np.ones((60, 60), bool); m3[:, 29:31] = False                # 0.5 mm slit inside a block
        self.assertGreater(deco.thin_feature_report(m3, 0.25)["narrow_gap_fraction"], 0.01)

    def test_warning_reaches_check_placement(self):
        d = tempfile.TemporaryDirectory(); part = Path(d.name) / "s.stl"; slab(part)
        hm = deco.build_heightmap(read_stl(part), "+z", 0.25)
        svg = Path(d.name) / "lines.svg"; svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="0" y="0" width="100" height="1.5"/><rect x="0" y="30" width="100" height="1.5"/><rect x="0" y="60" width="100" height="1.5"/><rect x="0" y="98.5" width="100" height="1.5"/></svg>')
        m = deco.render_mask(deco.DecoSpec(kind="svg", path=str(svg), size_mm=40, u=30, v=30), hm)
        e, w, i = deco.check_placement(hm, m, [], 1.0, "inlay"); self.assertTrue(any("plus fin" in x for x in w), w)
        d.cleanup()


class Inlay(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.part = Path(self.d.name) / "slab.stl"; slab(self.part)
        self.tris = read_stl(self.part)

    def tearDown(self): self.d.cleanup()

    def spec(self, **k): return deco.DecoSpec(**{**dict(kind="text", text="Léo", size_mm=30, u=30, v=30, depth_mm=1.0, mode="inlay", res_mm=0.25), **k})

    def test_inlay_is_flush_and_inside_the_part(self):
        r = deco.apply_decoration(self.part, self.spec(inlay_offset_mm=deco.INLAY_LEGACY_OFFSET_MM)); self.assertEqual(r.errors, [])      # flush mode (legacy offset)
        self.assertEqual(r.triangles, self.tris)                         # base geometry untouched
        lo, hi = bbox(r.deco_triangles)
        self.assertLessEqual(hi[2], 5.0 + 1e-6)                          # never above the surface (5.0)
        self.assertGreaterEqual(hi[2], 5.0 - 0.03); self.assertAlmostEqual(lo[2], 4.0, places=3)
        self.assertTrue(is_watertight(r.deco_triangles))
        cells = r.info["cells"]; self.assertAlmostEqual(volume(r.deco_triangles), cells * 0.25 ** 2 * (1.0 - 0.02), delta=0.1 * cells * 0.0625)

    def test_default_inlay_stands_proud_by_the_default_offset(self):
        r = deco.apply_decoration(self.part, self.spec()); self.assertEqual(r.errors, [])
        hi = bbox(r.deco_triangles)[1][2]; self.assertAlmostEqual(hi, 5.0 + deco.INLAY_TOP_OFFSET_MM, delta=0.03); self.assertGreater(hi, 5.0 + 0.05)

    def test_inlay_on_curved_surface_never_protrudes(self):
        import math
        # cylinder-like top: sample the heightmap and check inlay stays under the original surface everywhere
        p = Path(self.d.name) / "ramp.stl"; slab(p, ramp=20.0)           # gentle slope (~18 deg)
        r = deco.apply_decoration(p, self.spec(size_mm=20, inlay_offset_mm=deco.INLAY_LEGACY_OFFSET_MM)); self.assertEqual(r.errors, [])
        hm = deco.build_heightmap(read_stl(p), "+z", 0.25)
        for t in r.deco_triangles[::7]:
            for x, y, z in t:
                i, j = int(round((x - hm.u0) / hm.res)), int(round((y - hm.v0) / hm.res))
                self.assertLessEqual(z, hm.H[i, j] + 0.03)               # within the sampling tolerance

    def test_inlay_depth_limits(self):
        r = deco.apply_decoration(self.part, self.spec(depth_mm=2.0)); self.assertTrue(r.errors)   # > 1.5 and > 30 % of 5 mm

    def test_preview_has_visible_skin(self):
        r = deco.apply_decoration(self.part, self.spec()); self.assertGreater(r.preview_highlight, 0)
        self.assertEqual(len(r.preview_triangles), len(self.tris) + r.preview_highlight)
        self.assertGreater(bbox(r.preview_triangles[-r.preview_highlight:])[0][2], 5.0)

    def test_export_writes_base_and_inlay(self):
        s = self.spec(); r = deco.apply_decoration(self.part, s)
        out = deco.export_result(r, self.part, s, Path(self.d.name) / "out")
        self.assertTrue(out.name.endswith("_EXPERIMENTAL_incrustation.stl"))
        base = next(out.parent.glob("*_base_unmodified.stl")); self.assertEqual(len(read_stl(base)), len(self.tris))
        self.assertEqual(len(read_stl(out)), len(r.deco_triangles))
        self.assertIn("MÊME OBJET", json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))["how_to_use"].upper())

    def test_inlay_works_on_open_palm(self):
        f = next((JES / "files").glob("*Palm*.stl")) if (JES / "LICENSE.txt").exists() else None
        if not f: self.skipTest("jesimon archive not present")
        r = deco.apply_decoration(f, deco.DecoSpec(kind="text", text="Léo", size_mm=22, u=54.3, v=-116.5, depth_mm=1.0, mode="inlay"))
        self.assertEqual(r.errors, []); self.assertTrue(is_watertight(r.deco_triangles))      # no boolean needed -> works on non-manifold parts


class BambuReady(unittest.TestCase):
    def test_3mf_structure_and_export_guide(self):
        import zipfile, xml.dom.minidom as md
        d = tempfile.TemporaryDirectory(); part = Path(d.name) / "src" / "p.stl"; part.parent.mkdir(); slab(part)
        s = deco.DecoSpec(kind="text", text="Léo", size_mm=30, u=30, v=30, depth_mm=1.0, mode="inlay", res_mm=0.25)
        r = deco.apply_decoration(part, s); out = deco.export_result(r, part, s, Path(d.name) / "out")
        m3 = next(out.parent.glob("*_Bambu_pret.3mf")); z = zipfile.ZipFile(m3); names = z.namelist()
        for n in ("[Content_Types].xml", "3D/3dmodel.model", "Metadata/model_settings.config", "3D/_rels/3dmodel.model.rels"): self.assertIn(n, names)
        parts = [n for n in names if n.startswith("3D/Objects/object_")]; self.assertEqual(len(parts), 2)
        for n in names:
            if n.endswith((".model", ".config", ".rels", ".xml")): md.parseString(z.read(n))                    # well-formed XML
        cfg = z.read("Metadata/model_settings.config").decode(); self.assertEqual(cfg.count("<part "), 2)
        self.assertIn('key="extruder" value="2"', cfg); self.assertIn('value="1"', cfg)
        total = sum(z.read(n).decode().count("<triangle ") for n in parts); self.assertEqual(total, len(r.triangles) + len(r.deco_triangles))
        guide = next(out.parent.glob("*_LISEZ-MOI_Bambu.txt")).read_text(encoding="utf-8"); self.assertIn("filament 2", guide); self.assertIn("EXPÉRIMENTALE", guide.upper())
        d.cleanup()

    def test_colour_pieces_in_3mf(self):
        import zipfile
        from PySide6.QtGui import QColor, QImage
        deco._ensure_qt(); d = tempfile.TemporaryDirectory(); part = Path(d.name) / "p.stl"; slab(part)
        im = QImage(100, 100, QImage.Format_RGB32); im.fill(QColor("white"))
        for x in range(10, 45):
            for y in range(10, 90): im.setPixelColor(x, y, QColor(16, 72, 127))
        for x in range(55, 90):
            for y in range(10, 90): im.setPixelColor(x, y, QColor(207, 39, 51))
        f = Path(d.name) / "l.png"; im.save(str(f))
        s = deco.DecoSpec(kind="image", path=str(f), size_mm=30, u=30, v=30, depth_mm=1.0, mode="inlay", ncolors=2, res_mm=0.25)
        r = deco.apply_decoration(part, s); out = deco.export_result(r, part, s, Path(d.name) / "o")
        cfg = zipfile.ZipFile(next(out.parent.glob("*_Bambu_pret.3mf"))).read("Metadata/model_settings.config").decode()
        self.assertEqual(cfg.count("<part "), 3); self.assertIn('value="3"', cfg); d.cleanup()


def frame_part(path):
    """Square ring of four closed slabs around a 20 x 20 mm through-hole (hole centred at u=30, v=30)."""
    tris = []
    for (x0, y0, w, l) in ((0, 0, 60, 20), (0, 40, 60, 20), (0, 20, 20, 20), (40, 20, 20, 20)):
        t = Path(path).parent / "tmp_slab.stl"; slab(t, w=w, l=l, t=5.0)
        tris += [tuple((p[0] + x0, p[1] + y0, p[2]) for p in tri) for tri in read_stl(t)]
    write_stl(path, tris)


class AutoProtect(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.part = Path(self.d.name) / "frame.stl"; frame_part(self.part)
        self.hm = deco.build_heightmap(read_stl(self.part), "+z", 0.25)

    def tearDown(self): self.d.cleanup()

    def cell(self, u, v): return int((u - self.hm.u0) / self.hm.res), int((v - self.hm.v0) / self.hm.res)

    def test_hole_found_but_outside_is_not(self):
        prot = deco.auto_protected_mask(self.hm, 2.0)
        self.assertTrue(prot[self.cell(30, 30)])                       # inside the hole
        self.assertTrue(prot[self.cell(19, 30)])                       # 1 mm from the hole wall -> inside the 2 mm margin
        self.assertFalse(prot[self.cell(14, 30)])                      # 6 mm away -> free
        self.assertFalse(prot[self.cell(-1, -1)])                      # outside of the part (exterior is not a hole)

    def test_zero_margin_protects_only_the_hole(self):
        prot = deco.auto_protected_mask(self.hm, 0.0)
        self.assertTrue(prot[self.cell(30, 30)]); self.assertFalse(prot[self.cell(19, 30)])

    def test_decoration_near_the_hole_refused_far_accepted(self):
        near = deco.DecoSpec(kind="text", text="A", size_mm=8, u=14.5, v=30, depth_mm=1.0, mode="inlay", res_mm=0.25)     # reaches ~1.5 mm from the hole
        far = deco.DecoSpec(kind="text", text="A", size_mm=8, u=8, v=30, depth_mm=1.0, mode="inlay", res_mm=0.25)
        self.assertTrue(any("protégée" in e for e in deco.apply_decoration(self.part, near, hm=self.hm).errors))
        self.assertEqual(deco.apply_decoration(self.part, far, hm=self.hm).errors, [])
        off = deco.DecoSpec(**{**near.__dict__, "protect_margin_mm": 0.0})
        self.assertFalse(any("protégée" in e for e in deco.apply_decoration(self.part, off, hm=self.hm).errors))

    def test_real_gauntlet_slots_are_protected(self):
        f = next((JES / "files").glob("*Gauntlet*.stl")) if (JES / "LICENSE.txt").exists() else None
        if not f: self.skipTest("jesimon archive not present")
        hm = deco.build_heightmap(read_stl(f), "+z", 0.25); prot = deco.auto_protected_mask(hm, 2.0); bare = deco.auto_protected_mask(hm, 0.0)
        self.assertGreater(int(prot.sum()), int(bare.sum()) * 1.5)      # margins add area around the strap slots and square holes
        self.assertGreater(int(bare.sum()), 500)                        # several through-holes exist on this part


class SuggestColours(unittest.TestCase):
    def test_counts_logo_colours(self):
        import tempfile
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 30"><rect width="30" height="30" fill="#09324E"/>'
               '<rect x="30" width="30" height="30" fill="#2A67A1"/><rect x="60" width="30" height="30" fill="#CF232A"/></svg>')
        one = svg.replace("#2A67A1", "#09324E").replace("#CF232A", "#09324E")
        with tempfile.TemporaryDirectory() as d:
            for name, txt, n in (("three.svg", svg, 3), ("one.svg", one, 1)):
                p = Path(d) / name; p.write_text(txt)
                self.assertEqual(deco.suggest_colours(deco.DecoSpec(kind="svg", path=str(p), mode="inlay", axis="+z", size_mm=20)), n)


if __name__ == "__main__": unittest.main()


class ThickenThin(unittest.TestCase):
    def test_thin_strokes_are_widened_thick_blocks_and_other_colours_untouched(self):
        m = np.zeros((120, 60), bool); m[10:12, 5:55] = True; m[30:90, 10:50] = True       # res 0.1 mm: 0.2 mm line + a 4 mm block
        out = deco.thicken_thin(m, 0.1)
        self.assertGreaterEqual(out[:, 30][5:17].sum(), 6)                                  # line now >= 0.6 mm wide
        self.assertEqual(out[30:90, 10:50].sum(), m[30:90, 10:50].sum()); self.assertTrue((out[40:80, 20:40]).all())
        self.assertFalse(out[60, 5] and not m[60, 5] and out[60, 4] and out[60, 3])         # the block is not grown
        other = np.zeros_like(m); other[8:10, 5:55] = True
        self.assertFalse((deco.thicken_thin(m, 0.1, other) & other).any())

