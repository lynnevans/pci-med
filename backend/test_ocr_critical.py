# -*- coding: utf-8 -*-
"""OCR 映射 → 危急值闭环的纯 Python 单元测试（不依赖网络/图片/第三方库）。

运行：
    cd backend
    .\\venv\\Scripts\\python.exe -m unittest test_ocr_critical -v

覆盖：
- 一条识别项派生多个字段（钾 → potassium + potassium_status；血红蛋白 → hb + hb_low）
- 单位不一致时不误填数值，但仍能从箭头派生状态
- 单字别名不误吃（脑钠肽 ≠ 钠）
- 白细胞计数不误映射成血小板
- 映射结果喂给 rule_engine 后能命中 CV-01/02/04/05/07/08/11/12
"""
import unittest

from ocr_map import SPECS, map_items
from rule_engine import match

CRITICAL_ITEMS = [
    {"item": "钾", "value": "6.5", "unit": "mmol/L", "ref_range": "3.5-5.3", "flag": "high"},
    {"item": "钠", "value": "118", "unit": "mmol/L", "ref_range": "137-147", "flag": "low"},
    {"item": "血红蛋白", "value": "55", "unit": "g/L", "ref_range": "130-175", "flag": "low"},
    {"item": "血小板计数", "value": "15", "unit": "×10^9/L", "ref_range": "125-350", "flag": "low"},
    {"item": "INR", "value": "4.8", "unit": "", "ref_range": "0.8-1.2", "flag": "high"},
    {"item": "纤维蛋白原", "value": "0.6", "unit": "g/L", "ref_range": "2.0-4.0", "flag": "low"},
    {"item": "高敏肌钙蛋白T", "value": "0.12", "unit": "ng/mL", "ref_range": "0-0.014", "flag": "high"},
    {"item": "二氧化碳结合率", "value": "10", "unit": "mmol/L", "ref_range": "22-29", "flag": "low"},
    {"item": "肌酐", "value": "150", "unit": "μmol/L", "ref_range": "57-97", "flag": "high"},
    {"item": "低密度脂蛋白胆固醇", "value": "3.21", "unit": "mmol/L", "ref_range": "2.60-3.40", "flag": "normal"},
    {"item": "糖化血红蛋白", "value": "6.2", "unit": "%", "ref_range": "4.0-6.0", "flag": "high"},
    {"item": "丙氨酸氨基转移酶", "value": "68", "unit": "U/L", "ref_range": "9-50", "flag": "high"},
    {"item": "天门冬氨酸氨基转移酶", "value": "42", "unit": "U/L", "ref_range": "15-40", "flag": "high"},
    {"item": "总胆红素", "value": "28.5", "unit": "μmol/L", "ref_range": "3.4-20.5", "flag": "high"},
    {"item": "葡萄糖", "value": "6.4", "unit": "mmol/L", "ref_range": "3.9-6.1", "flag": "high"},
    {"item": "白细胞计数", "value": "6.8", "unit": "×10^9/L", "ref_range": "3.5-9.5", "flag": "normal"},
]


def fields_of(items, conclusion=""):
    return {f["field"]: f for f in map_items(items, conclusion)["fields"]}


