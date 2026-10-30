# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import OrderedDict


DISCLAIMER = "本报告由计算机辅助生成，仅供具有执业资质的医师临床参考，不构成诊断或处方；最终决策请结合患者实际情况与临床判断。危急值与红旗症状的处理请遵循本院危急值报告制度。"

SOURCES = {
    "TEMPLATE": "PCI术后用药管理助手分析结果报告输出模板 V1.0",
    "CN-01": "经皮冠状动脉介入治疗指南（2025）",
    "CN-02": "中国慢性冠脉综合征患者诊断及管理指南",
    "CN-03": "冠心病双联抗血小板治疗中国专家共识",
    "CN-04": "中国血脂管理指南（2023年）",
    "CN-05": "心房颤动诊断和治疗中国指南",
    "CN-06": "稳定性冠心病基层合理用药指南",
    "CN-07": "口服抗栓药物相关消化道损伤防治专家共识",
    "CN-08": "中国糖尿病防治指南（2024版）",
    "EN-01": "2024 ESC Guidelines for the management of chronic coronary syndromes",
    "心衰指南": "中国心力衰竭诊断和治疗指南2024",
    "说明书": "相关药品说明书（以实际品种最新版为准）",
    "心内": "心内科规则库（原始出处标识，需专科核对）",
    "CN": "项目指南数据库（原始来源编号 CN）",
}

DOMAIN_IMPACT = {
    "抗血小板": "影响支架内血栓、再发缺血与出血风险。",
    "调脂": "影响动脉粥样硬化进展与长期心血管预后。",
    "抗缺血": "影响心肌缺血控制与长期心脏预后。",
    "合并症": "合并症与用药相互影响，可能改变抗栓安全性或长期预后。",
    "随访": "影响异常变化的及时发现与长期治疗安全性。",
    "用药行为": "漏服或自行停药可能增加血栓、缺血或出血风险。",
    "接诊信息": "关键信息缺失会导致疗程和方案判断不可靠。",
    "出血处理": "影响出血控制与抗栓治疗安全性。",
    "临时用药": "临时用药或检查可能与现有治疗产生相互影响。",
    "下转衔接": "影响下转后方案连续执行与异常及时发现。",
    "血压协同": "影响血压达标与心血管长期预后。",
    "老年": "老年患者的缺血、出血与药物不良反应风险需要共同权衡。",
    "ADR判读": "异常指标可能提示药物不良反应或疾病进展。",
    "降压药ADR": "症状与指标异常可能与降压药相关，影响治疗安全性。",
    "用药变化": "术后疗程内自行降级可能增加支架内血栓风险。",
}

RULE_TIMEFRAMES = {
    "LP-04": "本次随访调整；4–6 周复查",
    "LP-05": "本次随访评估；4–6 周复查",
    "LP-06": "本次随访评估；4–6 周复查",
    "LP-07": "本次随访调整；4–6 周复查",
    "LP-08": "启动/调整后 4–6 周",
    "EL-01": "本次随访；4–6 周复查",
    "LB-01": "本次随访；4 周复查肝功能",
    "LB-03": "本次随访暂停并复查",
    "LB-06": "立即复核；24 小时内完成评估",
    "LB-08": "立即纠正并评估诱因",
    "HT-01": "立即复查血钾与心电图",
    "HT-02": "立即纠正并复查电解质",
    "CM-11": "每 6 个月；有症状随时",
    "CX-02": "本次随访；1–2 周复查",
    "JC-03": "检查前 48 小时至检查后 48 小时",
    "AD-02": "立即联系并恢复原方案评估",
}

CRITICAL_DETAILS = {
    "CV-01": ("potassium", "mmol/L", "≤2.5 或 ≥6.5 mmol/L", "显著增加心律失常风险；使用 ACEI/ARB/ARNI 或螺内酯者需立即复核。", "立即复查确认，纠正诱因并由医师调整相关药物；按本院危急值制度上报。", "立即处理；处理后 4–6 小时复查"),
    "CV-02": ("sodium", "mmol/L", "≤120 或 ≥160 mmol/L", "可能导致意识障碍、抽搐，并影响整体治疗安全。", "立即复查并由医师谨慎纠正，避免纠正过快；按本院危急值制度上报。", "立即处理并按医嘱复查"),
    "CV-03": ("calcium_corrected", "mmol/L", "<1.9 或 >2.9 mmol/L", "可能导致手足搐搦、心律失常或意识改变。", "立即复查并评估病因及处理；按本院危急值制度上报。", "立即处理"),
    "CV-04": ("hb", "g/L", "<60 g/L，或 24 小时下降 >20 g/L", "显著降低心肌供氧并提示活动性出血可能，直接影响抗栓安全。", "立即评估出血原因、输血指征与抗栓方案；按本院危急值制度上报。", "立即处理"),
    "CV-05": ("plt", "×10⁹/L", "<30×10⁹/L，或较基线下降 >50%", "自发出血风险显著升高，并可能提示药物相关血小板减少。", "立即复查并由专科评估出血原因与抗栓方案；按本院危急值制度上报。", "立即处理"),
    "CV-06": ("scr", "μmol/L", "较 48–72 小时基线上升 ≥50%", "提示急性肾损伤，可能影响抗凝、二甲双胍等药物安全。", "立即复核肾功能，评估肾毒性药物与容量状态；按本院危急值制度上报。", "立即处理并复查肾功能"),
    "CV-07": ("inr", "", ">4.5（华法林使用者）", "出血风险显著升高，需及时调整抗凝方案。", "立即复查并由医师调整华法林方案；按本院危急值制度上报。", "立即处理"),
    "CV-08": ("fibrinogen", "g/L", "<1.0 g/L", "出血倾向明显增加，影响抗栓治疗安全。", "立即复查并评估凝血异常原因与处理；按本院危急值制度上报。", "立即处理"),
    "CV-09": ("qtc", "ms", ">500 ms，或较基线增加 >60 ms", "尖端扭转型室速风险增加，需核对抗心律失常药等诱因。", "立即复核心电图、电解质及 QT 延长药物；按本院危急值制度上报。", "立即处理"),
    "CV-10": ("heart_rate", "次/分", "<40 或 >130 次/分", "可能存在严重传导阻滞或快速心律失常。", "立即复查心电图和电解质并评估转诊；按本院危急值制度上报。", "立即处理"),
    "CV-11": ("hs_ctnt", "ng/mL", ">0.07 ng/mL 且伴胸痛", "提示急性心肌损伤，需警惕支架内血栓或再发 ACS。", "立即转诊评估，复查心电图、肌钙蛋白并由专科决定是否造影。", "立即处理"),
    "CV-12": ("co2cp", "mmol/L", "≤10 mmol/L", "提示严重代谢性酸中毒可能，可伴随肾功能恶化。", "立即复查并评估酸中毒病因；按本院危急值制度上报。", "立即处理"),
    "CV-13": ("fpg", "mmol/L", "≤2.8 或 ≥22.2 mmol/L", "严重低血糖或高血糖可诱发心肌缺血并危及生命。", "立即复查血糖，按低血糖或高血糖急症流程处理。", "立即处理"),
}

CRITICAL_KEYS = {
    "CV-01": {"potassium"}, "CV-02": {"sodium"}, "CV-03": {"calcium_corrected"},
    "CV-04": {"hb"}, "CV-05": {"plt"}, "CV-06": {"scr"}, "CV-07": {"inr"},
    "CV-08": {"fibrinogen"}, "CV-09": {"qtc"}, "CV-10": {"heart_rate"},
    "CV-11": {"hs_ctnt", "troponin"}, "CV-12": {"co2cp"}, "CV-13": {"fpg"},
}

EXAM_CARD_FIELDS = {
    "cbc": {"hb", "hb_prev", "hb_low", "plt", "plt_status", "plt_drop_over_50pct", "wbc"},
    "urine": {"urine_protein", "brown_urine"},
    "liver": {"alt", "ast", "bilirubin", "albumin", "alt_ast_status", "jaundice"},
    "renal": {"scr", "egfr"},
    "coag": {"coag_abnormal", "pt", "aptt", "tt", "inr", "fibrinogen", "d_dimer"},
    "enzyme": {"ck_mb"},
    "troponin": {"troponin_value", "troponin_elevated", "hs_ctnt"},
    "potassium": {"potassium", "potassium_status"},
    "lipid": {"baseline_ldl", "current_ldl", "tc", "tg", "hdl", "lipid_abnormal"},
    "glucose": {"fpg", "fbg_status", "hba1c"},
    "bnp": {"bnp", "bnp_state"},
    "ecg": {"st_t", "arrhythmia_type", "arrhythmia", "hr_abnormal", "heart_rate", "pr_interval", "qrs_duration"},
    "echo": {"lvef", "wall_aneurysm", "wall_motion", "wall_abnormality", "echo_other"},
}

