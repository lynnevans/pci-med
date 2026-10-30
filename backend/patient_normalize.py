# -*- coding: utf-8 -*-
"""把页面原始录入整理成规则引擎字段。

这一层只使用确定性规则，不调用大模型：
- ASCVD 危险分层、心衰分型由已有病史和检查值计算；
- 血红蛋白、血小板、血钾、血糖等状态由数值计算；
- 三联抗栓和逐药停药/漏服记录整理成报告与规则所需结构。

OCR 已根据化验单参考范围生成的状态，在缺少数值时仍会保留。
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import re
from typing import Any


ANTIPLATELET_PATTERN = re.compile(r"阿司匹林|吲哚布芬|氯吡格雷|替格瑞洛")
STATIN_PATTERN = re.compile(r"他汀|阿托伐他汀|瑞舒伐他汀|辛伐他汀|普伐他汀|匹伐他汀|氟伐他汀|洛伐他汀")


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _months_since(value: Any, today: date) -> int | None:
    parsed = _parse_date(value)
    if not parsed or parsed > today:
        return None
    return (today.year - parsed.year) * 12 + today.month - parsed.month - (1 if today.day < parsed.day else 0)


def _derive_ascvd(p: dict[str, Any], today: date) -> None:
    """按项目内 2023 中国血脂管理指南及超高危共识分层。"""
    if not p.get("post_pci"):
        return

    severe: list[str] = []
    recent_acs = p.get("scenario") == "ACS" and _number(p.get("post_pci_months")) and p["post_pci_months"] <= 12
    if recent_acs:
        severe.append("近 12 个月内 ACS")

    prior_mi = bool(p.get("prior_mi_event") or p.get("prior_mi_date") or p.get("prior_mi_year"))
    prior_mi_months = _months_since(p.get("prior_mi_date"), today)
    if prior_mi and not (recent_acs and prior_mi_months is not None and prior_mi_months <= 12):
        severe.append("既往心肌梗死")
    if p.get("stroke_tia_history") or p.get("prior_stroke_date") or p.get("prior_stroke_year"):
        severe.append("缺血性卒中史")

    factors: list[str] = []
    age = p.get("age")
    if _number(age) and ((p.get("sex") == "男" and age < 55) or (p.get("sex") == "女" and age < 65)):
        factors.append("早发冠心病")
    if _number(p.get("baseline_ldl")) and p["baseline_ldl"] > 4.9:
        factors.append("基线 LDL-C >4.9 mmol/L")
    if p.get("diabetes"):
        factors.append("糖尿病")
    if p.get("hypertension") or p.get("hypertension_grade"):
        factors.append("高血压")
    if str(p.get("ckd_stage") or "") in ("3期", "3a期", "3b期", "4期"):
        factors.append("慢性肾脏病 3/4 期")
    if p.get("on_statin") and _number(p.get("current_ldl")) and p["current_ldl"] >= 2.6:
        factors.append("他汀治疗后 LDL-C 仍 ≥2.6 mmol/L")

    ultra = len(severe) >= 2 or (len(severe) >= 1 and len(factors) >= 2)
    p["ascvd_risk"] = "超高危" if ultra else "极高危"
    p["ascvd_risk_basis"] = {
        "severe_events": severe,
        "high_risk_factors": factors,
        "criterion": "≥2 次严重 ASCVD 事件，或 1 次严重事件合并 ≥2 个高危险因素时判为超高危；其他已确诊 ASCVD 为极高危。",
    }


def _derive_hf(p: dict[str, Any]) -> None:
    lvef = p.get("lvef")
    if not _number(lvef):
        return
    p["lvef_reduced"] = lvef <= 40
    if p.get("hf"):
        p["hf_type"] = "HFrEF" if lvef <= 40 else "HFmrEF" if lvef < 50 else "HFpEF"


def _derive_exam_states(p: dict[str, Any]) -> None:
    if _number(p.get("hb")):
        p["hb_low"] = p["hb"] <= 109
    if _number(p.get("plt")):
        p["plt_status"] = "降低" if p["plt"] < 100 else "正常"
    if _number(p.get("potassium")):
        p["potassium_status"] = "低" if p["potassium"] < 3.5 else "高" if p["potassium"] > 5.5 else "正常"
    if _number(p.get("fpg")):
        p["fbg_status"] = "低" if p["fpg"] < 3.9 else "高" if p["fpg"] >= 6.1 else "正常"

    abnormal: list[str] = []
    if _number(p.get("tc")) and p["tc"] > 5.2:
        abnormal.append("TC 升高")
    if _number(p.get("tg")) and p["tg"] >= 1.7:
        abnormal.append("TG 升高")
    if _number(p.get("hdl")) and p["hdl"] < 1.0:
        abnormal.append("HDL-C 降低")
    target = 1.4 if p.get("ascvd_risk") == "超高危" else 1.8 if p.get("ascvd_risk") == "极高危" else None
    if target and _number(p.get("current_ldl")) and p["current_ldl"] > target:
        abnormal.append(f"LDL-C 高于 {target} mmol/L 目标")
    if abnormal:
        p["lipid_abnormal"] = "、".join(abnormal)

    if p.get("arrhythmia_type"):
        p["arrhythmia"] = True


def _derive_triple_therapy(p: dict[str, Any]) -> None:
    current_anticoagulant = bool(p.get("on_anticoagulant") or p.get("on_noac") or p.get("on_warfarin"))
    current_triple = bool(p.get("on_dapt") and current_anticoagulant)
    p["triple_therapy"] = current_triple
    discharge_triple = bool(p.get("discharge_dapt") and p.get("discharge_anticoagulant"))
    p["triple_therapy_since_discharge"] = bool(current_triple and discharge_triple)
    if current_triple and discharge_triple and _number(p.get("post_pci_months")):
        # 只有出院与当前均为三联时，才按“出院至今连续使用”估算；其余情况不猜月数。
        p["triple_therapy_months"] = p["post_pci_months"]
        p["triple_therapy_months_estimated"] = True


def _derive_adherence(p: dict[str, Any]) -> None:
    context = p.setdefault("report_context", {})
    raw_events = context.get("adherence_events") or p.get("adherence_events") or []
    events: list[dict[str, Any]] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        drug = str(raw.get("drug") or "").strip()
        days = raw.get("days")
        if not drug or not _number(days) or days < 0:
            continue
        events.append({"drug": drug, "days": days})

    if events:
        context["adherence_events"] = events
        context["adherence_drugs"] = [x["drug"] for x in events]
        p["adherence_events"] = events
        p["self_stop_days"] = max(x["days"] for x in events)
        ap_days = [x["days"] for x in events if ANTIPLATELET_PATTERN.search(x["drug"])]
        if ap_days:
            p["want_stop_antiplatelet"] = True
            p["antiplatelet_stop_days"] = max(ap_days)
        if any(x["days"] == 1 for x in events):
            p["miss_single_dose"] = True


def normalize_patient(payload: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """返回不修改原对象的规范化副本；today 仅供确定性测试注入。"""
    p = deepcopy(payload or {})
    current_date = today or date.today()

    sbp, dbp = p.get("systolic_bp"), p.get("diastolic_bp")
    if "bp_high" not in p and (_number(sbp) or _number(dbp)):
        p["bp_high"] = bool((_number(sbp) and sbp >= 140) or (_number(dbp) and dbp >= 90))

    _derive_ascvd(p, current_date)
    _derive_hf(p)
    _derive_exam_states(p)
    _derive_triple_therapy(p)
    _derive_adherence(p)

    names = p.get("other_drug_intolerances")
    if isinstance(names, list):
        p["other_drug_intolerances"] = [str(x).strip() for x in names if str(x).strip()]
    return p
