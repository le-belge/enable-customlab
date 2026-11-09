"""Multi-colour / multi-material export: materials, printer checks, plate packing and the whole-device Bambu 3MF."""
import io
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from customlab import bambu3mf, deco, export_all, materials
from tests.test_deco import slab


def zip_of(p): return zipfile.ZipFile(io.BytesIO(Path(p).read_bytes()))


def cube(x0, y0, s):
    return [((x0, y0, 0), (x0 + s, y0, 0), (x0, y0 + s, 0)), ((x0, y0, s), (x0 + s, y0 + s, s), (x0 + s, y0, s))]


class Materials(unittest.TestCase):
    def test_tpu_suggested_only_from_the_file_name(self):
        for n in ("Kinetic_Hinge_TPU.stl", "palm-cover flex.stl", "doigt_souple.stl"): self.assertEqual(materials.suggest_material(n), "TPU 95A", n)
        for n in ("Palm.stl", "Gauntlet_L.stl", "output.stl", "reflexion.stl"): self.assertEqual(materials.suggest_material(n), "PLA", n)

    def test_plan_merges_identical_filaments_and_numbers_them_in_order(self):
        pl = materials.plan([{"label": "Paume", "material": "PLA", "colour": "white", "motif_colours": ["#C12E1F"]},
                             {"label": "Doigts", "material": "PLA", "colour": "#ffffff"},
                             {"label": "Charnière", "material": "TPU 95A", "colour": "black"}], "x1c_ams")
        self.assertEqual(pl.errors, []); self.assertEqual(pl.filaments, [("PLA", "#FFFFFF"), ("PLA", "#C12E1F"), ("TPU 95A", "#161616")])
        self.assertEqual(pl.index("TPU 95A", "black"), 3); self.assertTrue(any("TPU" in w for w in pl.warnings))

    def test_x1c_refuses_two_flexible_spools_and_too_many_filaments_other_accepts(self):
        two_tpu = [{"label": "a", "material": "TPU 95A", "colour": "black"}, {"label": "b", "material": "TPU 85A", "colour": "black"}]
        self.assertTrue(materials.plan(two_tpu, "x1c_ams").errors); self.assertEqual(materials.plan(two_tpu, "other").errors, [])
        six = [{"label": str(i), "material": "PLA", "colour": c} for i, c in enumerate(["white", "black", "red", "blue", "green", "yellow"])]
        self.assertTrue(materials.plan(six, "x1c_ams").errors); self.assertEqual(materials.plan(six, "other").errors, [])
        ten = six + [{"label": str(i), "material": "PLA", "colour": c} for i, c in enumerate(["pink", "purple", "orange", "grey"])]
        self.assertEqual(materials.plan(ten, "other").errors, [])

    def test_mixed_rigid_materials_are_flagged(self):
        pl = materials.plan([{"label": "a", "material": "PLA", "colour": "white"}, {"label": "b", "material": "PETG", "colour": "white"}], "x1c_ams")
        self.assertTrue(any("PETG" in w and "PLA" in w for w in pl.warnings))


class Plates(unittest.TestCase):
    def test_packing_fills_plates_without_overlap_and_reports_parts_too_big(self):
        objs = [{"name": f"p{i}", "parts": [{"triangles": cube(0, 0, 100)}]} for i in range(5)] + [{"name": "big", "parts": [{"triangles": cube(0, 0, 300)}]}]
        plates, too_big = bambu3mf.pack(objs, (256.0, 256.0))
        self.assertEqual(too_big, ["big"]); self.assertEqual(sum(len(p) for p in plates), 5); self.assertEqual(len(plates), 2)          # 4 cubes of 100 mm per 256 mm plate
        for pl in plates:
            boxes = [(tx, ty, tx + 100, ty + 100) for o, tx, ty, tz in pl]
            for b in boxes: self.assertTrue(0 <= b[0] and b[2] <= 256 and 0 <= b[1] and b[3] <= 256, b)
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]: self.assertTrue(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b))

    def test_plate_3mf_has_one_object_per_part_with_filaments_and_materials(self):
        objs = [{"name": "Paume", "parts": [{"name": "Base", "triangles": cube(0, 0, 40), "extruder": 1}, {"name": "Motif", "triangles": cube(5, 5, 10), "extruder": 2}]},
                {"name": "Charnière", "parts": [{"name": "Charnière", "triangles": cube(0, 0, 20), "extruder": 3}]}]
        plates, _ = bambu3mf.pack(objs, (330.0, 320.0))
        with tempfile.TemporaryDirectory() as d:
            f = bambu3mf.write_bambu_plate(Path(d) / "x.3mf", plates[0], [("PLA", "#FFFFFF"), ("PLA", "#C12E1F"), ("TPU", "#161616")]); z = zip_of(f)
            cfg = z.read("Metadata/model_settings.config").decode(); model = z.read("3D/3dmodel.model").decode()
            self.assertEqual(len([n for n in z.namelist() if n.startswith("3D/Objects/object_")]), 3)
            self.assertEqual(model.count("<item "), 2); self.assertEqual(cfg.count("<model_instance>"), 2)
            self.assertEqual(sorted(re.findall(r'key="extruder" value="(\d)"', cfg)), ["1", "1", "2", "3", "3"])     # 2 objects + 3 parts
            ps = json.loads(z.read("Metadata/project_settings.config")); self.assertEqual(ps["filament_type"], ["PLA", "PLA", "TPU"]); self.assertEqual(ps["filament_colour"][2], "#161616")


