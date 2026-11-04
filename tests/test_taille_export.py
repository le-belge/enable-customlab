"""Non-régression, audit du 3 novembre 2026, constats 1, 4 et 5 (taille exportée).

1 : une taille forcée à la main est annulée quand une mesure change ; la page Mesures montre l'échelle réellement exportée ;
    Kinetic Hand : insert recalculé pour la taille forcée ; Kinetic Arm : même échelle forcée dans l'export unitaire et l'export complet.
4 : Kinetic Arm : les pièces supérieures suivent le tableau B2 (jusqu'à 120 %) au lieu d'être refusées au-delà de 100 %.
5 : Phoenix : la bibliothèque et l'export complet ne contiennent que les 8 pièces du côté choisi.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CUSTOMLAB_SYNC"] = "1"
from PySide6.QtWidgets import QApplication

from customlab import kinetic_arm, kinetic_hand, library
from customlab import messages as M
from customlab.gui import MainWindow
from tests.test_deco import slab


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); os.environ["CUSTOMLAB_HOME"] = str(Path(self.d.name) / "home")

    def tearDown(self): self.d.cleanup()

    def force(self, w, value):
        """The volunteer types a final size on page 4."""
        w.scale_spin.setValue(value); w._scale_edited()


class ForcedSizeDroppedOnNewMeasure(_Base):
    """Constat 1 : reproduction de l'audit (Phoenix, poignet 50 mm, taille forcée 130 %, poignet ressaisi à 40 mm)."""

    def test_new_measure_cancels_the_forced_size_and_says_so(self):
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(50)
        self.assertEqual(w.scale_percent(), 127.91)
        self.force(w, 130.0); self.assertEqual(w.scale_percent(), 130.0); self.assertEqual(w.scale_for_part("x.stl"), (130.0, None))
        self.assertIn("Échelle appliquée à l'export : 130 % (taille forcée à la main)", w.live.toPlainText())
        w.fields["wrist_mm"].setValue(40)
        self.assertIsNone(w.scale_override); self.assertEqual(w.scale_percent(), 104.65); self.assertEqual(w.scale_for_part("x.stl"), (104.65, None))
        txt = w.live.toPlainText(); self.assertIn("Échelle appliquée à l'export : 104.65 %", txt); self.assertIn("taille forcée de 130 % a été annulée", txt)
        self.assertNotIn("taille forcée à la main", txt)

    def test_unticked_option_shows_original_size_and_project_reload_keeps_the_forced_size(self):
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(50); self.force(w, 130.0)
        st = w.state_dict(); w2 = MainWindow(); w2.load_state(st)
        self.assertEqual(w2.scale_percent(), 130.0); self.assertNotIn("annulée", w2.live.toPlainText())          # reloading the measures is not a change
        w2.scale_cb.setChecked(False); w2.recompute(); self.assertIn("aucune : taille d'origine (100 %)", w2.live.toPlainText())

    def test_english_message(self):
        w = MainWindow(); w.select("phoenix_hand"); w.fields["wrist_mm"].setValue(50); self.force(w, 130.0); w.toggle_lang()
        w.fields["wrist_mm"].setValue(45); txt = w.live.toPlainText()
        self.assertIn("Scale applied on export", txt); self.assertIn("forced to 130 % was cancelled", txt)


