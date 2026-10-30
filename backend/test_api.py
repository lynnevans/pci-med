# -*- coding: utf-8 -*-
"""不依赖外部服务的 /api/analyze 接口测试。"""
import unittest

from fastapi.testclient import TestClient

from api import app


def base_payload():
    return {
        "scenario": "ACS",
        "post_pci": True,
        "post_pci_months": 12,
        "age": 62,
        "sex": "男",
        "surgery_date": "2025-10-01",
        "stent_type": "药物洗脱支架×2",
        "discharge_plan": "DAPT 12个月",
        "report_context": {"medications": [], "symptoms": [], "adherence_events": []},
    }


class AnalyzeApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_full_payload_medications_and_three_level_triage(self):
        payload = base_payload()
        payload.update({
            "post_pci_months": 3,
            "on_dapt": True,
            "discharge_dapt": True,
            "on_anticoagulant": True,
            "discharge_anticoagulant": True,
            "red_flag": True,
            "report_context": {
                "medications": [
                    {"key": "aspirin", "name": "阿司匹林", "category": "抗血小板药物",
                     "discharge": 100, "dischargeFrequency": "qd", "now": 100, "nowFrequency": "qd"},
                    {"key": "custom-ac", "name": "阿哌沙班", "category": "口服抗凝药",
                     "discharge": 5, "dischargeFrequency": "bid", "now": 5, "nowFrequency": "bid"},
                    {"key": "custom-other", "name": "辅酶 Q10", "category": "其他药物",
                     "discharge": 10, "dischargeFrequency": "qd", "now": 10, "nowFrequency": "tid"},
                ],
                "symptoms": [
                    {"key": "sym_reflux", "label": "反酸恶心", "severity": "green", "bleeding": False},
                    {"key": "sym_dyspnea", "label": "胸闷气短加重", "severity": "yellow", "bleeding": False},
                    {"key": "sym_chest", "label": "持续胸痛", "severity": "red", "bleeding": False},
                ],
                "adherence_events": [
                    {"drug": "阿司匹林", "days": 4},
                    {"drug": "二甲双胍", "days": 8},
                ],
            },
        })
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        patient = data["normalized_patient"]
        report = data["report"]
        self.assertEqual(patient["ascvd_risk"], "极高危")
        self.assertEqual(patient["antiplatelet_stop_days"], 4)
        self.assertEqual(patient["self_stop_days"], 8)
        self.assertEqual(patient["triple_therapy_months"], 3)
        self.assertTrue(patient["triple_therapy_months_estimated"])

        evidence = next(x for x in report["medication_gap"]["items"] if x["id"] == "AP-CHECK")["evidence"]
        self.assertIn("阿司匹林 100 mg qd", evidence)
        medication_summary = report["medication_gap"]["summary"]
        self.assertIn("阿司匹林（出院 100 mg qd；当前 100 mg qd）", medication_summary)
        self.assertIn("阿哌沙班（出院 5 mg bid；当前 5 mg bid）", medication_summary)
        self.assertIn("辅酶 Q10（出院 10 mg qd；当前 10 mg tid）", medication_summary)
        symptoms = {x["id"]: x for x in report["symptom_behavior"]["symptoms"]}
        self.assertIn("【立即急诊】", symptoms["TRIAGE-sym_chest"]["conclusion"])
        self.assertIn("【尽快转诊】", symptoms["TRIAGE-sym_dyspnea"]["conclusion"])
        self.assertIn("【基层随访】", symptoms["TRIAGE-sym_reflux"]["conclusion"])
        self.assertTrue(any("立即急诊" in x for x in report["followup"]["referral"]))
        behavior = "\n".join(x["evidence"] + x["conclusion"] for x in report["symptom_behavior"]["behavior"])
        self.assertIn("阿司匹林 已停/漏服 4 天", behavior)
        self.assertIn("二甲双胍 已停/漏服 8 天", behavior)

    def test_other_drug_stop_does_not_trigger_antiplatelet_rule(self):
        payload = base_payload()
        payload["report_context"]["adherence_events"] = [{"drug": "二甲双胍", "days": 8}]
        data = self.client.post("/api/analyze", json=payload).json()
        self.assertEqual(data["normalized_patient"]["self_stop_days"], 8)
        self.assertNotIn("antiplatelet_stop_days", data["normalized_patient"])
        self.assertNotIn("AD-02", {x["id"] for x in data["advices"]})

    def test_antiplatelet_stop_after_twelve_months_triggers_ad02(self):
        payload = base_payload()
        payload["report_context"]["adherence_events"] = [{"drug": "阿司匹林", "days": 4}]
        data = self.client.post("/api/analyze", json=payload).json()
        self.assertIn("AD-02", {x["id"] for x in data["advices"]})

    def test_interrupted_or_non_discharge_triple_does_not_estimate_months(self):
        payload = base_payload()
        payload.update({"on_dapt": True, "on_anticoagulant": True})
        data = self.client.post("/api/analyze", json=payload).json()
        self.assertTrue(data["normalized_patient"]["triple_therapy"])
        self.assertNotIn("triple_therapy_months", data["normalized_patient"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