class DeviceExport(unittest.TestCase):
    def test_whole_device_3mf_with_tpu_part_and_motif_colour(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a, b = d / "Palm.stl", d / "Hinge_TPU.stl"; slab(a, w=60, l=60, t=6); slab(b, w=30, l=20, t=4)
            spec = deco.DecoSpec(kind="text", text="A", mode="relief", depth_mm=0.6, axis="+z", size_mm=20, u=30.0, v=30.0, res_mm=0.5, protect_margin_mm=0)
            ctx = {"mirror_for": lambda p: False, "extra": lambda: {}, "scale_for": lambda p: (None, None), "printer": "x1c_ams",
                   "materials": {str(a.resolve()): ("PLA", "white")}}
            res = export_all.run([("Paume", a), ("Charnière", b)], (a, spec, []), d / "out", ctx)
            dev = res[-1]; self.assertEqual(dev["status"], "ok", dev)
            self.assertEqual([(f["material"], f["colour"]) for f in dev["filaments"]], [("PLA", "#FFFFFF"), ("PLA", "#161616"), ("TPU 95A", "#161616")])
            z = zip_of(d / "out" / "APPAREIL_Bambu_pret.3mf"); cfg = z.read("Metadata/model_settings.config").decode()
            self.assertIn('value="3"', cfg); self.assertEqual(json.loads(z.read("Metadata/project_settings.config"))["filament_type"], ["PLA", "PLA", "TPU"])
            guide = (d / "out" / "APPAREIL_LISEZ-MOI_Bambu.txt").read_text(encoding="utf-8")
            self.assertIn("TPU 95A", guide); self.assertIn("Aucune impression", guide)

    def test_refused_when_the_printer_cannot_hold_the_filaments(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a, b = d / "a_TPU.stl", d / "b_flex.stl"; slab(a); slab(b)
            ctx = {"mirror_for": lambda p: False, "extra": lambda: {}, "scale_for": lambda p: (None, None), "printer": "x1c_ams",
                   "materials": {str(b.resolve()): ("TPU 85A", "red")}}
            res = export_all.run([("A", a), ("B", b)], None, d / "out", ctx)
            self.assertEqual(res[-1]["status"], "skipped"); self.assertIn("souples", res[-1]["message"]); self.assertFalse(list((d / "out").glob("APPAREIL*.3mf")))
            self.assertEqual([r["status"] for r in res[:2]], ["ok", "ok"])            # the parts themselves are still exported

    def test_no_printer_no_device_file(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a = d / "a.stl"; slab(a)
            res = export_all.run([("A", a)], None, d / "out", {"mirror_for": lambda p: False, "extra": lambda: {}, "scale_for": lambda p: (None, None)})
            self.assertEqual(len(res), 1); self.assertFalse(list((d / "out").glob("APPAREIL*")))


class Dialog(unittest.TestCase):
    def test_table_suggests_tpu_flags_the_x1c_limit_and_passes_the_choices(self):
        from PySide6.QtWidgets import QApplication
        from customlab import export_all_dialog as ed
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a, b, c = d / "Palm.stl", d / "Hinge_TPU.stl", d / "Cover_flex.stl"
            for f in (a, b, c): slab(f)
            items = [{"label": "Paume", "path": a}, {"label": "Charnière", "path": b}, {"label": "Couvercle", "path": c}]
            dlg = ed.ExportAllDialog(None, "fr", items, None, {"mirror_for": lambda p: False, "extra": lambda: {}, "scale_for": lambda p: (None, None)}, "", None)
            self.assertEqual([dlg.mat.cellWidget(r, 1).currentData() for r in range(3)], ["PLA", "TPU 95A", "TPU 95A"])
            dlg.printer.setCurrentIndex(dlg.printer.findData("x1c_ams")); self.assertNotIn("⚠", dlg.summary.text())             # same TPU colour = one spool: fine
            dlg.mat.cellWidget(2, 2).setCurrentIndex(dlg.mat.cellWidget(2, 2).findData("red")); self.assertIn("souples", dlg.summary.text())   # 2 TPU spools: refused on the X1C
            dlg.printer.setCurrentIndex(dlg.printer.findData("other")); self.assertNotIn("⚠", dlg.summary.text())
            dlg.mat.cellWidget(0, 2).setCurrentIndex(dlg.mat.cellWidget(0, 2).findData("red"))
            self.assertEqual(dlg.choices()[str(a.resolve())], ("PLA", "red")); self.assertIn("3 filament(s)", dlg.summary.text())
            dlg.close(); app.processEvents()


if __name__ == "__main__":
    unittest.main()
