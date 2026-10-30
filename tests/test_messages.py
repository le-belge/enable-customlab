import unittest

from customlab import messages as M


class Messages(unittest.TestCase):
    def test_known_sizing_messages_are_translated_both_ways(self):
        s, t, ok = M.localize("EXPERIMENTAL: dimensional compatibility not validated; no conformity claim", "fr"); self.assertTrue(ok); self.assertIn("EXPÉRIMENTAL", t); self.assertEqual(s, M.CHECK)
        s, t, ok = M.localize("EXPERIMENTAL: dimensional compatibility not validated; no conformity claim", "en"); self.assertIn("EXPERIMENTAL", t)
        _, t, ok = M.localize("HandLen: no documented valid range; value not validated", "fr"); self.assertTrue(ok); self.assertIn("HandLen", t); self.assertIn("plage", t)

    def test_out_of_range_message_is_plain_french_with_numbers(self):
        src = ("Scale 174.42 % is above 160 %: outside the documented range. With a 5 mm margin the usable wrist width is 38.0-63.8 mm. "
               "Check the measurement, margin, or choose another device; nothing was adjusted.")
        s, t, ok = M.localize(src, "fr"); self.assertTrue(ok); self.assertEqual(s, M.BLOCK)
        self.assertIn("174.42", t); self.assertIn("38.0", t); self.assertIn("Rien n'a été modifié", t)
        _, t, _ = M.localize(src, "en"); self.assertIn("Nothing was changed", t)

    def test_french_deco_messages_get_english(self):
        _, t, ok = M.localize("Pente locale 71° > 60° sous le motif (bord/paroi) : le motif serait déformé.", "en"); self.assertTrue(ok); self.assertIn("too steep", t)
        _, t, ok = M.localize("La décoration entre dans la zone interdite n°2 (14 cellules).", "en"); self.assertIn("no. 2", t)

    def test_every_engine_message_is_recognised(self):
        """Run real scenarios and make sure no message produced by the engines escapes the translation table."""
        import tempfile
        from pathlib import Path
        from customlab import deco, phoenix
        from customlab.profiles import compute_phoenix_sizing, compute_sizing
        from tests.test_deco import slab, STAR
        texts = []
        texts += compute_phoenix_sizing("left", "Palm", 40, 8).warnings + compute_sizing("unlimbited_arm", "right", "Cuff", {"HandLen": 170, "ForearmLen": 230, "BicepCircum": 250}).warnings
        for w in (30, 70):
            try: phoenix.compute(w)
            except phoenix.OutOfRange as e: texts.append(str(e))
        d = tempfile.TemporaryDirectory(); part = Path(d.name) / "s.stl"; slab(part)
        for kw in (dict(u=30, v=30), dict(u=55, v=30), dict(u=30, v=30, depth_mm=3.0), dict(u=30, v=30, mode="inlay"), dict(u=30, v=30, mode="relief")):
            r = deco.apply_decoration(part, deco.DecoSpec(**{**dict(kind="svg", path=str(STAR), size_mm=26, depth_mm=1.0, res_mm=0.25), **kw}))
            texts += r.errors + r.warnings
        r = deco.apply_decoration(part, deco.DecoSpec(kind="svg", path=str(STAR), size_mm=26, u=30, v=30, mode="inlay", depth_mm=1.0, res_mm=0.25), zones=[(25, 25, 35, 35)]); texts += r.errors
        unknown = [t for t in texts if not M.localize(t, "fr")[2]]
        self.assertEqual(unknown, [], unknown); d.cleanup()

    def test_sorting_and_html(self):
        items = [("Les zones fonctionnelles… x", None), ("Pente locale 71° > 60° sous le motif (bord/paroi) : le motif serait déformé.", M.BLOCK),
                 ("Licence depends on the file variant used (see x)", None)]
        order = [s for s, _ in M.sort_messages(items, "fr")]; self.assertEqual(order, sorted(order, key={M.BLOCK: 0, M.CHECK: 1, M.INFO: 2}.get))
        self.assertIn("✖", M.messages_html(items, "fr")); self.assertEqual(M.sort_messages([("x", None), ("x", None)]), [(M.CHECK, "x")])    # de-duplicated, unknown kept


if __name__ == "__main__":
    unittest.main()
