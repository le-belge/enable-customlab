import unittest

from customlab import kinetic_hand as K
from customlab.profiles import SizingError, compute_kinetic_sizing, compute_sizing, load_profile


class Chart(unittest.TestCase):
    def test_chart_is_the_manual_table(self):
        self.assertEqual(len(K.SCALES), 21); self.assertEqual((K.SCALES[0], K.SCALES[-1]), (50.0, 100.0))
        self.assertTrue(all(abs((b - a) - 2.5) < 1e-9 for a, b in zip(K.SCALES, K.SCALES[1:])))
        self.assertEqual({k: K.CHART[100][k] for k in K.COLUMNS}, dict(palm_length=100, wrist_width=71, forearm_width=75, max_palm_width=92, overall_hand_length=217, dist_max_palm_width=45))
        self.assertEqual(K.CHART[100]["inserts"], {"A": 17, "B": 25, "C": 33, "D": 42, "E": 50}); self.assertEqual(K.CHART[50]["inserts"], {"A": 8, "B": 12, "C": 17, "D": 21, "E": 25})

    def test_chart_is_linear_in_scale_like_uniform_scaling(self):
        for s in K.SCALES:                                     # every dimension = 100 % value x scale (the manual rounds to whole mm)
            for col in K.COLUMNS: self.assertLess(abs(K.CHART[s][col] - K.CHART[100][col] * s / 100.0), 1.1, (s, col))
            for k, v in K.CHART[s]["inserts"].items(): self.assertLess(abs(v - K.CHART[100]["inserts"][k] * s / 100.0), 1.1, (s, k))

    def test_monotonic_and_ordered_inserts(self):
        for col in K.COLUMNS: vals = [K.CHART[s][col] for s in K.SCALES]; self.assertEqual(vals, sorted(vals), col)
        for s in K.SCALES: v = [K.CHART[s]["inserts"][k] for k in "ABCDE"]; self.assertEqual(v, sorted(v))


class ManualExamples(unittest.TestCase):
    def test_basic_example_72_5_percent_insert_D(self):
        r = K.compute(wrist_mm=48, palm_length_mm=40)          # 48 + 3 mm padding = 51 -> 72.5 % ; palm 72 - 40 = 32 mm -> insert D (30 mm)
        self.assertEqual((r.scale_percent, r.insert, r.insert_mm, r.space_mm), (72.5, "D", 30, 32.0)); self.assertEqual(r.padded_wrist_mm, 51)

    def test_advanced_example_Z_82_5_insert_E_is_information_only(self):
        r = K.compute(48, 40, sound_hand_length_mm=178)
        self.assertEqual(r.advanced["scale_z"], 82.5); self.assertEqual(r.advanced["insert"], "E"); self.assertFalse(r.advanced["applied"])
        self.assertEqual(r.scale_percent, 72.5)                # the applied scale stays the basic uniform one
        self.assertTrue(any("-21" in w for w in r.warnings))   # 157 mm design vs 178 mm sound hand: 21 mm shorter, as in the manual (M20)

    def test_padding_is_added_to_the_affected_wrist(self):
        self.assertEqual(K.compute(48, 40).scale_percent, K.compute(51 - 3, 40).scale_percent); self.assertNotEqual(K.compute(36, 40).scale_percent, K.compute(48, 40).scale_percent)


class Limits(unittest.TestCase):
    def test_out_of_chart_is_refused_not_clamped(self):
        for w in (25, 28, 70, 90):
            with self.assertRaises(K.OutOfRange) as c: K.compute(w, 40)
            self.assertIn("nothing was adjusted", str(c.exception))
        K.compute(32, 40); K.compute(69, 40)                   # 35 and 72 mm after padding: inside the chart extremes

    def test_below_55_percent_warns(self):
        r = K.compute(32, 30); self.assertEqual(r.scale_percent, 50.0); self.assertTrue(any("55 %" in w for w in r.warnings))
        self.assertFalse(any("55 %" in w for w in K.compute(48, 40).warnings))

    def test_invalid_inputs(self):
        for a in ((0, 40), (-1, 40), (48, 0), (float("nan"), 40), (True, 40)):
            with self.assertRaises(ValueError): K.compute(*a)

    def test_space_warnings(self):
        r = K.compute(48, 80); self.assertLess(r.space_mm, 0); self.assertTrue(any("longer than the design palm" in w for w in r.warnings))
        self.assertTrue(any("test palm" in w.lower() for w in K.compute(48, 40).warnings))
        self.assertTrue(any("maximum palm width" in w for w in K.compute(48, 40, max_palm_width_mm=80).warnings))
        self.assertFalse(any("maximum palm width" in w for w in K.compute(48, 40, max_palm_width_mm=60).warnings))

    def test_tie_goes_to_the_larger_scale(self):
        self.assertEqual(K.closest_scale("wrist_width", 36.0), 52.5)       # 35 mm (50 %) and 37 mm (52.5 %) are equally close: more room is chosen
        self.assertEqual(K.closest_scale("wrist_width", 55.0), 77.5)       # exact chart value


class Integration(unittest.TestCase):
    def test_profile_and_sizing_result(self):
        p = load_profile("kinetic_hand"); self.assertEqual(p["status"], "experimental"); self.assertEqual(p["method"], "kinetic_chart")
        self.assertTrue(p["license"]["verified"]); self.assertIn("NC-SA", p["license"]["name"])
        r = compute_kinetic_sizing("left", "Palm", 48, 40); self.assertEqual(r.derived["scale_percent"], 72.5); self.assertEqual(r.derived["insert"], "D")
        self.assertEqual(r.scad_defines["mirror_x"], True); self.assertEqual(compute_kinetic_sizing("right", "Palm", 48, 40).scad_defines["mirror_x"], False)
        self.assertEqual(r.status, "experimental"); self.assertTrue(any("EXPERIMENTAL" in w for w in r.warnings))
        with self.assertRaises(SizingError): compute_kinetic_sizing("left", "Palm", 25, 40)


if __name__ == "__main__":
    unittest.main()