class KineticHandInsertFollowsForcedSize(_Base):
    def test_insert_for_scale_matches_the_chart(self):
        self.assertEqual(kinetic_hand.insert_for_scale(72.5, 40)[:2], ("D", 30))               # manual example: 48 mm wrist -> 72.5 % + insert D
        self.assertEqual(kinetic_hand.insert_for_scale(80, 40)[:2], ("E", 40))
        with self.assertRaises(kinetic_hand.OutOfRange): kinetic_hand.insert_for_scale(81, 40)   # not a chart row: nothing interpolated

    def test_forced_size_recomputes_the_insert_everywhere(self):
        w = MainWindow(); w.select("kinetic_hand"); w.fields["wrist_mm"].setValue(48); w.fields["palm_mm"].setValue(40)
        self.assertEqual(w.kinetic_insert()[:2], ("D", 30))
        w.scale_override = 80.0; w.recompute()
        self.assertEqual(w.kinetic_insert()[:2], ("E", 40)); self.assertIn("Insert souple : E (40 mm) — pour la taille exportée de 80 %", w.live.toPlainText())
        self.assertEqual(w.export_extra()["kinetic_insert_for_exported_scale"], "E"); self.assertEqual(w.export_extra()["scale_forced_by_volunteer"], 80.0)
        w.scale_override = 81.0; w.recompute(); self.assertIsNone(w.kinetic_insert()[0])
        self.assertIn("n'est pas une ligne du tableau", w.live.toPlainText()); self.assertIn("à déterminer", w.live.toPlainText())
        w.scale_override = None; w.scale_cb.setChecked(False); w.recompute(); self.assertEqual(w.kinetic_insert()[:2], ("E", 50))   # exported at 100 %: insert of the 100 % row


class KineticArmSameScaleBothPaths(_Base):
    def window(self, hand=168.7, elbow=70.66, resid=83.32):
        w = MainWindow(); w.select("kinetic_arm")
        for k, x in (("hand_mm", hand), ("elbow_mm", elbow), ("resid_mm", resid)): w.fields[k].setValue(x)
        w.show_result = lambda: None                    # no STL here: only the scale rules are exercised
        return w

    def test_forced_size_applies_to_its_group_in_both_exports(self):
        w = self.window(); w.custom.part_path = "UpArmCov100.STL"        # Jake: lower 70 %, upper 70 %
        self.force(w, 75.0); self.assertEqual((w.scale_override, w.scale_override_group), (75.0, "upper"))
        self.assertEqual(w.scale_percent(), 75.0); self.assertEqual(w.scale_for_part("UpArmCov100.STL"), (75.0, None)); self.assertEqual(w.scale_for_part("ElbowHinges100.STL"), (75.0, None))
        self.assertEqual(w.scale_for_part("TypeB-Forearm100.STL"), (70.0, None)); self.assertEqual(w.scale_for_part("PalmRH70.STL"), (None, None))
        w.custom.part_path = "TypeB-Forearm100.STL"; self.assertEqual(w.scale_percent(), w.scale_for_part("TypeB-Forearm100.STL")[0])      # unit export = full export
        w.recompute(); self.assertIn("composants inférieurs 70 % · composants supérieurs 75 % (taille forcée à la main)", w.live.toPlainText())
        w.fields["hand_mm"].setValue(190); self.assertIsNone(w.scale_override); self.assertEqual(w.scale_for_part("UpArmCov100.STL"), (w.sizing.derived["upper_scale"], None))
        self.assertEqual(w.state_dict()["scale_override_group"], None)

    def test_focus_out_on_a_part_of_the_other_group_keeps_the_forced_size(self):
        w = self.window(); w.custom.part_path = "UpArmCov100.STL"; self.force(w, 75.0)
        w.custom.part_path = "TypeB-Forearm100.STL"; w.refresh_scale_row(); self.assertEqual(w.scale_spin.value(), 70.0)
        w._scale_edited()                                                   # editingFinished on focus out, value untouched
        self.assertEqual((w.scale_override, w.scale_override_group), (75.0, "upper")); self.assertEqual(w.scale_for_part("UpArmCov100.STL"), (75.0, None))

    def test_forced_upper_size_beyond_the_tested_range_is_accepted_with_a_warning(self):
        w = self.window(); w.custom.part_path = "UpArmCov100.STL"; self.force(w, 110.0)
        self.assertEqual(w.scale_for_part("UpArmCov100.STL"), (110.0, None))
        sev, fr, ok = M.localize(w.arm_forced_warning(), "fr"); self.assertTrue(ok); self.assertEqual(sev, M.CHECK)
        self.assertIn("110 % pour les composants supérieurs", fr); self.assertIn("bras d'essai", fr)
        self.force(w, 90.0); self.assertIsNone(w.arm_forced_warning())


