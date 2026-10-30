# -*- coding: utf-8 -*-
import unittest

from report_builder import DISCLAIMER, build_report
from rule_engine import match


REPORT_GROUPS = {
    "summary", "comorbidity", "exam_critical", "exam_attention", "exam_normal",
    "exam_gap", "medication_gap", "drug_disease", "adjust_plan",
    "symptom_behavior", "action_plan", "followup", "references",
}


def base_patient():
    return {
        "age": 66,
        "sex": "男",
        "scenario": "ACS",
        "post_pci": True,
        "post_pci_months": 12,
        "surgery_date": "2025-10-01",
        "discharge_diagnosis": "急性 ST 段抬高型心肌梗死",
        "vessel_count": 2,
        "target_vessel": ["左主干", "前降支"],
        "stent_type": "药物洗脱支架×2",
        "discharge_plan": "DAPT 12个月",
        "ascvd_risk": "超高危",
        "report_context": {"core_completed": 7, "exam_cards": [], "medications": []},
    }


def report_for(patient):
    return build_report(patient, match(patient))


def formal_items(report):
    return (
        report["exam_critical"] + report["exam_attention"]
        + report["medication_gap"]["items"] + report["drug_disease"]["items"]
        + report["drug_disease"]["synergy"] + report["adjust_plan"]
        + report["symptom_behavior"]["symptoms"] + report["symptom_behavior"]["behavior"]
    )


class CriticalThresholdTest(unittest.TestCase):
    def critical_ids(self, **patch):
        return {x["id"] for x in match(patch)["critical"]}

    def test_hb_boundary_and_24h_drop(self):
        self.assertIn("CV-04", self.critical_ids(hb=59.9))
        self.assertNotIn("CV-04", self.critical_ids(hb=60))
        self.assertIn("CV-04", self.critical_ids(hb=80, hb_prev=100.1))
        self.assertNotIn("CV-04", self.critical_ids(hb=80, hb_prev=100))

    def test_platelet_boundary_and_drop(self):
        self.assertIn("CV-05", self.critical_ids(plt=29.9))
        self.assertNotIn("CV-05", self.critical_ids(plt=30))
        self.assertIn("CV-05", self.critical_ids(plt=100, plt_drop_over_50pct=True))

    def test_potassium_boundaries(self):
        for value in (2.5, 6.5):
            self.assertIn("CV-01", self.critical_ids(potassium=value))
        for value in (2.51, 6.49):
            self.assertNotIn("CV-01", self.critical_ids(potassium=value))

    def test_sodium_boundaries(self):
        for value in (120, 160):
            self.assertIn("CV-02", self.critical_ids(sodium=value))
        for value in (120.1, 159.9):
            self.assertNotIn("CV-02", self.critical_ids(sodium=value))

    def test_inr_requires_warfarin_and_over_45(self):
        self.assertNotIn("CV-07", self.critical_ids(inr=5))
        self.assertNotIn("CV-07", self.critical_ids(inr=4.5, on_warfarin=True))
        self.assertIn("CV-07", self.critical_ids(inr=4.6, on_warfarin=True))

    def test_scr_uses_fifty_percent_rise(self):
        self.assertIn("CV-06", self.critical_ids(scr=150, baseline_scr=100))
        self.assertNotIn("CV-06", self.critical_ids(scr=149, baseline_scr=100))
        self.assertNotIn("CV-06", self.critical_ids(scr=126.5, baseline_scr=100))

    def test_glucose_boundaries(self):
        for value in (2.8, 22.2):
            self.assertIn("CV-13", self.critical_ids(fpg=value))
        for value in (2.81, 22.19):
            self.assertNotIn("CV-13", self.critical_ids(fpg=value))

    def test_co2cp_boundary(self):
        self.assertIn("CV-12", self.critical_ids(co2cp=10))
        self.assertNotIn("CV-12", self.critical_ids(co2cp=10.1))


