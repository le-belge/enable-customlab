import os, tempfile, time, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from unittest import mock
from PySide6.QtWidgets import QApplication
from customlab import export_all_dialog as ed
from tests.test_deco import slab
app = QApplication.instance() or QApplication([])


class QuickExport(unittest.TestCase):
    def test_one_click_exports_every_part_without_choices(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); a, b = d / "a.stl", d / "b.stl"; slab(a, w=80, l=80, t=6); slab(b, w=90, l=70, t=6)
            ctx = {"mirror_for": lambda p: False, "extra": lambda: {"device": "test"}, "scale_for": lambda p: (60.0, None)}
            items = [{"label": "A", "path": a}, {"label": "B", "path": b}]
            with mock.patch.object(ed.QFileDialog, "getExistingDirectory", return_value=str(d / "dest")):
                dlg = ed.ExportAllDialog(None, "fr", items, None, ctx, " (60 %)", None, quick=True)
                self.assertTrue(dlg.list.isHidden())
                t0 = time.time()
                while not hasattr(dlg, "results") and time.time() - t0 < 30: app.processEvents(); time.sleep(0.05)
            self.assertEqual([r["status"] for r in dlg.results], ["ok", "ok"])
            self.assertTrue((d / "dest" / "export_toutes_les_pieces" / "a").is_dir()); self.assertFalse(dlg.b_reveal.isHidden()); self.assertTrue(dlg.b_bambu.isHidden())      # no decorated part here -> no .3mf
            (d / "dest" / "export_toutes_les_pieces" / "a" / "x_Bambu_pret.3mf").write_bytes(b"0"); dlg._finished(dlg.results); self.assertFalse(dlg.b_bambu.isHidden())


if __name__ == "__main__": unittest.main()