class KineticArmUpperAbove100(_Base):
    def test_every_b2_value_is_inside_the_upper_range_and_lower_stays_50_100(self):
        self.assertEqual(kinetic_arm.GROUP_RANGE["lower"], (50.0, 100.0)); self.assertEqual(kinetic_arm.GROUP_RANGE["upper"], (47.5, 120.0))
        lo, hi = kinetic_arm.GROUP_RANGE["upper"]
        self.assertTrue(all(lo <= v <= hi for row in kinetic_arm.CHART.values() for v in row["upper"].values()))
        self.assertEqual(kinetic_arm.part_group("UpArm100.STL"), "upper"); self.assertEqual(kinetic_arm.part_group("TypeA-Forearm100.STL"), "lower")

    def test_audit_case_upper_102_is_exported_with_a_warning(self):
        w = MainWindow(); w.select("kinetic_arm")
        for k, x in (("hand_mm", 201), ("elbow_mm", 104), ("resid_mm", 100)): w.fields[k].setValue(x)
        self.assertEqual((w.sizing.derived["lower_scale"], w.sizing.derived["upper_scale"]), (85.0, 102.0))
        self.assertEqual(w.scale_for_part("UpArm100.STL"), (102.0, None)); self.assertEqual(w.scale_for_part("TypeF-Forearm100.STL"), (85.0, None))
        self.assertIn("tableau B2 du manuel", w.live.toPlainText())
        sev, en, ok = M.localize(next(x for x in w.sizing.warnings if x.startswith("Upper scale")), "en"); self.assertTrue(ok); self.assertEqual(sev, M.CHECK)
        w.scale_override = 125.0; w.scale_override_group = "upper"; err = w.scale_for_part("UpArm100.STL")[1]
        self.assertIn("47.5–120 %", err)                                   # beyond chart B2: refused, never clamped
        w.scale_override_group = "lower"; w.scale_override = 102.0; self.assertIn("50–100 %", w.scale_for_part("TypeF-Forearm100.STL")[1])


class PhoenixSideImposed(_Base):
    def test_library_and_full_export_hold_only_the_chosen_side(self):
        w = MainWindow(); w.select("phoenix_hand"); w.side.setCurrentIndex(w.side.findData("left"))
        self.assertEqual(len(w.custom.items), 8); self.assertTrue(all(library.side_of(i["path"]) == "left" for i in w.custom.items))
        w.side.setCurrentIndex(w.side.findData("right"))
        self.assertEqual(len(w.custom.items), 8); self.assertTrue(all(library.side_of(i["path"]) == "right" for i in w.custom.items))
        w.toggle_lang(); self.assertEqual(w.side.currentData(), "right")                 # a change of language keeps the side
        seen = {}
        with mock.patch("customlab.export_all_dialog.ExportAllDialog") as D:
            D.return_value.exec.side_effect = lambda: None; w.export_all_parts(); seen = D.call_args
        items, ctx = seen.args[2], seen.args[4]
        self.assertEqual(len(items), 8); self.assertTrue(all(library.side_of(i["path"]) == "right" for i in items)); self.assertEqual(ctx["folder_suffix"], "_droite")

    def test_customised_part_of_the_other_side_blocks_the_export(self):
        w = MainWindow(); w.select("phoenix_hand"); w.side.setCurrentIndex(w.side.findData("left")); w.fields["wrist_mm"].setValue(40)
        part = Path(self.d.name) / "left" / "p.stl"; part.parent.mkdir(); slab(part); w.load_stl(str(part)); w.custom.text.setText("Léo"); w.custom.place(30, 30)
        w.go(3); self.assertIsNone(w.part_side_mismatch()); self.assertTrue(w.b_exp.isEnabled())
        w.side.setCurrentIndex(w.side.findData("right")); w.go(3)
        self.assertEqual(w.part_side_mismatch(), ("left", "right")); self.assertFalse(w.b_exp.isEnabled()); self.assertIn("pièce gauche alors que le côté choisi est droite", w.res.toPlainText())
        with self.assertRaises(Exception): w.export_to(Path(self.d.name) / "out")
        with mock.patch("customlab.gui.QMessageBox.warning") as warn, mock.patch("customlab.export_all_dialog.ExportAllDialog") as D:
            w.export_all_parts(); warn.assert_called_once(); D.assert_not_called()


if __name__ == "__main__":
    unittest.main()
