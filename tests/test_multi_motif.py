import os, tempfile, unittest, json
from unittest import mock
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["CUSTOMLAB_SYNC"] = "1"
import numpy as np
from PySide6.QtWidgets import QApplication
from customlab import deco
from customlab.gui import MainWindow
app = QApplication.instance() or QApplication([])
PART = "customlab/bundled_parts/phoenix_jesimon_100pct/left/files/unlimbitedphoenix_Palm20170317-11586-1blsvbc-0.stl"


def flat_hm(n=240, res=0.25):
    return deco.HeightMap("+z", res, -n * res / 2, -n * res / 2, np.zeros((n + 1, n + 1)), 5.0)


class MultiMotifMasks(unittest.TestCase):
    def test_two_texts_make_two_pieces(self):
        hm = flat_hm(); a = deco.DecoSpec(kind="text", text="AB", size_mm=12, u=-15, v=0)
        b = deco.DecoSpec(kind="text", text="CD", size_mm=12, u=15, v=0)
        union, layers = deco.render_spec_masks(deco.DecoSpec(**{**a.__dict__, "extra": (b,)}), hm)
        self.assertEqual(len(layers), 2); self.assertTrue((layers[0][2] & layers[1][2]).sum() == 0)
        self.assertEqual(int(union.sum()), sum(int(m.sum()) for _, _, m in layers))

    def test_single_motif_unchanged(self):
        hm = flat_hm(); a = deco.DecoSpec(kind="text", text="AB", size_mm=12)
        m, ly = deco.render_spec_masks(a, hm); self.assertIsNone(ly); self.assertTrue(m.any())

    def test_empty_extra_is_ignored_and_too_many_colours_refused(self):
        hm = flat_hm(); a = deco.DecoSpec(kind="text", text="AB", size_mm=12, u=-30)
        e = deco.DecoSpec(kind="text", text="  ")
        _, ly = deco.render_spec_masks(deco.DecoSpec(**{**a.__dict__, "extra": (e,)}), hm); self.assertIsNone(ly)
        ex = tuple(deco.DecoSpec(kind="text", text="X", size_mm=8, u=-20 + 10 * i) for i in range(5))
        with self.assertRaises(deco.DecoError): deco.render_spec_masks(deco.DecoSpec(**{**a.__dict__, "extra": ex}), hm)


class MultiMotifGui(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = mock.patch.dict(os.environ, {"CUSTOMLAB_HOME": self.d.name}); self.p.start()

    def tearDown(self): self.p.stop(); self.d.cleanup()

    def test_add_switch_remove_and_state(self):
        w = MainWindow(); w.select("phoenix_hand"); c = w.custom; c.set_part(PART)
        c.text.setText("Léo"); c.refresh()
        self.assertTrue(c.b_delm.isHidden())
        c.add_motif(); self.assertEqual(len(c.motif_list), 2); self.assertEqual(c.text.text(), "")
        c.text.setText("Mike"); c.refresh()
        self.assertEqual(len(c.spec().extra), 1); self.assertEqual(c.spec().extra[0].text, "Léo")
        d = json.loads(json.dumps(c.state_dict())); self.assertEqual([m["text"] for m in d["motifs"]], ["Léo", "Mike"])
        c.select_motif(0); self.assertEqual(c.text.text(), "Léo"); self.assertEqual(c.spec().extra[0].text, "Mike")
        c.load_state(d); self.assertEqual(len(c.motif_list), 2); self.assertEqual(c.cur, 1); self.assertEqual(c.text.text(), "Mike")
        c.remove_motif(); self.assertEqual(len(c.motif_list), 1); self.assertEqual(c.text.text(), "Léo"); self.assertEqual(c.spec().extra, ())