class OcrCriticalMappingTest(unittest.TestCase):
    def test_specs_are_consistent(self):
        fields = [s["field"] for s in SPECS]
        self.assertEqual(len(fields), len(set(fields)), "字段名不能重复")
        for spec in SPECS:
            for derive in spec.get("derive", []):
                self.assertIn(derive["field"], fields, "派生目标必须存在")

    def test_one_item_derives_multiple_fields(self):
        f = fields_of(CRITICAL_ITEMS)
        self.assertEqual(f["potassium"]["value"], 6.5)
        self.assertEqual(f["potassium_status"]["value"], "高")
        self.assertEqual(f["hb"]["value"], 55.0)
        self.assertIs(f["hb_low"]["value"], True)
        self.assertEqual(f["plt"]["value"], 15.0)
        self.assertEqual(f["plt_status"]["value"], "降低")
        self.assertEqual(f["inr"]["value"], 4.8)
        self.assertIs(f["coag_abnormal"]["value"], True)
        self.assertEqual(f["hs_ctnt"]["value"], 0.12)
        self.assertIs(f["troponin_elevated"]["value"], True)

    def test_critical_values_from_ocr(self):
        f = fields_of(CRITICAL_ITEMS)
        patch = {k: v["value"] for k, v in f.items()}
        patch.update({"post_pci": True, "on_warfarin": True, "chest_pain": True})
        ids = {c["id"] for c in match(patch)["critical"]}
        self.assertTrue(
            {"CV-01", "CV-02", "CV-04", "CV-05", "CV-07", "CV-08", "CV-11", "CV-12"} <= ids,
            ids,
        )

    def test_normal_potassium_has_no_critical(self):
        f = fields_of([{"item": "钾", "value": "4.2", "unit": "mmol/L",
                        "ref_range": "3.5-5.3", "flag": "normal"}])
        self.assertEqual(f["potassium_status"]["value"], "正常")
        self.assertEqual(match({"potassium": f["potassium"]["value"]})["critical"], [])

    def test_unit_mismatch_keeps_derived_flag_but_skips_number(self):
        # 血红蛋白 8 g/dL 是低值，但单位不是 g/L：数值不回填，hb_low 仍应为 True
        f = fields_of([{"item": "血红蛋白", "value": "8", "unit": "g/dL",
                        "ref_range": "13-17", "flag": "low"}])
        self.assertNotIn("hb", f)
        self.assertEqual(f["hb_low"]["value"], True)

    def test_ldl_mg_dl_is_not_silently_filled(self):
        result = map_items([{"item": "LDL-C", "value": "124", "unit": "mg/dL",
                             "ref_range": "0-130", "flag": "normal"}])
        self.assertEqual(result["fields"], [])
        self.assertTrue(any("mg/dL" in u["reason"] for u in result["unmatched"]))

    def test_single_char_alias_does_not_match_bnp(self):
        result = map_items([{"item": "脑钠肽", "value": "500", "unit": "pg/mL",
                             "ref_range": "0-100", "flag": "high"}])
        self.assertNotIn("sodium", {f["field"] for f in result["fields"]})

    def test_wbc_is_not_platelet(self):
        f = fields_of([{"item": "白细胞计数", "value": "6.8", "unit": "×10^9/L",
                        "ref_range": "3.5-9.5", "flag": "normal"}])
        self.assertEqual(f["wbc"]["value"], 6.8)
        self.assertNotIn("plt", f)

    def test_new_exam_fields_are_mapped(self):
        f = fields_of([
            {"item": "总胆红素", "value": "18", "unit": "μmol/L", "ref_range": "3.4-20.5", "flag": "normal"},
            {"item": "白蛋白", "value": "42", "unit": "g/L", "ref_range": "40-55", "flag": "normal"},
            {"item": "D-二聚体", "value": "0.3", "unit": "mg/L", "ref_range": "0-0.5", "flag": "normal"},
            {"item": "肌酸激酶同工酶", "value": "16", "unit": "U/L", "ref_range": "0-24", "flag": "normal"},
            {"item": "PR间期", "value": "160", "unit": "ms", "ref_range": "120-200", "flag": "normal"},
            {"item": "QRS波时限", "value": "90", "unit": "ms", "ref_range": "60-100", "flag": "normal"},
        ])
        expected = {"bilirubin": 18, "albumin": 42, "d_dimer": 0.3,
                    "ck_mb": 16, "pr_interval": 160, "qrs_duration": 90}
        for field, value in expected.items():
            self.assertEqual(f[field]["value"], value)

    def test_egfr_does_not_fill_crcl(self):
        f = fields_of([{"item": "eGFR", "value": "72", "unit": "ml/min/1.73m²",
                        "ref_range": ">90", "flag": "normal"}])
        self.assertEqual(f["egfr"]["value"], 72)
        self.assertNotIn("crcl", f)

    def test_coag_variants_from_real_reports(self):
        # 真实单上的写法：少一个「活」字 + 仪器后缀；TT / APTT 比值也应算凝血异常
        f = fields_of([
            {"item": "活化部分凝血酶时间 (CP3000)", "value": "45", "unit": "s",
             "ref_range": "25-37", "flag": "high"},
            {"item": "凝血酶时间比值", "value": "1.05", "unit": "",
             "ref_range": "0.8-1.2", "flag": "normal"},
        ])
        self.assertTrue(f["coag_abnormal"]["value"])

    def test_pt_activity_is_not_auto_mapped(self):
        # PT 活动度是「越低越异常」的逆向指标，不能按 flag==high 直接置 coag_abnormal
        result = map_items([{"item": "凝血酶原活动度", "value": "55", "unit": "%",
                             "ref_range": "70-130", "flag": "low"}])
        self.assertEqual(result["fields"], [])

    def test_ecg_heart_rate_and_qtc(self):
        # QT/QTc 用 380/520：QTc 必须取 520，不能取 380
        f = fields_of([
            {"item": "心率(脉HR)", "value": "35", "unit": "次/分",
             "ref_range": "60-100", "flag": "low"},
            {"item": "QT/QTc间期", "value": "380/520", "unit": "ms",
             "ref_range": "", "flag": "high"},
        ], conclusion="窦性心律，ST-T 改变")
        self.assertEqual(f["heart_rate"]["value"], 35.0)
        self.assertEqual(f["qtc"]["value"], 520.0)
        self.assertIs(f["sinus_rhythm"]["value"], True)

        ids = {c["id"] for c in match({"heart_rate": 35, "qtc": 520})["critical"]}
        self.assertTrue({"CV-09", "CV-10"} <= ids, ids)

    def test_ecg_qtc_delta_from_baseline(self):
        # QTc 480 本身没到 500，但比基线 400 增加 80ms，仍触发 CV-09
        self.assertEqual(match({"qtc": 480})["critical"], [])
        ids = {c["id"] for c in match({"qtc": 480, "qtc_baseline": 400})["critical"]}
        self.assertIn("CV-09", ids)

    def test_ecg_conclusion_variants(self):
        self.assertIs(fields_of([], "窦性心动过缓")["sinus_rhythm"]["value"], True)
        self.assertIs(fields_of([], "心房颤动")["sinus_rhythm"]["value"], False)
        self.assertIs(fields_of([], "非窦性心律")["sinus_rhythm"]["value"], False)
        self.assertNotIn("sinus_rhythm", fields_of([], ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
