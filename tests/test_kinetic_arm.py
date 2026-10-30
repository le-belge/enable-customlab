import unittest

from customlab import kinetic_arm as K
from customlab.profiles import SizingError, compute_kinetic_arm_sizing, compute_sizing, load_profile


class Charts(unittest.TestCase):
    def test_shape_and_ordering(self):
        self.assertEqual(len(K.SCALES), 21); self.assertEqual((K.SCALES[0], K.SCALES[-1]), (100.0, 50.0))
        for s, r in K.CHART.items():
            for key in ("elbow", "upper", "insert_len"):
                v = list(r[key].values()); self.assertEqual(v, sorted(v), (s, key))
        self.assertEqual(len(K.CHART[100]["insert_len"]), 17)
        for a, b in zip(K.SCALES, K.SCALES[1:]):
            self.assertGreater(K.CHART[a]["hand_length"], K.CHART[b]["hand_length"])
            for t in K.TYPES: self.assertGreater(K.CHART[a]["upper"][t], K.CHART[b]["upper"][t])

    def test_charts_are_linear_in_scale_which_checks_the_transcription(self):
        c100 = K.CHART[100]
        for s in K.SCALES:
            r = K.CHART[s]; f = s / 100.0
            self.assertLess(abs(r["hand_length"] - c100["hand_length"] * f), 1.6, s)
            for t in K.TYPES:
                self.assertLess(abs(r["elbow"][t] - c100["elbow"][t] * f), 1.6, (s, t))
                self.assertLess(abs(r["upper"][t] - c100["upper"][t] * f), 0.2, (s, t))
            for k in K.INSERTS: self.assertLess(abs(r["insert_len"][k] - c100["insert_len"][k] * f), 1.6, (s, k))

    def test_tongue_and_liner_charts(self):
        for ins, kind in (("A", "short"), ("H", "short"), ("I", "long"), ("Q", "long")):
            self.assertEqual(K.compute(166, 70, K.CHART[70]["insert_len"][ins]).insert, ins)
        r = K.compute(166, 60, 60); self.assertEqual((r.forearm_type, r.insert, r.tongue, r.liner_set), ("A", "A", 2, 2))


class ManualExample(unittest.TestCase):
    def test_jake(self):
        r = K.compute(168.7, 70.66, 83.32)       # manual pages 27-33
        self.assertEqual((r.lower_scale, r.forearm_type, r.upper_scale, r.insert, r.tongue, r.liner_set), (70.0, "B", 70.0, "D", 2, 4))
        self.assertEqual((r.palm_scale, r.tensioner_scale), (70.0, 70.0))

    def test_rounding_directions(self):
        self.assertEqual(K.compute(166.0, 60, 60).lower_scale, 70.0)          # exact value
        self.assertEqual(K.compute(165.9, 60, 60).lower_scale, 67.5)          # DOWN
        self.assertEqual(K.compute(166, 71, 60).forearm_type, "B"); self.assertEqual(K.compute(166, 71.1, 60).forearm_type, "C")     # UP
        self.assertEqual(K.compute(166, 60, 84).insert, "D"); self.assertEqual(K.compute(166, 60, 84.1).insert, "E")               # UP

    def test_tongue_liner_by_insert_group(self):
        r = K.compute(237, 122, 250); self.assertEqual((r.forearm_type, r.insert, r.tongue, r.liner_set), ("F", "Q", 3, 11))
        r = K.compute(237, 98, 90); self.assertEqual((r.forearm_type, r.insert, r.tongue, r.liner_set), ("A", "A", 2, 2))
        r = K.compute(237, 117, 150); self.assertEqual((r.forearm_type, r.insert, r.tongue, r.liner_set), ("E", "G", 4, 10))

    def test_tensioner_closest_file(self):
        r = K.compute(166, 86, 60)                # Lower 70 %, type F -> upper 84 %: a provided file
        self.assertEqual((r.upper_scale, r.tensioner_scale), (84.0, 85.0))
        self.assertTrue(any("Tensioners" in w for w in r.warnings))
        self.assertEqual(K.nearest_file_scale(K.TENSIONERS, 81.4), 82.5)


class Refusals(unittest.TestCase):
    def test_out_of_chart_is_refused_never_clamped(self):
        for args in ((118, 60, 60), (238, 60, 60), (166, 87, 60), (166, 60, 176), (0, 60, 60), (166, -1, 60), (float("nan"), 60, 60), (True, 60, 60)):
            with self.assertRaises(ValueError, msg=str(args)): K.compute(*args)

    def test_residual_ratio_warning(self):
        self.assertTrue(any("15-70" in w for w in K.compute(168.7, 70.66, 83.32, 100).warnings))     # 83 % of the sound forearm
        self.assertFalse(any("15-70" in w for w in K.compute(168.7, 70.66, 83.32, 250).warnings))


class Profile(unittest.TestCase):
    def test_profile_and_sizing(self):
        p = load_profile("kinetic_arm"); self.assertEqual((p["status"], p["method"]), ("experimental", "kinetic_arm_chart"))
        r = compute_kinetic_arm_sizing("left", 168.7, 70.66, 83.32, 250)
        self.assertEqual(r.derived["forearm_type"], "B"); self.assertTrue(r.scad_defines["mirror_x"]); self.assertIn("EXPERIMENTAL", r.warnings[0])
        with self.assertRaises(SizingError): compute_kinetic_arm_sizing("up", 168.7, 70.66, 83.32)
        with self.assertRaises(SizingError): compute_kinetic_arm_sizing("left", 100, 70.66, 83.32)
        with self.assertRaises(SizingError): compute_sizing("kinetic_arm", "left", "Palm", {})


if __name__ == "__main__":
    unittest.main()