class ReportBuilderTest(unittest.TestCase):
    def test_required_groups_and_fixed_disclaimer(self):
        report = report_for(base_patient())
        self.assertTrue(REPORT_GROUPS <= set(report))
        self.assertEqual(report["references"]["disclaimer"], DISCLAIMER)
        self.assertLessEqual(len(report["summary"]["portrait"]), 120)
        self.assertEqual(report["summary"]["core_completed"], 7)
        self.assertEqual(report["summary"]["exam_total"], 13)

    def test_all_formal_items_have_five_elements_and_sources(self):
        patient = base_patient()
        patient.update({
            "hypertension_grade": "2级", "diabetes": True, "ckd": True,
            "ckd_stage": "3b期", "egfr": 42, "potassium": 6.5, "hb": 82,
            "current_ldl": 3.8, "baseline_ldl": 4.2, "lvef": 38,
            "lvef_reduced": True, "hf": True, "hf_type": "HFrEF", "on_dapt": True,
        })
        patient["report_context"].update({
            "exam_cards": ["cbc", "renal", "lipid", "echo", "potassium"],
            "medications": [
                {"key": "aspirin", "name": "阿司匹林", "category": "抗血小板药物", "now": 100},
                {"key": "clopidogrel", "name": "氯吡格雷", "category": "抗血小板药物", "now": 75},
                {"key": "atorvastatin", "name": "阿托伐他汀", "category": "降脂药物", "now": 20},
            ],
        })
        report = report_for(patient)
        self.assertEqual(report["summary"]["counts"]["critical"], len(report["exam_critical"]))
        self.assertEqual(report["summary"]["counts"]["attention"], len(report["exam_attention"]))
        self.assertEqual(report["summary"]["counts"]["behavior"], len(report["symptom_behavior"]["symptoms"]) + len(report["symptom_behavior"]["behavior"]))
        self.assertGreater(report["summary"]["counts"]["medication"], 0)
        self.assertEqual(report["summary"]["risk_level"], "red")
        self.assertEqual(report["exam_critical"][0]["evidence"].split("；")[0], "6.5 mmol/L")
        self.assertTrue(any(x["timing"].startswith("处理后 4–6 小时") for x in report["followup"]["schedule"]))
        for item in formal_items(report):
            for key in ("conclusion", "evidence", "impact", "action", "timeframe", "source"):
                self.assertTrue(str(item.get(key, "")).strip(), (item.get("id"), key))
        self.assertEqual(report["unresolved"], [])

    def test_attention_severity_and_sorting(self):
        patient = base_patient()
        patient.update({
            "hb": 82, "plt": 60, "egfr": 42, "current_ldl": 3.8,
            "heart_rate": 52, "qtc": 490, "alt_ast_status": "轻度升高",
        })
        report = report_for(patient)
        def severity(prefix):
            return next(x["severity"] for x in report["exam_attention"] if x["conclusion"].startswith(prefix))

        self.assertEqual(severity("血红蛋白"), "中度")
        self.assertEqual(severity("血小板"), "中度")
        self.assertEqual(severity("eGFR"), "中度")
        self.assertEqual(severity("LDL-C"), "重度")
        self.assertEqual(severity("心率"), "重度")
        self.assertEqual(severity("QTc"), "中度")
        self.assertEqual(severity("ALT/AST"), "轻度")
        order = {"重度": 0, "中度": 1, "轻度": 2}
        severities = [order[x["severity"]] for x in report["exam_attention"]]
        self.assertEqual(severities, sorted(severities))

    def test_normal_confirmation_does_not_include_missing_values(self):
        patient = base_patient()
        patient.update({
            "hb": 120, "plt": 120, "plt_status": "正常", "egfr": 95,
            "current_ldl": 1.2, "heart_rate": 70, "qtc": 430,
            "potassium": 4.2, "potassium_status": "正常", "sodium": 140, "fpg": 5,
        })
        report = report_for(patient)
        self.assertEqual(report["exam_normal"]["count"], 9)
        self.assertIn("未触发异常阈值", report["exam_normal"]["text"])
        self.assertNotIn("肝功能", report["exam_normal"]["text"])

    def test_information_gaps_are_explicit(self):
        patient = base_patient()
        patient.update({"scr": 120, "hb": 82, "alt_ast_status": "中度升高", "current_ldl": None})
        report = report_for(patient)
        gaps = {x["missing"] for x in report["exam_gap"]}
        self.assertIn("PCI 术前 48–72 小时基线血肌酐", gaps)
        self.assertIn("24 小时前血红蛋白", gaps)
        self.assertIn("本次 LDL-C", gaps)
        self.assertIn("ALT/AST 相对正常上限倍数与本院参考范围", gaps)
        for gap in report["exam_gap"]:
            self.assertTrue(gap["impact"])
            self.assertTrue(gap["action"])

    def test_symptoms_behavior_counts_and_action_numbers(self):
        patient = base_patient()
        patient.update({"post_pci_months": 8, "red_flag": True, "chest_pain": True, "self_stop_days": 3})
        patient["report_context"].update({
            "symptoms": [{"key": "sym_chest", "label": "持续胸痛", "severity": "red", "bleeding": False}],
            "bleeding_events": [],
            "adherence_events": [{"drug": "阿司匹林", "days": 3}],
            "adrs": [],
        })
        report = report_for(patient)
        behavior = report["symptom_behavior"]
        self.assertEqual(report["summary"]["counts"]["behavior"], len(behavior["symptoms"]) + len(behavior["behavior"]))
        self.assertTrue(any(x["severity"] == "critical" for x in behavior["symptoms"]))
        for level in report["action_plan"]["levels"]:
            expected = [f"{level['title'].split('·')[0]}-{i}" for i in range(1, len(level["items"]) + 1)]
            self.assertEqual([x["number"] for x in level["items"]], expected)
            for item in level["items"]:
                self.assertTrue(item["ref"])
        self.assertEqual(report["summary"]["risk_level"], "red")

    def test_no_symptoms_has_positive_confirmation(self):
        report = report_for(base_patient())
        self.assertIn("未报告红旗症状", report["symptom_behavior"]["confirmation"])
        self.assertEqual(report["symptom_behavior"]["symptoms"], [])

    def test_green_and_yellow_symptoms_have_distinct_triage(self):
        green = base_patient()
        green["report_context"]["symptoms"] = [{"key": "sym_reflux", "label": "反酸恶心", "severity": "green", "bleeding": False}]
        green_report = report_for(green)
        item = next(x for x in green_report["symptom_behavior"]["symptoms"] if x["id"] == "TRIAGE-sym_reflux")
        self.assertEqual(item["priority"], 3)
        self.assertEqual(item["severity"], "normal")
        self.assertEqual(green_report["followup"]["referral"], [])

        yellow = base_patient()
        yellow["report_context"]["symptoms"] = [{"key": "sym_dyspnea", "label": "胸闷气短加重", "severity": "yellow", "bleeding": False}]
        yellow_report = report_for(yellow)
        item = next(x for x in yellow_report["symptom_behavior"]["symptoms"] if x["id"] == "TRIAGE-sym_dyspnea")
        self.assertEqual(item["priority"], 2)
        self.assertIn("尽快转诊", item["conclusion"])

    def test_medication_frequency_is_shown(self):
        patient = base_patient()
        patient.update({"post_pci_months": 3, "on_dapt": True})
        patient["report_context"]["medications"] = [
            {"name": "阿司匹林", "category": "抗血小板药物", "now": 100, "nowFrequency": "qd"},
            {"name": "替格瑞洛", "category": "抗血小板药物", "now": 90, "nowFrequency": "bid"},
        ]
        report = report_for(patient)
        evidence = next(x for x in report["medication_gap"]["items"] if x["id"] == "AP-CHECK")["evidence"]
        self.assertIn("阿司匹林 100 mg qd", evidence)
        self.assertIn("替格瑞洛 90 mg bid", evidence)

    def test_reference_list_contains_only_used_sources(self):
        patient = base_patient()
        patient["current_ldl"] = 1.2
        report = report_for(patient)
        references = report["references"]["sources"]
        codes = {x["code"] for x in references}
        self.assertIn("CN-01", codes)
        self.assertIn("CN-04", codes)
        for source in references:
            self.assertTrue(source["name"])
            self.assertNotEqual(source["name"], f"规则库来源 {source['code']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
