# -*- coding: utf-8 -*-
import unittest
from datetime import date

from patient_normalize import normalize_patient
from rule_engine import match


TODAY = date(2026, 10, 27)


class PatientNormalizeTest(unittest.TestCase):
    def test_ascvd_extreme_and_ultra_high_risk(self):
        ordinary = normalize_patient({"post_pci": True, "scenario": "CCS"}, TODAY)
        self.assertEqual(ordinary["ascvd_risk"], "极高危")

        ultra = normalize_patient({
            "post_pci": True, "scenario": "ACS", "post_pci_months": 3,
            "stroke_tia_history": True, "diabetes": True,
        }, TODAY)
        self.assertEqual(ultra["ascvd_risk"], "超高危")
        self.assertIn("近 12 个月内 ACS", ultra["ascvd_risk_basis"]["severe_events"])

    def test_ascvd_one_event_plus_two_factors(self):
        patient = normalize_patient({
            "post_pci": True, "scenario": "ACS", "post_pci_months": 2,
            "diabetes": True, "hypertension": True,
        }, TODAY)
        self.assertEqual(patient["ascvd_risk"], "超高危")

    def test_hf_boundaries(self):
        for value, expected in ((40, "HFrEF"), (41, "HFmrEF"), (49, "HFmrEF"), (50, "HFpEF")):
            patient = normalize_patient({"hf": True, "lvef": value}, TODAY)
            self.assertEqual(patient["hf_type"], expected)
            self.assertEqual(patient["lvef_reduced"], value <= 40)

    def test_exam_states_are_derived_from_numbers(self):
        patient = normalize_patient({"hb": 109, "plt": 99, "potassium": 5.6, "fpg": 6.1}, TODAY)
        self.assertTrue(patient["hb_low"])
        self.assertEqual(patient["plt_status"], "降低")
        self.assertEqual(patient["potassium_status"], "高")
        self.assertEqual(patient["fbg_status"], "高")

        normal = normalize_patient({"hb": 110, "plt": 100, "potassium": 3.5, "fpg": 3.9}, TODAY)
        self.assertFalse(normal["hb_low"])
        self.assertEqual(normal["plt_status"], "正常")
        self.assertEqual(normal["potassium_status"], "正常")
        self.assertEqual(normal["fbg_status"], "正常")

    def test_triple_months_only_estimated_for_continuous_triple(self):
        base = {"on_dapt": True, "on_anticoagulant": True, "post_pci_months": 5}
        continuous = normalize_patient({**base, "discharge_dapt": True, "discharge_anticoagulant": True}, TODAY)
        self.assertEqual(continuous["triple_therapy_months"], 5)
        self.assertTrue(continuous["triple_therapy_months_estimated"])

        interrupted = normalize_patient(base, TODAY)
        self.assertTrue(interrupted["triple_therapy"])
        self.assertNotIn("triple_therapy_months", interrupted)

    def test_adherence_is_drug_specific(self):
        base = {
            "post_pci": True, "scenario": "ACS", "post_pci_months": 12,
            "surgery_date": "2025-10-01", "stent_type": "药物洗脱支架×1",
            "discharge_plan": "DAPT 12个月",
        }
        patient = normalize_patient({**base, "report_context": {"adherence_events": [
            {"drug": "阿司匹林", "days": 4}, {"drug": "二甲双胍", "days": 8},
        ]}}, TODAY)
        self.assertEqual(patient["antiplatelet_stop_days"], 4)
        self.assertEqual(patient["self_stop_days"], 8)
        self.assertIn("AD-02", {x["id"] for x in match(patient)["advices"]})

        other_only = normalize_patient({**base, "report_context": {"adherence_events": [
            {"drug": "二甲双胍", "days": 8},
        ]}}, TODAY)
        self.assertNotIn("AD-02", {x["id"] for x in match(other_only)["advices"]})

        early = normalize_patient({**base, "post_pci_months": 8, "report_context": {"adherence_events": [
            {"drug": "阿司匹林", "days": 4},
        ]}}, TODAY)
        self.assertIn("RL-01", {x["id"] for x in match(early)["redlines"]})

    def test_input_is_not_mutated(self):
        original = {"post_pci": True, "report_context": {}}
        normalize_patient(original, TODAY)
        self.assertEqual(original, {"post_pci": True, "report_context": {}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