EXAM_CARD_NAMES = {
    "cbc": "血常规", "urine": "尿常规", "liver": "肝功能", "renal": "肾功能",
    "coag": "凝血功能", "enzyme": "心肌酶谱", "troponin": "肌钙蛋白",
    "potassium": "电解质", "lipid": "血脂", "glucose": "空腹血糖和糖化血红蛋白",
    "bnp": "B型前脑尿钠肽", "ecg": "十二导联心电图", "echo": "超声心动图",
}

ADJUST_IDS = {
    "AP-03", "AP-04", "AP-06", "AP-07", "AP-08", "AP-09", "AP-10", "AP-11",
    "LP-03", "LP-04", "LP-05", "LP-06", "LP-07", "IC-01", "IC-02", "IC-03",
    "IC-04", "IC-05", "IC-06", "CM-01", "CM-02", "CM-03", "CM-04", "CM-06",
    "CM-07", "CM-08", "CM-09", "CX-05", "HT-01", "HT-02", "HT-03", "HT-04",
    "HT-05", "EL-01", "EL-03", "MC-01", "JC-03",
}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _value(patient, key, unit=""):
    value = patient.get(key)
    if value is None or value == "":
        return "未录入"
    return f"{value}{(' ' + unit) if unit else ''}"


def _circled(index):
    chars = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    return chars[index - 1] if index <= len(chars) else str(index)


def _current_medications(patient):
    context = patient.get("report_context") or {}
    medications = context.get("medications")
    if medications is not None:
        return [m for m in medications if _number(m.get("now")) and m.get("now") > 0]
    result = []
    for key, name in (("aspirin", "阿司匹林"), ("indobufen", "吲哚布芬"), ("clopidogrel", "氯吡格雷"), ("ticagrelor", "替格瑞洛")):
        if patient.get("on_" + key):
            result.append({"key": key, "name": name, "category": "抗血小板药物", "now": patient.get(key + "_dose")})
    for key, field, category in (("beta_blocker_type", "on_beta_blocker", "β 受体阻滞剂"), ("acei_arb_type", "on_acei_arb", "ARNI / ACEI / ARB"), ("diuretic_type", "on_diuretic", "利尿剂")):
        if patient.get(field) and patient.get(key):
            result.append({"key": field, "name": patient[key], "category": category, "now": None})
    if patient.get("on_statin"):
        result.append({"key": "statin", "name": "他汀（品种未传）", "category": "降脂药物", "now": None})
    if patient.get("on_metformin"):
        result.append({"key": "metformin", "name": "二甲双胍", "category": "降糖药物", "now": None})
    if patient.get("ppi"):
        result.append({"key": "ppi", "name": patient["ppi"], "category": "质子泵抑制剂", "now": None})
    return result


def _medication_text(medications, category=None):
    selected = [m for m in medications if category is None or category in (m.get("category") or "")]
    if not selected:
        return "未使用/未录入"
    parts = []
    for med in selected:
        dose = f" {med['now']} mg" if _number(med.get("now")) and med.get("now") > 0 else ""
        frequency = f" {med['nowFrequency']}" if dose and med.get("nowFrequency") else ""
        parts.append((med.get("name") or "未命名药物") + dose + frequency)
    return "、".join(parts)


def _medication_record_text(medications):
    """完整列出每种药的出院与当前剂量、频次，包含用户自行添加的药。"""
    if not medications:
        return "未使用/未录入"
    records = []
    for med in medications:
        phases = []
        for phase, label in (("discharge", "出院"), ("now", "当前")):
            dose = med.get(phase)
            frequency = med.get(phase + "Frequency")
            value = f"{dose} mg" if _number(dose) and dose > 0 else "未使用/未录入"
            if _number(dose) and dose > 0 and frequency:
                value += f" {frequency}"
            phases.append(f"{label} {value}")
        records.append(f"{med.get('name') or '未命名药物'}（{'；'.join(phases)}）")
    return "；".join(records)


def _rule_evidence(rule_id, patient, medications):
    prefix = rule_id.split("-")[0]
    if prefix == "AP":
        return f"诊断 {patient.get('discharge_diagnosis') or patient.get('scenario') or '未录入'}；术后 {_value(patient, 'post_pci_months', '个月')}；当前抗血小板：{_medication_text(medications, '抗血小板')}。"
    if prefix == "LP":
        return f"ASCVD {patient.get('ascvd_risk') or '未录入'}；基线 LDL-C {_value(patient, 'baseline_ldl', 'mmol/L')}；本次 {_value(patient, 'current_ldl', 'mmol/L')}；当前降脂：{_medication_text(medications, '降脂')}。"
    if prefix == "IC":
        return f"LVEF {_value(patient, 'lvef', '%')}；心率 {_value(patient, 'heart_rate', '次/分')}；β 阻滞剂：{_medication_text(medications, 'β 受体')}；ARNI/ACEI/ARB：{_medication_text(medications, 'ARNI')}。"
    if prefix == "CM":
        return f"eGFR {_value(patient, 'egfr', 'ml/min/1.73m²')}；CrCl {_value(patient, 'crcl', 'ml/min')}；合并症与当前用药见报告第二、四部分。"
    if prefix == "FU":
        return f"PCI 术后 {_value(patient, 'post_pci_months', '个月')}；当前抗血小板：{_medication_text(medications, '抗血小板')}。"
    if prefix == "AD":
        context = patient.get("report_context") or {}
        return f"停药/漏服药物：{'、'.join(context.get('adherence_drugs') or []) or '未指明'}；天数 {_value(patient, 'self_stop_days', '天')}；临时用药：{context.get('temp_meds') or '未报告'}。"
    if prefix == "XJ":
        return f"手术日期 {'已录' if patient.get('surgery_date') else '缺失'}；支架/干预方式 {'已录' if patient.get('stent_type') else '缺失'}；出院方案 {'已录' if patient.get('discharge_plan') else '缺失'}。"
    if prefix == "CX":
        context = patient.get("report_context") or {}
        events = "、".join(x.get("label", "") for x in context.get("bleeding_events") or [])
        return f"出血事件：{events or '未报告'}；溃疡/出血史 {'有' if patient.get('ulcer_bleed_history') else '未报告'}；当前抗血小板：{_medication_text(medications, '抗血小板')}。"
    if prefix == "JC":
        return f"增强 CT/造影 {'拟行' if patient.get('enhance_ct') else '未报告'}；二甲双胍 {'使用' if patient.get('on_metformin') else '未使用/未录入'}；eGFR {_value(patient, 'egfr', 'ml/min/1.73m²')}。"
    if prefix == "XZ":
        return f"上级方案下转确认 {'是' if patient.get('referral_plan_confirmed') else '否/未录入'}；下转后再发症状 {'是' if patient.get('recent_symptom_after_referral') else '否/未录入'}。"
    if prefix in ("WT", "EL"):
        return f"年龄 {_value(patient, 'age', '岁')}；规范服药血压仍高 {'是' if patient.get('bp_high') else '否/未录入'}；糖尿病 {'有' if patient.get('diabetes') else '未报告'}。"
    if prefix == "LB":
        return f"Hb {_value(patient, 'hb', 'g/L')}；ALT/AST {_value(patient, 'alt', 'U/L')}/{_value(patient, 'ast', 'U/L')}（{patient.get('alt_ast_status') or '状态未录'}）；CK {_value(patient, 'ck', 'U/L')}（{patient.get('ck_status') or '状态未录'}）；FPG {_value(patient, 'fpg', 'mmol/L')}。"
    if prefix == "HT":
        return f"血钾 {_value(patient, 'potassium', 'mmol/L')}（{patient.get('potassium_status') or '状态未录'}）；心率 {_value(patient, 'heart_rate', '次/分')}；相关症状与用药见报告第四、五部分。"
    if prefix == "MC":
        return f"出院抗血小板：{'、'.join(patient.get('discharge_meds') or []) or '未录入'}；当前：{_medication_text(medications, '抗血小板')}；术后 {_value(patient, 'post_pci_months', '个月')}。"
    if prefix == "RL":
        estimate = "（按出院至今连续三联估算）" if patient.get("triple_therapy_months_estimated") else ""
        return f"术后 {_value(patient, 'post_pci_months', '个月')}；当前用药：{_medication_text(medications)}；三联抗栓 {_value(patient, 'triple_therapy_months', '个月')}{estimate}；PPI {patient.get('ppi') or '未使用/未录'}。"
    return "患者录入条件命中本规则；具体证据见对应报告部分。"


class ReportAssembler:
    def __init__(self, patient, matched):
        self.p = patient
        self.matched = matched
        self.context = patient.get("report_context") or {}
        self.medications = _current_medications(patient)
        self.advices = {x["id"]: x for x in matched.get("advices", [])}
        self.redlines = {x["id"]: x for x in matched.get("redlines", [])}
        self.used_sources = OrderedDict()
        self.unresolved = []
        self.exam_critical = []
        self.exam_attention = []
        self.exam_gap = []
        self.medication_gap_items = []
        self.drug_disease_items = []
        self.drug_disease_synergy = []
        self.adjust_plan = []
        self.symptoms = []
        self.behavior = []
        self.followup_rows = []
        self.referrals = []
        self.abnormal_keys = set()
        self.critical_keys = set()

    def source_label(self, source, rule_id):
        codes = [x for x in (source or "CN").split("/") if x]
        for code in codes:
            self.used_sources.setdefault(code, set())
            if rule_id:
                self.used_sources[code].add(rule_id)
        names = []
        for code in codes:
            name = SOURCES.get(code, f"规则库来源 {code}")
            names.append(name if name.startswith("相关药品") else f"《{name}》")
        return "、".join(names) + (f"；规则库条目 {rule_id}" if rule_id else "")

    def item(self, *, rule_id, conclusion, evidence, impact, action, timeframe, source, severity="attention", priority=2, section="", **extra):
        values = (conclusion, evidence, impact, action, timeframe, source)
        if not all(value is not None and str(value).strip() for value in values):
            self.unresolved.append({"rule_id": rule_id, "reason": "五要素不完整，未作为正式建议输出"})
            return None
        item = {
            "id": rule_id,
            "severity": severity,
            "priority": priority,
            "conclusion": str(conclusion),
            "evidence": str(evidence),
            "impact": str(impact),
            "action": str(action),
            "timeframe": str(timeframe),
            "source": self.source_label(source, rule_id),
            "section": section,
        }
        item.update(extra)
        return item

    def rule_item(self, advice, *, severity="attention", priority=2, section=""):
        action = advice["action"]
        conclusion = action.rstrip("。").split("：")[0].split("，")[0]
        domain = advice.get("domain", "用药")
        return self.item(
            rule_id=advice["id"], conclusion=conclusion,
            evidence=_rule_evidence(advice["id"], self.p, self.medications),
            impact=DOMAIN_IMPACT.get(domain, "影响本次治疗安全性与长期管理。"),
            action=action, timeframe=RULE_TIMEFRAMES.get(advice["id"], "本次随访"),
            source=advice.get("source", "CN"), severity=severity, priority=priority, section=section,
            level=advice.get("level", "常规"),
        )

    def redline_item(self, redline, section):
        priority = 1 if redline["id"] not in ("RL-02", "RL-04", "XJ-01") else 2
        return self.item(
            rule_id=redline["id"], conclusion=redline["name"],
            evidence=_rule_evidence(redline["id"], self.p, self.medications),
            impact="该问题可能显著增加出血、缺血或药物不良反应风险，需优先处理。",
            action=redline["action"], timeframe="立即/今天内" if priority == 1 else "本次随访，1–2 周内",
            source="CN-01", severity="critical" if priority == 1 else "attention", priority=priority, section=section,
        )

    def add_exam_attention(self, key, conclusion, evidence, impact, action, timeframe="本次随访（1–2 周内）", severity="轻度", source="TEMPLATE", rule_id=None):
        if key in self.critical_keys:
            return
        item = self.item(
            rule_id=rule_id or f"EXAM-{key}", conclusion=conclusion, evidence=evidence,
            impact=impact, action=action, timeframe=timeframe, source=source,
            severity=severity, priority=2 if severity in ("重度", "中度") else 3, section="5.2",
        )
        if item:
            self.exam_attention.append(item)
            self.abnormal_keys.add(key)

    def build_exams(self):
        for critical in self.matched.get("critical", []):
            rule_id = critical["id"]
            self.critical_keys.update(CRITICAL_KEYS.get(rule_id, set()))
        for critical in self.matched.get("critical", []):
            rule_id = critical["id"]
            key, unit, threshold, impact, action, timeframe = CRITICAL_DETAILS[rule_id]
            value = _value(self.p, key, unit)
            if rule_id == "CV-04" and self.p.get("hb_prev") is not None:
                value += f"；24 小时前 {_value(self.p, 'hb_prev', 'g/L')}"
            if rule_id == "CV-05":
                value += f"；较基线下降 >50%：{'是' if self.p.get('plt_drop_over_50pct') else '否/未录'}"
            if rule_id == "CV-06":
                value += f"；基线 {_value(self.p, 'baseline_scr', 'μmol/L')}"
            if rule_id == "CV-09" and self.p.get("qtc_baseline") is not None:
                value += f"；基线 QTc {_value(self.p, 'qtc_baseline', 'ms')}"
            if rule_id == "CV-11":
                value += "；伴胸痛"
            item = self.item(
                rule_id=rule_id, conclusion=f"【危急值】{critical['name'].replace('危急值', '').strip('()')}",
                evidence=f"{value}；危急阈值 {threshold}。", impact=impact, action=action,
                timeframe=timeframe, source="TEMPLATE", severity="critical", priority=1, section="5.1",
            )
            if item:
                self.exam_critical.append(item)
                self.abnormal_keys.add(key)

        hb = self.p.get("hb")
        if _number(hb) and hb >= 60:
            if hb < 90:
                severity, range_text = "中度", "60–89 g/L"
            elif hb <= 109 or self.p.get("hb_low"):
                severity, range_text = "轻度", "90–109 g/L；其他按本实验室范围判定"
            else:
                severity = None
            if severity:
                advice = self.advices.get("CM-12")
                self.add_exam_attention(
                    "hb", f"血红蛋白降低（{severity}）", f"Hb {hb} g/L；分档 {range_text}。",
                    "心肌缺血耐受性下降；强化抗栓时出血风险升高。",
                    advice["action"] if advice else "查明贫血原因，评估消化道失血与纠正贫血方案；抗栓强度调整由专科评估。",
                    severity=severity, source=advice["source"] if advice else "TEMPLATE", rule_id="CM-12" if advice else None,
                )
        elif self.p.get("hb_low") and hb is None:
            self.add_exam_attention("hb", "血红蛋白降低，数值缺失", "已勾选血红蛋白降低，但未录入 Hb 数值。", "无法判断贫血严重程度及抗栓出血风险。", "补充血红蛋白数值后重新分析。")

        plt = self.p.get("plt")
        if _number(plt) and plt >= 30:
            severity = "重度" if plt < 50 else "中度" if plt < 75 else "轻度" if plt < 100 or self.p.get("plt_status") == "降低" else None
            if severity:
                redline = self.redlines.get("LB-05")
                self.add_exam_attention(
                    "plt", f"血小板下降（{severity}）", f"PLT {plt}×10⁹/L；较基线下降 >50%：{'是' if self.p.get('plt_drop_over_50pct') else '否/未录'}。",
                    "出血风险升高，影响抗血小板治疗安全。",
                    redline["action"] if redline else "复查血常规，评估血小板减少原因与出血表现；抗栓调整由专科评估。",
                    severity=severity, source="CN-07", rule_id="LB-05" if redline else None,
                )

        liver_status = self.p.get("alt_ast_status")
        if liver_status in ("轻度升高", "中度升高", "重度升高"):
            severity = liver_status.replace("升高", "")
            redline = self.redlines.get("LB-02")
            advice = self.advices.get("LB-01")
            source = redline.get("source", "CN-04/CN-06") if redline else advice["source"] if advice else "TEMPLATE"
            action = redline["action"] if redline else advice["action"] if advice else "复查肝功能，评估肝损伤原因及相关用药；由医师决定是否调整。"
            self.add_exam_attention(
                "liver", f"ALT/AST {liver_status}", f"ALT {_value(self.p, 'alt', 'U/L')}；AST {_value(self.p, 'ast', 'U/L')}；录入状态 {liver_status}。",
                "可能影响他汀及其他经肝代谢药物的安全性。", action,
                timeframe="立即评估" if severity == "重度" else "本次随访；4 周内复查",
                severity=severity, source=source, rule_id="LB-02" if redline else "LB-01" if advice else None,
            )

        egfr = self.p.get("egfr")
        if _number(egfr) and egfr < 90:
            severity = "重度" if egfr < 30 else "中度" if egfr < 60 else "轻度"
            advice = self.advices.get("CM-05")
            self.add_exam_attention(
                "egfr", f"eGFR 降低（{severity}）", f"eGFR {egfr} ml/min/1.73m²；分档：60–89 轻度、30–59 中度、<30 重度。",
                "影响 NOAC、二甲双胍及其他经肾清除药物的选择与剂量。",
                advice["action"] if advice else "复核肾功能，按肾功能核对当前用药剂量与造影计划。",
                severity=severity, source=advice["source"] if advice else "CN-05/CN-08", rule_id="CM-05" if advice else None,
            )

        current_ldl = self.p.get("current_ldl")
        risk = self.p.get("ascvd_risk")
        target = 1.4 if risk == "超高危" else 1.8 if risk == "极高危" else None
        if _number(current_ldl) and target:
            excess = (current_ldl - target) / target * 100
            if excess > 0:
                severity = "重度" if excess > 100 or (risk == "极高危" and current_ldl > 2.6) else "中度" if excess > 50 else "轻度"
                self.add_exam_attention(
                    "current_ldl", f"LDL-C 未达标（{severity}）", f"本次 LDL-C {current_ldl} mmol/L；{risk}目标 <{target} mmol/L，超标 {excess:.0f}%。",
                    "持续未达标会增加动脉粥样硬化进展与再发缺血事件风险。",
                    "本次随访评估强化降脂方案；调整后 4–6 周复查血脂。",
                    timeframe="本次随访；调整后 4–6 周复查", severity=severity, source="CN-04",
                )
            else:
                self.abnormal_keys.discard("current_ldl")

        heart_rate = self.p.get("heart_rate")
        if _number(heart_rate) and 40 <= heart_rate and (heart_rate < 60 or heart_rate >= 100):
            severity = "重度" if heart_rate < 55 or heart_rate > 110 else "轻度"
            advice = self.advices.get("HT-05")
            self.add_exam_attention(
                "heart_rate", f"心率异常（{severity}）", f"心率 {heart_rate} 次/分；分档：55–59 或 100–110 为轻度，<55 或 >110 持续存在为重度。",
                "可能与 β 阻滞剂、传导异常或缺血相关，影响耐量与心律安全。",
                advice["action"] if advice else "复查心电图，结合症状评估心率异常原因及相关药物。",
                severity=severity, source=advice["source"] if advice else "CN-06", rule_id="HT-05" if advice else None,
            )

        qtc = self.p.get("qtc")
        if _number(qtc) and "qtc" not in self.critical_keys and qtc >= 460:
            severity = "中度" if qtc > 480 else "轻度"
            self.add_exam_attention(
                "qtc", f"QTc 延长（{severity}）", f"QTc {qtc} ms；基线 {_value(self.p, 'qtc_baseline', 'ms')}；460–480 轻度，>480–500 中度。",
                "QTc 延长增加室性心律失常风险，需核对相关药物。",
                "复查心电图与电解质，由医师评估 QT 延长药物。",
                severity=severity, source="CN-06/说明书",
            )

        if self.p.get("troponin_elevated") and "troponin" not in self.critical_keys:
            advice = self.advices.get("LB-06")
            self.add_exam_attention(
                "troponin", "肌钙蛋白升高", f"肌钙蛋白 {_value(self.p, 'troponin_value', 'ng/mL')}；已勾选升高。",
                "提示心肌损伤或再发缺血可能。", advice["action"] if advice else "复查肌钙蛋白与心电图，评估是否再发 ACS。",
                timeframe="立即复核；24 小时内评估", severity="中度", source=advice["source"] if advice else "EN-01", rule_id="LB-06" if advice else None,
            )

        if self.p.get("ck_status") in ("中度升高", "重度升高"):
            severity = self.p["ck_status"].replace("升高", "")
            redline = self.redlines.get("LB-04")
            advice = self.advices.get("LB-03")
            self.add_exam_attention(
                "ck", f"肌酸激酶{self.p['ck_status']}", f"CK {_value(self.p, 'ck', 'U/L')}；状态 {self.p['ck_status']}。",
                "需警惕他汀相关肌肉损伤及横纹肌溶解。",
                redline["action"] if redline else advice["action"] if advice else "暂停相关药物并复查 CK，由医师评估。",
                timeframe="立即评估" if severity == "重度" else "本次随访暂停并复查",
                severity=severity, source="CN-04", rule_id="LB-04" if redline else "LB-03" if advice else None,
            )

        potassium_status = self.p.get("potassium_status")
        if potassium_status in ("高", "低") and "potassium" not in self.critical_keys:
            rule_id = "HT-01" if potassium_status == "高" else "HT-02"
            advice = self.advices.get(rule_id)
            self.add_exam_attention(
                "potassium", f"血钾{potassium_status}", f"血钾 {_value(self.p, 'potassium', 'mmol/L')}；状态 {potassium_status}。",
                "电解质异常增加心律失常风险，并可能与降压药或利尿剂相关。",
                advice["action"] if advice else "复查血钾、心电图与肾功能，评估相关药物。",
                timeframe="立即复查", severity="中度", source=advice["source"] if advice else "CN-06/说明书", rule_id=rule_id if advice else None,
            )

        fpg = self.p.get("fpg")
        hba1c = self.p.get("hba1c")
        if "fpg" not in self.critical_keys and ((self.p.get("fbg_status") == "高") or (_number(hba1c) and hba1c >= 6.5) or self.p.get("fbg_status") == "低"):
            low = self.p.get("fbg_status") == "低"
            rule_id = "LB-08" if low else "LB-07"
            advice = self.advices.get(rule_id)
            self.add_exam_attention(
                "fpg", "低血糖" if low else "血糖控制需关注", f"FPG {_value(self.p, 'fpg', 'mmol/L')}；HbA1c {_value(self.p, 'hba1c', '%')}。",
                "血糖异常可影响心肌缺血风险与降糖治疗安全。",
                advice["action"] if advice else "复核血糖并评估降糖方案。",
                timeframe="立即纠正" if low else "本次随访", severity="中度", source=advice["source"] if advice else "CN-08", rule_id=rule_id if advice else None,
            )

        lvef = self.p.get("lvef")
        if _number(lvef) and lvef <= 40:
            advice = self.advices.get("IC-03")
            self.add_exam_attention(
                "lvef", "左心室射血分数降低", f"LVEF {lvef}%；心衰分型 {self.p.get('hf_type') or '未录'}。",
                "提示心功能受损，影响改善预后药物选择与长期预后。",
                advice["action"] if advice else "评估心衰及指南推荐的改善预后药物。",
                severity="中度", source=advice["source"] if advice else "心衰指南", rule_id="IC-03" if advice else None,
            )

        severity_order = {"重度": 0, "中度": 1, "轻度": 2}
        self.exam_attention.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["priority"], x["id"]))

    def build_gaps(self):
        core_labels = {
            "age": "年龄", "sex": "性别", "surgery_date": "PCI 手术日期",
            "discharge_diagnosis": "出院诊断", "vessel_count": "病变支数",
            "stent_type": "干预血管与方式",
        }
        for key, label in core_labels.items():
            if self.p.get(key) is None or self.p.get(key) == "":
                self.exam_gap.append({"missing": label, "impact": f"缺少{label}，无法完整评估患者概要及相应治疗条件。", "action": f"建议补充{label}后重新分析。", "timeframe": "本次随访前"})
        if self.p.get("hb") is not None and self.p.get("hb_prev") is None:
            self.exam_gap.append({"missing": "24 小时前血红蛋白", "impact": "无法判断是否 24 小时内下降 >20 g/L。", "action": "建议补充既往血红蛋白及采样时间。", "timeframe": "本次随访"})
        if self.p.get("plt") is not None and not self.p.get("plt_drop_over_50pct"):
            self.exam_gap.append({"missing": "血小板基线或变化幅度", "impact": "无法独立确认是否较基线下降 >50%。", "action": "建议补充基线血小板或确认变化幅度。", "timeframe": "本次随访"})
        if self.p.get("scr") is not None and self.p.get("baseline_scr") is None:
            self.exam_gap.append({"missing": "PCI 术前 48–72 小时基线血肌酐", "impact": "无法判断肾功能是否发生急性变化。", "action": "建议补充基线血肌酐后重新分析。", "timeframe": "本次随访"})
        if self.p.get("current_ldl") is None:
            self.exam_gap.append({"missing": "本次 LDL-C", "impact": "无法评估当前降脂是否达标及与基线相比的降幅。", "action": "建议补充本次血脂检查后重新分析。", "timeframe": "本次随访"})
        if self.p.get("current_ldl") is not None and not self.p.get("ascvd_risk"):
            self.exam_gap.append({"missing": "ASCVD 危险分层", "impact": "无法确定 LDL-C 目标值。", "action": "建议补充 ASCVD 危险分层。", "timeframe": "本次随访"})
        if self.p.get("alt_ast_status") in ("轻度升高", "中度升高", "重度升高"):
            self.exam_gap.append({"missing": "ALT/AST 相对正常上限倍数与本院参考范围", "impact": "当前分档来自人工状态，无法核对 1–3、3–5、>5 倍 ULN 的精确分档。", "action": "建议补充本院参考上限或倍数。", "timeframe": "本次随访"})
        if self.p.get("troponin_value") is not None and not self.p.get("troponin_reference_known"):
            self.exam_gap.append({"missing": "肌钙蛋白参考上限与检测方法", "impact": "不同 cTnI/cTnT 检测的参考上限不同，仅凭手工数值不能判断是否升高。", "action": "建议补充同次报告的参考上限或升高标记。", "timeframe": "本次随访"})
        incomplete = [m.get("name") for m in (self.context.get("medications") or []) if not _number(m.get("now")) or m.get("now") <= 0]
        if incomplete:
            self.exam_gap.append({"missing": "当前用药剂量", "impact": f"{'、'.join(incomplete)} 的当前剂量为空/0，按未当前使用处理，可能影响方案完整性判断。", "action": "如仍在使用，请补充当前剂量；如已停药，请在用药行为中确认。", "timeframe": "提交分析前"})

    def build_comorbidity(self):
        rows = []

        def add(name, status, association, source):
            rows.append({"name": name, "status": status, "association": association, "source": self.source_label(source, "")})

        if self.p.get("hypertension_grade"):
            bp = "是" if self.p.get("bp_high") is True else "否" if self.p.get("bp_high") is False else "未录"
            values = f"目前血压 {_value(self.p, 'systolic_bp')}/{_value(self.p, 'diastolic_bp')} mmHg"
            add(f"高血压（{self.p['hypertension_grade']}）", f"{values}；规范服药下血压仍 ≥140/90：{bp}", "β 受体阻滞剂兼具降压作用；血压未达标时需核对依从性与联合方案。", "CN-06")
        if self.p.get("diabetes"):
            add("糖尿病", f"最新 HbA1c {_value(self.p, 'hba1c', '%')}", "二甲双胍需结合肾功能；HbA1c 未达标时建议评估降糖方案。", "CN-08")
        if self.p.get("dyslipidemia"):
            status = self.p.get("lipid_goal") or "未录"
            add("高脂血症", f"达标情况：{status}", "他汀强度与 LDL-C 达标情况见第四部分。", "CN-04")
        if self.p.get("ckd") or self.p.get("egfr") is not None and self.p.get("egfr") < 60:
            add("慢性肾脏病", f"{self.p.get('ckd_stage') or '分期未录'} / eGFR {_value(self.p, 'egfr', 'ml/min/1.73m²')}", "影响 NOAC 选择与剂量、二甲双胍用量与造影计划。", "CN-05/CN-08")
        if self.p.get("hf"):
            add("心力衰竭", f"分型 {self.p.get('hf_type') or '未录'}，EF {_value(self.p, 'lvef', '%')}", "决定 ACEI/ARB/ARNI、β 阻滞剂、SGLT2i 等改善预后药物评估。", "心衰指南")
        if self.p.get("af"):
            anticoag = _medication_text(self.medications, "抗凝")
            add("心房颤动", f"抗凝方案：{anticoag}", "抗凝与抗血小板联用方案及三联时长见第四部分。", "CN-05")
        if self.p.get("asthma_copd"):
            add("COPD/哮喘", "有", "避免非选择性 β 受体阻滞剂；需要时评估高选择性 β1 品种。", "CN-02/CN-06")
        if self.p.get("prior_mi_stroke") or self.p.get("prior_mi_event"):
            events = []
            if self.p.get("prior_mi_event"):
                events.append(f"心肌梗死 {self.p.get('prior_mi_date') or '日期待补'}")
            if self.p.get("stroke_tia_history"):
                events.append(f"脑梗死 {self.p.get('prior_stroke_date') or '日期待补'}")
            add("既往心肌梗死/脑梗死", "；".join(events) or "有，日期待补", "是缺血风险与抗栓疗程评估的重要因素。", "CN-01")
        if self.p.get("ulcer_bleed_history"):
            add("消化道溃疡/出血史", "有", "DAPT 期间需评估 PPI 联合与出血监测。", "CN-07")
        if self.p.get("c_liver") or self.p.get("alt_ast_status") in ("轻度升高", "中度升高", "重度升高"):
            degree = self.p.get("liver_degree") or self.p.get("alt_ast_status") or "未录"
            add("肝功能异常", f"程度：{degree}", "影响他汀与 NOAC 等药物的代谢与安全性。", "CN-04/CN-05")
        if self.p.get("ich_history"):
            add("颅内出血史", "有", "是抗栓方案的核心制约，处理优先级最高。", "CN-01/CN-07")
        if self.p.get("other_pmh"):
            add("其他既往史", str(self.p["other_pmh"]), "需由接诊医师核对与当前用药的相关性。", "CN")
        if self.p.get("other_drug_intolerances"):
            add("其他药物不耐受/禁忌", "、".join(self.p["other_drug_intolerances"]), "调整方案时应避用相关药物，并由医师选择替代方案。", "说明书")
        if self.p.get("triple_therapy"):
            duration = _value(self.p, "triple_therapy_months", "个月")
            estimated = "（按出院与当前均为三联、出院至今连续使用估算）" if self.p.get("triple_therapy_months_estimated") else ""
            add("当前三联抗栓", f"已叠加 {duration}{estimated}", "三联抗栓增加出血风险，需由专科定期评估降阶。", "CN-01/CN-07")
        return rows

    def build_medication(self):
        months = self.p.get("post_pci_months")
        target_months = 6 if self.p.get("scenario") == "CCS" else 12
        current_ap = _medication_text(self.medications, "抗血小板")
        if _number(months) and months < target_months and not self.p.get("on_dapt"):
            decision = "缺口，术后疗程内未记录 DAPT"
            action = "核对出院方案与停药原因，恢复或启动指南推荐的抗血小板方案；具体品种由专科确认。"
        elif self.p.get("on_dapt") and _number(months) and months < target_months:
            decision = "疗程内，当前 DAPT 已记录"
            action = "维持疗程并评估缺血/出血风险，不自行停药或降级。"
        elif _number(months) and months >= target_months:
            decision = "DAPT 疗程期满，需评估降阶或延长"
            action = "结合缺血与出血风险，评估转单药或延长疗程。"
        else:
            decision = "信息不足，无法判定疗程"
            action = "补充术后时长与当前抗血小板方案后评估。"
        item = self.item(
            rule_id="AP-CHECK", conclusion=f"DAPT 疗程：{decision}", evidence=f"术后 {_value(self.p, 'post_pci_months', '个月')}；当前 {current_ap}。",
            impact=DOMAIN_IMPACT["抗血小板"], action=action, timeframe="本次随访", source="CN-01/CN-03",
            severity="attention" if "缺口" in decision else "normal", priority=2 if "缺口" in decision else 3, section="6.1",
            item="DAPT 疗程", current=current_ap, recommendation=f"{self.p.get('scenario') or 'PCI 术后'}常规疗程 {target_months} 个月，之后按风险个体化", decision=decision,
        )
        if item:
            self.medication_gap_items.append(item)

        if self.matched.get("tags", {}).get("tag_br"):
            item = self.item(
                rule_id="AP-04", conclusion="存在高出血风险，需复评抗栓强度", evidence=f"年龄 {_value(self.p, 'age', '岁')}；Hb {_value(self.p, 'hb', 'g/L')}；高出血风险标签已命中。",
                impact="继续强化或延长抗栓可能增加出血风险。", action="评估出血风险与 DAPT 疗程，决定是否缩短或转单药。", timeframe="本次随访",
                source="CN-01", priority=2, section="6.1", item="出血高危评估", current=current_ap,
                recommendation="评分与临床风险评估后决定 DAPT 缩短或延长", decision="建议评估",
            )
            if item:
                self.medication_gap_items.append(item)

        statin_text = _medication_text(self.medications, "降脂")
        current_ldl = self.p.get("current_ldl")
        target = 1.4 if self.p.get("ascvd_risk") == "超高危" else 1.8 if self.p.get("ascvd_risk") == "极高危" else None
        if not self.p.get("on_statin"):
            decision = "缺口，未记录他汀"
            action = "评估启动中等强度他汀；存在禁忌或不耐受时按规则调整。"
        elif current_ldl is not None and target and current_ldl > target:
            decision = "未达标，需强化"
            action = "评估加用依折麦布或调整降脂方案，4–6 周复查。"
        elif current_ldl is not None and target:
            decision = "当前 LDL-C 达标"
            action = "维持现有方案并按计划复查。"
        else:
            decision = "待确认当前 LDL-C 与目标"
            action = "补充本次 LDL-C 和 ASCVD 分层后评估。"
        item = self.item(
            rule_id="LP-CHECK", conclusion=f"降脂方案：{decision}", evidence=f"当前降脂：{statin_text}；本次 LDL-C {_value(self.p, 'current_ldl', 'mmol/L')}；目标 {('<' + str(target) + ' mmol/L') if target else '待确定'}。",
            impact=DOMAIN_IMPACT["调脂"], action=action, timeframe="本次随访；调整后 4–6 周复查" if "未达标" in decision or "缺口" in decision else "长期",
            source="CN-04", severity="attention" if "缺口" in decision or "未达标" in decision else "normal", priority=2 if "缺口" in decision or "未达标" in decision else 3,
            section="6.1", item="他汀与 LDL-C", current=statin_text, recommendation=f"ASCVD 危险分层对应 LDL-C 目标：{('<' + str(target) + ' mmol/L') if target else '待确定'}", decision=decision,
        )
        if item:
            self.medication_gap_items.append(item)

        hf_indicated = self.p.get("hf") and self.p.get("lvef_reduced")
        if hf_indicated:
            for category, title, source, rule_id in (("β 受体", "β 受体阻滞剂", "CN-01/心衰指南", "IC-03"), ("ARNI", "ACEI/ARB/ARNI", "CN-06/心衰指南", "IC-03")):
                current = _medication_text(self.medications, category)
                used = self.p.get("on_beta_blocker") if category == "β 受体" else self.p.get("on_acei_arb")
                item = self.item(
                    rule_id=rule_id + "-GAP-" + category, conclusion=f"{title}：{'已使用' if used else '二级预防缺口'}",
                    evidence=f"心衰 {self.p.get('hf_type') or ''}；LVEF {_value(self.p, 'lvef', '%')}；当前 {current}。",
                    impact="规范使用改善预后药物可降低心衰与缺血长期风险。",
                    action="维持并评估滴定。" if used else f"评估启动{title}并根据耐受性滴定。",
                    timeframe="本次随访", source=source, severity="normal" if used else "attention", priority=3 if used else 2,
                    section="6.1", item=title, current=current, recommendation="LVEF 降低时评估指南推荐的改善预后药物", decision="已使用，继续评估滴定" if used else "缺口，需评估启动",
                )
                if item:
                    self.medication_gap_items.append(item)

        if self.p.get("on_dapt") and self.p.get("ulcer_bleed_history"):
            used = bool(self.p.get("ppi"))
            item = self.item(
                rule_id="CX-05-GAP", conclusion=f"PPI 胃保护：{'已使用' if used else '存在缺口'}",
                evidence=f"DAPT {'使用' if self.p.get('on_dapt') else '未使用'}；消化道溃疡/出血史 有；PPI {self.p.get('ppi') or '未使用'}。",
                impact="DAPT 与消化道出血史叠加会增加消化道出血风险。",
                action="维持并核对 PPI 品种。" if used else "评估加用 PPI；与氯吡格雷合用时优先泮托拉唑或雷贝拉唑。",
                timeframe="本次随访", source="CN-07", severity="normal" if used else "attention", priority=3 if used else 2,
                section="6.1", item="PPI", current=self.p.get("ppi") or "未使用", recommendation="溃疡出血史 + DAPT 时评估联合 PPI", decision="已使用" if used else "缺口，需加用",
            )
            if item:
                self.medication_gap_items.append(item)

        for rule_id, redline in self.redlines.items():
            if rule_id in ("RL-05", "XZ-03", "CX-04", "XJ-01", "LB-02", "LB-04", "LB-05"):
                continue
            item = self.redline_item(redline, "6.2")
            if item:
                self.drug_disease_items.append(item)
                adjustment = dict(item)
                adjustment["section"] = "6.3"
                adjustment["current_medication"] = _medication_text(self.medications)
                adjustment["reason"] = item["impact"]
                self.adjust_plan.append(adjustment)

        for rule_id, advice in self.advices.items():
            domain = advice.get("domain")
            if domain in ("合并症", "降压药ADR"):
                synergy = rule_id in ("CM-04", "CM-08")
                item = self.rule_item(advice, severity="normal" if synergy else "attention", priority=3 if synergy else 2, section="6.2")
                if item:
                    (self.drug_disease_synergy if synergy else self.drug_disease_items).append(item)
            if rule_id in ADJUST_IDS:
                if rule_id == "IC-01" and self.p.get("on_beta_blocker"):
                    continue
                if rule_id == "IC-02" and self.p.get("on_acei_arb"):
                    continue
                if rule_id == "LP-03" and self.p.get("on_statin"):
                    continue
                if rule_id == "CX-05" and self.p.get("ppi"):
                    continue
                item = self.rule_item(advice, priority=2 if advice.get("level") == "审核级" else 3, section="6.3")
                if item:
                    item["current_medication"] = _medication_text(self.medications)
                    item["reason"] = item["impact"]
                    self.adjust_plan.append(item)

        existing_prefixes = {x["id"].split("-")[0] for x in self.adjust_plan}
        for gap in self.medication_gap_items:
            if "缺口" not in gap["decision"] and "未达标" not in gap["decision"]:
                continue
            prefix = "AP" if gap["item"] == "DAPT 疗程" else "LP" if gap["item"] == "他汀与 LDL-C" else "IC" if gap["item"] in ("β 受体阻滞剂", "ACEI/ARB/ARNI") else "CX"
            if prefix in existing_prefixes:
                continue
            adjustment = dict(gap)
            adjustment["section"] = "6.3"
            adjustment["current_medication"] = gap["current"]
            adjustment["reason"] = gap["impact"]
            self.adjust_plan.append(adjustment)
            existing_prefixes.add(prefix)

        for index, item in enumerate(self.adjust_plan, 1):
            item["priority_rank"] = index

    def build_symptom_behavior(self):
        symptoms = self.context.get("symptoms") or []
        bleeds = self.context.get("bleeding_events") or []
        if not symptoms and self.p.get("red_flag"):
            symptoms = [{"key": "red_flag", "label": "红旗症状（具体项目未传）"}]
        for symptom in symptoms:
            if symptom.get("bleeding"):
                continue
            severity = symptom.get("severity") or "red"
            triage = {"red": ("立即急诊", "critical", 1, "立即急诊评估，不仅凭电话调整用药。", "立即"),
                      "yellow": ("尽快转诊", "attention", 2, "尽快转诊评估症状原因与当前用药，不自行停药。", "尽快；24–72 小时内"),
                      "green": ("基层随访", "normal", 3, "基层随访观察，核对症状与用药；加重或出现红色症状时立即急诊。", "按计划随访")}[severity]
            item = self.item(
                rule_id="TRIAGE-" + symptom.get("key", "symptom"), conclusion=f"【{triage[0]}】{symptom.get('label')}",
                evidence=f"患者勾选 {symptom.get('label')}；PCI 术后 {_value(self.p, 'post_pci_months', '个月')}。",
                impact="症状可能提示疾病变化、药物不良反应或出血风险，需按严重程度处理。",
                action=triage[3], timeframe=triage[4], source="CN-01/CN-06", severity=triage[1], priority=triage[2], section="7.1",
            )
            if item:
                self.symptoms.append(item)
        for bleed in bleeds:
            severe = bleed.get("severe") or bleed.get("key") in ("bleed_hematemesis", "bleed_melena", "bleed_hematuria")
            item = self.item(
                rule_id="CX-" + bleed.get("key", "bleed"), conclusion=f"{'【立即急诊】' if severe else '【基层随访】'}{bleed.get('label')}",
                evidence=f"患者勾选 {bleed.get('label')}；当前抗血小板：{_medication_text(self.medications, '抗血小板')}。",
                impact="出血可能影响抗栓安全；严重出血可危及生命。",
                action="立即急诊评估出血部位、严重程度与抗栓方案。" if severe else "局部处理并宣教，不自行停用抗栓；基层随访并复查血常规与粪隐血。",
                timeframe="立即" if severe else "按计划随访；1–2 周复查", source="CN-07", severity="critical" if severe else "normal", priority=1 if severe else 3, section="7.1",
            )
            if item:
                self.symptoms.append(item)
        if not self.symptoms:
            self.symptom_confirmation = "未报告红旗症状或出血事件，继续观察。"
        else:
            self.symptom_confirmation = ""

        for adr in self.context.get("adrs") or []:
            key = adr.get("key")
            related = {
                "adr_dry_cough": "ACEI 相关干咳", "adr_edema": "二氢吡啶类 CCB 相关水肿",
                "adr_bradycardia": "β 阻滞剂相关心动过缓", "adr_rate_fast": "心率控制不佳",
                "adr_angina": "抗缺血控制不佳",
            }.get(key, "药物相关表现")
            item = self.item(
                rule_id="ADR-" + str(key), conclusion=f"【需关注】{adr.get('label')}",
                evidence=f"患者勾选 {adr.get('label')}；心率 {_value(self.p, 'heart_rate', '次/分')}；相关用药见第四部分。",
                impact=f"需核对{related}，避免自行停药或延误疾病评估。",
                action="本次随访核对症状与用药时间关系，由医师评估调整；出现红旗症状立即转诊。",
                timeframe="本次随访", source="CN-06/说明书", severity="attention", priority=2, section="7.1",
            )
            if item:
                self.symptoms.append(item)

        events = self.context.get("adherence_events") or []
        for index, event in enumerate(events, 1):
            drug = event.get("drug") or "未命名药物"
            days = event.get("days")
            antiplatelet = any(name in drug for name in ("阿司匹林", "吲哚布芬", "氯吡格雷", "替格瑞洛"))
            statin = "他汀" in drug
            high = antiplatelet and _number(days) and days >= 3
            item = self.item(
                rule_id=f"AD-EVENT-{index}", conclusion=f"{drug}停药/漏服：{'高危行为' if high else '需核对'}",
                evidence=f"患者报告 {drug} 已停/漏服 {_value(event, 'days', '天')}。",
                impact="可能增加支架内血栓与再发缺血风险。" if antiplatelet else "可能影响血脂达标与长期二级预防。" if statin else "可能影响既有疾病控制。",
                action="立即核对停药原因并评估恢复原方案；术后疗程内不得自行停用。" if antiplatelet else "评估恢复服用并复查血脂。" if statin else "核对停药/漏服原因并恢复医嘱方案。",
                timeframe="立即/今天内" if high else "本次随访", source="CN-01/CN-04", severity="critical" if high else "attention",
                priority=1 if high else 2, section="7.2", behavior=f"{drug}停药/漏服", decision="高危行为" if high else "需核对",
            )
            if item:
                self.behavior.append(item)

        for rule_id, advice in self.advices.items():
            if advice.get("domain") in ("用药行为", "临时用药") or rule_id == "CX-02":
                high = rule_id == "AD-02"
                item = self.rule_item(advice, severity="critical" if high else "attention", priority=1 if high else 2, section="7.2")
                if item:
                    item["behavior"] = item["conclusion"]
                    item["decision"] = "高危行为" if high else "需评估"
                    self.behavior.append(item)

        if self.p.get("planned_surgery"):
            if not any(x["id"] == "JC-03" for x in self.behavior):
                item = self.item(
                    rule_id="JC-BRIDGE", conclusion="拟行其他手术，需围手术期评估",
                    evidence=f"拟行手术：{self.p.get('planned_surgery') or '未报告'}。",
                    impact="围手术期可能影响抗栓与其他长期用药管理。",
                    action="由专科制定围手术期用药调整计划，不自行停药。",
                    timeframe="手术前完成评估", source="CN-01/CN-08", priority=2, section="7.2",
                    behavior="拟行其他手术", decision="需围手术期评估",
                )
                if item:
                    self.behavior.append(item)

    def build_followup(self):
        rows = []

        def add(item, timing, purpose, source="CN-01"):
            key = (item, timing)
            if not any((x["item"], x["timing"]) == key for x in rows):
                rows.append({"item": item, "timing": timing, "purpose": purpose, "source": self.source_label(source, "")})

        if self.p.get("post_pci"):
            add("血脂、肝肾功能、血常规、凝血", "PCI 术后 1/3/6/12 个月及此后按计划", "二级预防与用药安全随访")
        if any(x["id"] == "CV-01" for x in self.exam_critical):
            add("血钾、肾功能、心电图", "处理后 4–6 小时复查血钾；1 周后复查肾功能", "危急值确认与相关药物调整后监测", "TEMPLATE")
        if any(x["id"] in ("EXAM-hb", "CM-12") for x in self.exam_attention):
            add("血常规±粪隐血", "1–2 周", "贫血与出血追踪", "CN-07")
        if any(x["id"] in ("EXAM-current_ldl",) or x["id"].startswith("LP-") for x in self.adjust_plan):
            add("血脂四项、肝酶、CK", "启动/调整降脂后 4–6 周", "降脂达标与安全性判定", "CN-04")
        if any(x["id"] in ("EXAM-liver", "LB-01", "LB-02") for x in self.exam_attention):
            add("肝功能", "4 周；重度异常立即", "肝损伤与他汀用药安全监测", "CN-04")
        if any(x["id"] in ("EXAM-egfr", "CM-05", "CM-06", "CM-07") for x in self.exam_attention + self.drug_disease_items):
            add("肾功能、eGFR/CrCl", "本次随访及调整后按医嘱复查", "肾功能相关剂量与造影安全评估", "CN-05/CN-08")
        if any(x["id"].startswith("ADR-") or x["id"] in ("EXAM-heart_rate", "EXAM-qtc") for x in self.symptoms + self.exam_attention):
            add("心电图、电解质", "有心悸/晕厥时随时；药物调整后复查", "心律、心率与 QTc 监测", "CN-06")
        if self.p.get("on_amiodarone"):
            add("甲状腺功能（TSH±T4）", "每 6 个月；心悸/消瘦/畏寒随时", "胺碘酮相关甲状腺不良反应监测", "CN-02")
        for advice in self.advices.values():
            if advice["id"] == "FU-02":
                add("LDL-C", "术后 6 个月", "评估降脂达标情况", "CN-04")
            if advice["id"] == "XZ-02":
                add("下转接续复查与红旗症状回执", "按下转方案", "确认上级方案连续执行", advice["source"])
        self.followup_rows = rows

        if self.exam_critical:
            self.referrals.append("危急值未纠正或需进一步急救处理：立即按本院制度联系上级医院/转诊。")
        if any(x["priority"] == 1 for x in self.symptoms):
            self.referrals.append("红色症状或严重出血：立即急诊/转上级医院评估。")
        elif any(x["priority"] == 2 for x in self.symptoms):
            self.referrals.append("黄色症状：尽快转诊评估，不等待常规随访。")
        if any(x["id"] in ("CV-10", "EXAM-heart_rate") and x["severity"] == "重度" for x in self.exam_critical + self.exam_attention):
            self.referrals.append("严重心律失常或需起搏/射频治疗评估：转上级医院。")
        if any("复杂" in x["action"] or "造影" in x["action"] for x in self.adjust_plan):
            self.referrals.append("复杂病变或需血运重建决策：转上级医院专科评估。")

    def build_normal(self):
        normal = []

        def add(key, label, value, valid=True):
            if valid and self.p.get(key) is not None and key not in self.abnormal_keys and key not in self.critical_keys:
                normal.append({"name": label, "value": value})

        hb = self.p.get("hb")
        add("hb", "血红蛋白", f"{hb} g/L", _number(hb) and hb > 109 and not self.p.get("hb_low"))
        plt = self.p.get("plt")
        add("plt", "血小板", f"{plt}×10⁹/L", _number(plt) and plt >= 100 and self.p.get("plt_status") != "降低")
        egfr = self.p.get("egfr")
        add("egfr", "eGFR", f"{egfr} ml/min/1.73m²", _number(egfr) and egfr >= 90)
        ldl = self.p.get("current_ldl")
        target = 1.4 if self.p.get("ascvd_risk") == "超高危" else 1.8 if self.p.get("ascvd_risk") == "极高危" else None
        add("current_ldl", "本次 LDL-C", f"{ldl} mmol/L（达标）", _number(ldl) and target is not None and ldl <= target)
        hr = self.p.get("heart_rate")
        add("heart_rate", "心率", f"{hr} 次/分", _number(hr) and 60 <= hr < 100)
        qtc = self.p.get("qtc")
        add("qtc", "QTc", f"{qtc} ms", _number(qtc) and qtc < 460)
        potassium = self.p.get("potassium")
        add("potassium", "血钾", f"{potassium} mmol/L", _number(potassium) and 3.5 <= potassium <= 5.5 and self.p.get("potassium_status") == "正常")
        sodium = self.p.get("sodium")
        add("sodium", "血钠", f"{sodium} mmol/L", _number(sodium) and 135 <= sodium <= 145)
        fpg = self.p.get("fpg")
        add("fpg", "空腹血糖", f"{fpg} mmol/L", _number(fpg) and 3.9 <= fpg < 6.1)
        text = f"已评估 {len(normal)} 项指标未触发异常阈值：{'、'.join(x['name'] for x in normal)}。维持现有方案，按计划复查。" if normal else "暂无可作正面确认的正常指标；未录入项目不作正常推定。"
        return {"count": len(normal), "items": normal, "text": text}

    def assign_refs(self):
        groups = (
            (self.exam_critical, "5.1"), (self.exam_attention, "5.2"),
            (self.medication_gap_items, "6.1"), (self.drug_disease_items, "6.2"),
            (self.adjust_plan, "6.3"), (self.symptoms, "7.1"), (self.behavior, "7.2"),
        )
        for items, section in groups:
            for index, item in enumerate(items, 1):
                item["ref"] = f"{section}-{_circled(index)}"

    def build_action_plan(self):
        candidates = self.exam_critical + self.exam_attention + self.drug_disease_items + self.adjust_plan + self.symptoms + self.behavior
        levels = [[], [], []]
        seen = set()
        for item in candidates:
            key = (item["ref"], item["conclusion"])
            if key in seen:
                continue
            seen.add(key)
            priority = max(1, min(3, int(item.get("priority", 2))))
            levels[priority - 1].append({"number": "", "conclusion": item["conclusion"], "action": item["action"], "timeframe": item["timeframe"], "ref": item["ref"]})
        output = []
        titles = ("一级·立即处理（今天）", "二级·尽快门诊调整（1–2 周内）", "三级·长期管理（本次随访落实）")
        keys = ("primary", "secondary", "tertiary")
        counts = {}
        for index, items in enumerate(levels):
            for item_index, item in enumerate(items, 1):
                item["number"] = f"{('一级', '二级', '三级')[index]}-{item_index}"
            counts[keys[index]] = len(items)
            output.append({"key": keys[index], "title": titles[index], "items": items})
        return {"levels": output, "counts": counts, "summary": f"一级 {counts['primary']} 条、二级 {counts['secondary']} 条、三级 {counts['tertiary']} 条。"}

    def build_references(self):
        sources = []
        for code, rule_ids in self.used_sources.items():
            sources.append({"code": code, "name": SOURCES.get(code, f"规则库来源 {code}"), "rules": sorted(rule_ids)})
        return {
            "sources": sources,
            "terms": [
                {"abbr": "DAPT", "full": "双联抗血小板治疗"},
                {"abbr": "NOAC", "full": "非维生素 K 拮抗剂口服抗凝药"},
                {"abbr": "LVEF", "full": "左心室射血分数"},
                {"abbr": "QTc", "full": "校正 QT 间期"},
                {"abbr": "LDL-C", "full": "低密度脂蛋白胆固醇"},
                {"abbr": "eGFR", "full": "估算肾小球滤过率"},
            ],
            "disclaimer": DISCLAIMER,
        }

    def assemble(self):
        self.build_exams()
        self.build_gaps()
        comorbidity = self.build_comorbidity()
        self.build_medication()
        self.build_symptom_behavior()
        self.build_followup()
        self.assign_refs()
        action_plan = self.build_action_plan()
        exam_normal = self.build_normal()

        medication_problem_gaps = [x for x in self.medication_gap_items if "缺口" in x["decision"] or "未达标" in x["decision"] or "建议评估" in x["decision"]]
        medication_count = len(medication_problem_gaps) + len(self.drug_disease_items) + len(self.adjust_plan)
        behavior_count = len(self.symptoms) + len(self.behavior)
        risk_red = bool(self.exam_critical) or any(x["priority"] == 1 for x in self.symptoms + self.behavior)
        risk_orange = bool(self.exam_attention or self.drug_disease_items or self.adjust_plan or self.behavior or self.redlines)
        risk_level = "red" if risk_red else "orange" if risk_orange else "green"
        risk_label = {"red": "红色-需立即处理", "orange": "橙色-尽快门诊调整", "green": "绿色-按计划随访"}[risk_level]
        counts = {"critical": len(self.exam_critical), "attention": len(self.exam_attention), "medication": medication_count, "behavior": behavior_count}
        months = self.p.get("post_pci_months")
        target_months = 6 if self.p.get("scenario") == "CCS" else 12
        phase = "DAPT 期满" if _number(months) and months >= target_months else "DAPT 期内"
        names = [x["name"] for x in comorbidity]
        if names:
            comorb_text = "、".join(names[:2]) + ("等" if len(names) > 2 else "")
        else:
            comorb_text = "未报告合并症"
        portrait = (
            f"患者{_value(self.p, 'age', '岁')}{self.p.get('sex') or ''}，PCI 术后 {_value(self.p, 'post_pci_months', '个月')}（{phase}）。"
            f"合并{comorb_text}，共 {len(comorbidity)} 项。发现危急值 {counts['critical']} 项、关注异常 {counts['attention']} 项、"
            f"用药问题 {counts['medication']} 项、症状/依从性问题 {counts['behavior']} 项。综合风险：{risk_label}。"
        )
        if len(portrait) > 120:
            portrait = (
                f"患者{_value(self.p, 'age', '岁')}{self.p.get('sex') or ''}，PCI 术后 {_value(self.p, 'post_pci_months', '个月')}。"
                f"危急值 {counts['critical']} 项、关注异常 {counts['attention']} 项、用药问题 {counts['medication']} 项、"
                f"症状/依从性问题 {counts['behavior']} 项。综合风险：{risk_label}。"
            )

        exam_cards = self.context.get("exam_cards")
        if exam_cards is None:
            exam_cards = [key for key, fields in EXAM_CARD_FIELDS.items() if any(self.p.get(field) not in (None, "", False) for field in fields)]
        summary = {
            "basic": f"{_value(self.p, 'age', '岁')}，{self.p.get('sex') or '性别未录'}",
            "surgery": f"{self.p.get('surgery_date') or '手术日期待补'}行 PCI，术后 {_value(self.p, 'post_pci_months', '个月')}；病变 {self.p.get('vessel_count') or '未录'} 支；干预血管：{'、'.join(self.p.get('target_vessel') or []) or '未录'}；干预方式：{self.p.get('stent_type') or '未录'}",
            "diagnosis": self.p.get("discharge_diagnosis") or self.p.get("scenario") or "未录",
            "comorbidity_count": len(comorbidity),
            "core_completed": self.context.get("core_completed", sum(self.p.get(key) not in (None, "") for key in ("age", "sex", "surgery_date", "discharge_diagnosis", "vessel_count", "target_vessel", "stent_type"))),
            "core_total": 7,
            "exam_completed": len(exam_cards),
            "exam_total": 13,
            "exam_names": [EXAM_CARD_NAMES.get(x, x) for x in exam_cards],
            "portrait": portrait,
            "risk_level": risk_level,
            "risk_label": risk_label,
            "counts": counts,
            "tags": [key for key, value in self.matched.get("tags", {}).items() if value],
        }
        gap_count = len(medication_problem_gaps)
        medication_summary = f"当前用药记录：{_medication_record_text(self.medications)}。二级预防缺口 {gap_count} 项；药病相互影响 {len(self.drug_disease_items)} 项；调整建议 {len(self.adjust_plan)} 条。"
        return {
            "summary": summary,
            "comorbidity": comorbidity,
            "exam_critical": self.exam_critical,
            "exam_attention": self.exam_attention,
            "exam_normal": exam_normal,
            "exam_gap": self.exam_gap,
            "medication_gap": {"items": self.medication_gap_items, "summary": medication_summary},
            "drug_disease": {"items": self.drug_disease_items, "synergy": self.drug_disease_synergy},
            "adjust_plan": self.adjust_plan,
            "symptom_behavior": {"symptoms": self.symptoms, "behavior": self.behavior, "confirmation": self.symptom_confirmation},
            "action_plan": action_plan,
            "followup": {"schedule": self.followup_rows, "referral": self.referrals, "referral_note": "本次未触发紧急转诊指征；如出现危急值、红旗症状或严重出血，立即按制度转诊。" if not self.referrals else ""},
            "references": self.build_references(),
            "unresolved": self.unresolved,
        }


def build_report(patient, matched):
    return ReportAssembler(patient, matched).assemble()
