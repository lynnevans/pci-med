# -*- coding: utf-8 -*-
"""
化验单字段映射（确定性字典，零 LLM 参与）

职责边界：
- ocr.py 只负责「读单子」：把单子上的项目、数值、单位、参考范围、箭头原样读出来；
- 本模块只负责「对字段」：把识别项按字典映射到前端表单字段，并按参考范围/箭头做
  确定性推导（升高/降低/轻度升高/重度升高）。
- 本模块不参与任何用药判断，rule_engine.py 仍是唯一判读入口。

输入：ocr.py 返回的 items = [{item, value, unit, ref_range, flag}, ...]
输出：{
    "fields": [{field, label, kind, card, value, unit, sources, note}, ...],
    "unmatched": [{item, value, unit, ref_range, flag, reason}, ...],
    "warnings": ["...", ...],
}

一条识别项可以派生多个字段：例如「钾 6.5」同时产出 potassium（数值，供危急值）
和 potassium_status（状态，供用药规则）；派生值只用该单自己的 flag/参考范围。
"""
from __future__ import annotations

import re
import unicodedata

# 与 App.vue「界面 3 · 辅助检查」卡片顺序保持一致
CARD_ORDER = [
    "血常规", "尿常规", "肝功能", "肾功能", "凝血功能",
    "心肌酶谱", "肌钙蛋白", "电解质", "血脂",
    "空腹血糖和糖化血红蛋白", "B型前脑尿钠肽", "十二导联心电图", "超声心动图", "补充数值",
]

# 字段字典。aliases 用化验单上常见的项目名；exclude 用来挡掉同名前缀的干扰项。
# kind: number=数值输入；status=胶囊单选；bool=开关
SPECS = [
    # ---------------- 血常规 ----------------
    {
        # 原始数值：进「危急值数值」卡，同时派生 hb_low 供人群标签/用药规则使用
        "field": "hb", "label": "血红蛋白 Hb", "kind": "number", "unit": "g/L",
        "card": "血常规",
        "aliases": ["血红蛋白", "血红蛋白浓度", "hgb", "hb"],
        "exclude": ["糖化", "尿", "胎儿", "血红蛋白a1c"],
        "expect_units": ["g/l"], "min": 10.0, "max": 250.0,
        "derive": [
            {"field": "hb_low", "kind": "bool",
             "values": {"low": True, "normal": False, "high": False}},
        ],
    },
    {
        "field": "hb_low", "label": "血红蛋白降低", "kind": "bool", "unit": "g/L",
        "card": "血常规",
        "aliases": ["血红蛋白", "血红蛋白浓度", "hgb", "hb"],
        "exclude": ["糖化", "尿", "胎儿", "血红蛋白a1c"],
    },
    {
        # 原始数值进「危急值数值」卡，同时派生 plt_status
        "field": "plt", "label": "血小板 PLT", "kind": "number", "unit": "×10^9/L",
        "card": "血常规",
        "aliases": ["血小板计数", "血小板", "plt"],
        "exclude": ["压积", "体积", "分布", "抗体", "聚集", "相关", "比积"],
        "expect_units": ["109/l", "10e9/l"], "min": 1.0, "max": 2000.0,
        "derive": [
            {"field": "plt_status", "kind": "status",
             "values": {"low": "降低", "normal": "正常", "high": "正常"}},
        ],
    },
    {
        "field": "plt_status", "label": "血小板", "kind": "status", "unit": "×10^9/L",
        "card": "血常规",
        "aliases": ["血小板计数", "血小板", "plt"],
        "exclude": ["压积", "体积", "分布", "抗体", "聚集", "相关", "比积"],
    },
    {
        "field": "wbc", "label": "白细胞 WBC", "kind": "number", "unit": "×10^9/L",
        "card": "血常规", "aliases": ["白细胞计数", "白细胞", "wbc"], "exclude": ["尿"],
        "expect_units": ["109/l", "10e9/l"], "min": 0.1, "max": 500.0,
    },
    # ---------------- 尿常规 ----------------
    {
        "field": "brown_urine", "label": "潜血 / 褐色尿", "kind": "bool", "unit": "",
        "card": "尿常规",
        "aliases": ["尿潜血", "尿隐血", "潜血", "隐血", "bld", "尿红细胞"],
        "exclude": ["便", "粪", "大便"],
    },
    # ---------------- 肝功能 ----------------
    {
        "field": "alt", "label": "ALT", "kind": "number", "unit": "U/L", "card": "肝功能",
        "aliases": ["谷丙转氨酶", "丙氨酸氨基转移酶", "alt"], "exclude": [],
        "expect_units": ["u/l"], "min": 0.0, "max": 10000.0,
        "derive": [{"field": "alt_ast_status", "values": {"high": "轻度升高", "normal": "正常", "low": "正常"}}],
    },
    {
        "field": "ast", "label": "AST", "kind": "number", "unit": "U/L", "card": "肝功能",
        "aliases": ["谷草转氨酶", "天门冬氨酸氨基转移酶", "ast"], "exclude": [],
        "expect_units": ["u/l"], "min": 0.0, "max": 10000.0,
        "derive": [{"field": "alt_ast_status", "values": {"high": "轻度升高", "normal": "正常", "low": "正常"}}],
    },
    {
        "field": "alt_ast_status", "label": "ALT/AST", "kind": "status", "unit": "U/L",
        "card": "肝功能",
        "aliases": ["谷丙转氨酶", "丙氨酸氨基转移酶", "alt", "谷草转氨酶", "天门冬氨酸氨基转移酶", "ast"],
        "exclude": [],
    },
    {
        "field": "bilirubin", "label": "总胆红素", "kind": "number", "unit": "μmol/L",
        "card": "肝功能", "aliases": ["总胆红素", "胆红素", "tbil", "stb"],
        "exclude": ["直接", "间接", "尿"], "expect_units": ["umol/l"], "min": 0.0, "max": 1000.0,
    },
    {
        "field": "albumin", "label": "白蛋白", "kind": "number", "unit": "g/L",
        "card": "肝功能", "aliases": ["白蛋白", "血清白蛋白", "alb"],
        "exclude": ["尿"], "expect_units": ["g/l"], "min": 1.0, "max": 100.0,
    },
    # ---------------- 肾功能 ----------------
    {
        "field": "crcl", "label": "肌酐清除率 CrCl", "kind": "number", "unit": "ml/min",
        "card": "肾功能",
        "aliases": ["肌酐清除率", "内生肌酐清除率", "crcl", "ccr"],
        "exclude": ["尿"],
        "expect_units": ["ml/min"], "min": 1.0, "max": 400.0,
    },
    {
        "field": "egfr", "label": "eGFR", "kind": "number", "unit": "ml/min/1.73m²",
        "card": "肾功能",
        "aliases": ["egfr", "估算肾小球滤过率", "肾小球滤过率", "gfr"],
        "exclude": ["肌酐清除"],
        "expect_units": ["ml/min"], "min": 1.0, "max": 250.0,
    },
    {
        "field": "scr", "label": "血肌酐 Scr", "kind": "number", "unit": "μmol/L",
        "card": "肾功能",
        "aliases": ["血肌酐", "肌酐", "scr", "crea", "creatinine"],
        "exclude": ["清除率", "尿肌酐", "肌酐比"],
        "expect_units": ["umol/l"], "min": 5.0, "max": 3000.0,
    },
    # ---------------- 凝血功能 ----------------
    {
        # INR 原始数值进「危急值数值」卡，同时派生 coag_abnormal
        "field": "inr", "label": "INR", "kind": "number", "unit": "",
        "card": "危急值数值",
        "aliases": ["国际标准化比值", "inr"],
        "exclude": ["活动度", "纠正"],
        "expect_units": ["比值", "ratio"], "min": 0.5, "max": 20.0,
        "derive": [
            {"field": "coag_abnormal", "kind": "bool",
             "values": {"high": True, "normal": False, "low": False}},
        ],
    },
    {
        # 纤维蛋白原原始数值进「危急值数值」卡；降低同样算凝血异常
        "field": "fibrinogen", "label": "纤维蛋白原 Fib", "kind": "number", "unit": "g/L",
        "card": "危急值数值",
        "aliases": ["纤维蛋白原", "fib"],
        "exclude": ["降解"],
        "expect_units": ["g/l"], "min": 0.1, "max": 15.0,
        "derive": [
            {"field": "coag_abnormal", "kind": "bool",
             "values": {"low": True, "normal": False, "high": False}},
        ],
    },
    {
        "field": "pt", "label": "凝血酶原时间 PT", "kind": "number", "unit": "s", "card": "凝血功能",
        "aliases": ["凝血酶原时间", "pt"], "exclude": ["活动度", "比值", "inr"],
        "expect_units": ["s", "秒"], "min": 1.0, "max": 300.0,
        "derive": [{"field": "coag_abnormal", "kind": "bool",
                    "values": {"high": True, "normal": False, "low": False}}],
    },
    {
        "field": "aptt", "label": "活化部分凝血活酶时间 APTT", "kind": "number", "unit": "s", "card": "凝血功能",
        "aliases": ["活化部分凝血活酶时间", "活化部分凝血酶时间", "aptt"], "exclude": ["比值"],
        "expect_units": ["s", "秒"], "min": 1.0, "max": 300.0,
        "derive": [{"field": "coag_abnormal", "kind": "bool",
                    "values": {"high": True, "normal": False, "low": False}}],
    },
    {
        "field": "tt", "label": "凝血酶时间 TT", "kind": "number", "unit": "s", "card": "凝血功能",
        "aliases": ["凝血酶时间", "tt"], "exclude": ["比值", "aptt"],
        "expect_units": ["s", "秒"], "min": 1.0, "max": 300.0,
        "derive": [{"field": "coag_abnormal", "kind": "bool",
                    "values": {"high": True, "normal": False, "low": False}}],
    },
    {
        "field": "d_dimer", "label": "D-二聚体", "kind": "number", "unit": "mg/L", "card": "凝血功能",
        "aliases": ["d-二聚体", "d二聚体", "ddimer", "d-dimer"], "exclude": [],
        "expect_units": ["mg/l"], "min": 0.0, "max": 1000.0,
    },
    {
        "field": "coag_abnormal", "label": "凝血功能异常", "kind": "bool", "unit": "",
        "card": "凝血功能",
        "aliases": [
            "凝血酶原时间", "pt", "活化部分凝血活酶时间", "活化部分凝血酶时间", "aptt",
            "活化部分凝血活酶比值", "凝血酶时间", "tt", "凝血酶时间比值",
            "国际标准化比值", "inr", "纤维蛋白原", "fib",
        ],
        "exclude": ["活动度", "纠正", "降解"],
    },
    # ---------------- 心肌酶谱 ----------------
    {
        "field": "ck_mb", "label": "CK-MB", "kind": "number", "unit": "U/L", "card": "心肌酶谱",
        "aliases": ["肌酸激酶同工酶", "ck-mb", "ckmb"], "exclude": [],
        "expect_units": ["u/l"], "min": 0.0, "max": 10000.0,
    },
    {
        "field": "ck_status", "label": "CK", "kind": "status", "unit": "U/L",
        "card": "心肌酶谱", "aliases": ["肌酸激酶", "磷酸肌酸激酶", "ck"],
        "exclude": ["同工酶", "mb", "ckmb", "ck-mb"],
    },
    # ---------------- 肌钙蛋白 ----------------
    {
        "field": "troponin_value", "label": "肌钙蛋白", "kind": "number", "unit": "ng/mL", "card": "肌钙蛋白",
        "aliases": ["肌钙蛋白", "ctni", "ctnt", "tni", "tnt"], "exclude": [],
        "expect_units": ["ng/ml"], "min": 0.0, "max": 1000.0,
        "derive": [
            {"field": "troponin_elevated", "values": {"high": True, "normal": False, "low": False}},
            {"field": "troponin_reference_known", "values": {"high": True, "normal": True, "low": True}},
        ],
    },
    {
        "field": "troponin_reference_known", "label": "肌钙蛋白参考范围已提供", "kind": "bool", "unit": "",
        "card": "肌钙蛋白", "aliases": [], "exclude": [],
    },
    {
        # 只认「高敏/超敏 T」的定量结果，单位必须 ng/mL；普通 cTnI/T 仍只走下面的开关
        "field": "hs_ctnt", "label": "高敏肌钙蛋白 T hs-cTnT", "kind": "number", "unit": "ng/mL",
        "card": "危急值数值",
        "aliases": ["高敏肌钙蛋白t", "超敏肌钙蛋白t", "hs-ctnt", "hsctnt"],
        "exclude": [],
        "expect_units": ["ng/ml"], "min": 0.0, "max": 100.0,
        "derive": [
            {"field": "troponin_elevated", "kind": "bool",
             "values": {"high": True, "normal": False, "low": False}},
            {"field": "troponin_reference_known", "values": {"high": True, "normal": True, "low": True}},
        ],
    },
    {
        "field": "troponin_elevated", "label": "肌钙蛋白升高", "kind": "bool", "unit": "ng/mL",
        "card": "肌钙蛋白",
        "aliases": [
            "高敏肌钙蛋白", "超敏肌钙蛋白", "肌钙蛋白", "hs-ctnt", "hs-ctni",
            "ctni", "ctnt", "tni", "tnt",
        ],
        "exclude": [],
    },
    # ---------------- 电解质 ----------------
    {
        # 血钾原始数值进「危急值数值」卡，同时派生 potassium_status 供用药规则使用
        "field": "potassium", "label": "血钾 K⁺", "kind": "number", "unit": "mmol/L",
        "card": "危急值数值",
        "aliases": ["血钾", "钾离子", "钾", "k", "k+"],
        "exclude": ["尿钾", "钠钾"],
        "expect_units": ["mmol/l"], "min": 1.0, "max": 10.0,
        "derive": [
            {"field": "potassium_status", "kind": "status",
             "values": {"high": "高", "low": "低", "normal": "正常"}},
        ],
    },
    {
        "field": "sodium", "label": "血钠 Na⁺", "kind": "number", "unit": "mmol/L",
        "card": "危急值数值",
        "aliases": ["血钠", "钠离子", "钠", "na", "na+"],
        "exclude": ["尿钠", "脑钠", "利钠"],
        "expect_units": ["mmol/l"], "min": 90.0, "max": 200.0,
    },
    {
        "field": "co2cp", "label": "二氧化碳结合率 CO₂CP", "kind": "number", "unit": "mmol/L",
        "card": "危急值数值",
        "aliases": ["二氧化碳结合率", "二氧化碳结合力", "co2cp", "co2-cp"],
        "exclude": ["分压"],
        "expect_units": ["mmol/l"], "min": 1.0, "max": 50.0,
    },
    {
        "field": "potassium_status", "label": "血钾", "kind": "status", "unit": "mmol/L",
        "card": "电解质",
        "aliases": ["血钾", "钾离子", "钾", "k", "k+"],
        "exclude": ["尿钾", "钠钾"],
    },
    # ---------------- 血脂 ----------------
    {
        "field": "baseline_ldl", "label": "LDL-C（基线）", "kind": "number", "unit": "mmol/L",
        "card": "血脂",
        "aliases": ["低密度脂蛋白胆固醇", "低密度脂蛋白", "ldl-c", "ldl", "ldl胆固醇"],
        "exclude": [],
        "expect_units": ["mmol/l"], "min": 0.05, "max": 30.0,
    },
    # ---------------- 血糖 / 糖化 ----------------
    {
        "field": "fpg", "label": "空腹血糖", "kind": "number", "unit": "mmol/L",
        "card": "空腹血糖和糖化血红蛋白",
        "aliases": ["空腹血糖", "血糖", "fpg", "glu", "葡萄糖"],
        "exclude": ["餐后", "随机", "糖化", "尿", "脱氢酶", "耐量"],
        "expect_units": ["mmol/l"], "min": 0.1, "max": 100.0,
        "derive": [{"field": "fbg_status", "values": {"high": "高", "normal": "正常", "low": "低"}}],
    },
    {
        "field": "fbg_status", "label": "空腹血糖", "kind": "status", "unit": "mmol/L",
        "card": "空腹血糖和糖化血红蛋白",
        "aliases": ["空腹血糖", "血糖", "fpg", "glu", "葡萄糖"],
        "exclude": ["餐后", "随机", "糖化", "尿", "脱氢酶", "耐量"],
    },
    {
        "field": "hba1c", "label": "糖化血红蛋白", "kind": "number", "unit": "%",
        "card": "空腹血糖和糖化血红蛋白",
        "aliases": ["糖化血红蛋白", "糖化hb", "hba1c", "ghb", "glycatedhemoglobin"],
        "exclude": [],
        "expect_units": ["%"], "min": 2.0, "max": 25.0,
    },
    {
        "field": "bnp", "label": "B型前脑尿钠肽", "kind": "number", "unit": "pg/mL", "card": "B型前脑尿钠肽",
        "aliases": ["b型前脑尿钠肽", "脑钠肽", "b型利钠肽", "bnp", "nt-probnp", "ntprobnp"],
        "exclude": [], "expect_units": ["pg/ml"], "min": 0.0, "max": 100000.0,
    },
    # ---------------- 心电图 ----------------
    {
        # 心率原始数值进心电图卡；CV-10 阈值 <40 或 >130 次/分
        "field": "heart_rate", "label": "心率", "kind": "number", "unit": "次/分",
        "card": "十二导联心电图",
        "aliases": ["心率", "心室率", "heartrate", "hr"],
        "exclude": ["变异性", "间期"],
        "expect_units": ["次/分", "bpm", "次/min"], "min": 20.0, "max": 300.0,
    },
    {
        "field": "pr_interval", "label": "PR 间期", "kind": "number", "unit": "ms", "card": "十二导联心电图",
        "aliases": ["pr间期", "pr interval"], "exclude": [], "expect_units": ["ms"], "min": 40.0, "max": 800.0,
    },
    {
        "field": "qrs_duration", "label": "QRS 波时限", "kind": "number", "unit": "ms", "card": "十二导联心电图",
        "aliases": ["qrs波时限", "qrs时限", "qrs波", "qrs duration"], "exclude": [], "expect_units": ["ms"], "min": 30.0, "max": 500.0,
    },
    {
        # QT/QTc 同时出现时（380/420）取最后一个数，避免把 QT 当 QTc
        "field": "qtc", "label": "QTc", "kind": "number", "unit": "ms",
        "card": "十二导联心电图",
        "aliases": ["qtc间期", "qtc", "qt/qtc间期", "qtqtc间期"],
        "exclude": [],
        "expect_units": ["ms"], "min": 100.0, "max": 800.0,
        "number_pick": "last",
    },
    {
        # 这个字段不由 items 匹配，只由 OCR 返回的 conclusion 文本派生
        "field": "sinus_rhythm", "label": "窦性心律", "kind": "bool", "unit": "",
        "card": "十二导联心电图",
        "aliases": [], "exclude": [],
    },
    # ---------------- 超声心动图 ----------------
    {
        "field": "lvef", "label": "LVEF", "kind": "number", "unit": "%",
        "card": "超声心动图",
        "aliases": ["左室射血分数", "左心室射血分数", "射血分数", "lvef", "ef"],
        "exclude": ["右室", "缩短分数"],
        "expect_units": ["%"], "min": 5.0, "max": 90.0,
    },
]

SPEC_BY_FIELD = {s["field"]: s for s in SPECS}

# 状态型字段的严重度排序（用于同一字段多条结果合并取「最重」）
STATUS_RANK = {
    "alt_ast_status": {"正常": 0, "轻度升高": 1, "重度升高": 2},
    "ck_status": {"正常": 0, "中度升高": 1, "重度升高": 2},
    "plt_status": {"正常": 0, "降低": 1},
    "potassium_status": {"正常": 0, "低": 1, "高": 1},
    "fbg_status": {"正常": 0, "低": 1, "高": 1},
    "jaundice_hint": {"正常": 0, "轻度升高": 1, "重度升高": 2},
}

# 医生必须人工确认的提示（不阻塞回填）
FIELD_CAUTION = {
    "baseline_ldl": "请确认这是降脂治疗前 / 入院时的基线 LDL-C，而不是本次随访值。",
    "plt_status": "「PLT 较基线下降>50%」需与基线对比，单张化验单无法判断，请人工核对。",
    "coag_abnormal": "仅依据 PT / APTT / TT / INR 是否升高、纤维蛋白原是否降低判定。",
}

# 只写进该字段备注、不升级为全局 warning 的提示
FIELD_NOTE = {
    "inr": "CV-07 还需在用药页选择「华法林」。",
    "hs_ctnt": "CV-11 还需在症状页勾选「胸痛」。",
    "heart_rate": "CV-10：<40 或 >130 次/分报警。",
    "qtc": "CV-09：>500 ms 或较基线增加 >60 ms 报警；基线 QTc 需手工填。",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_RANGE_LO_HI = re.compile(r"^([-+]?\d+(?:\.\d+)?)[-~—–至]([-+]?\d+(?:\.\d+)?)$")
_RANGE_UPPER = re.compile(r"^[<≤]([-+]?\d+(?:\.\d+)?)$")
_RANGE_LOWER = re.compile(r"^[>≥]([-+]?\d+(?:\.\d+)?)$")


# ================= 文本归一化 =================
def _norm_name(name) -> str:
    s = unicodedata.normalize("NFKC", str(name or "")).lower()
    s = re.sub(r"\([^)]*\)", "", s)              # 去掉括号内的单位/英文缩写
    s = re.sub(r"[\s*#:：,，;；/\\\-—_]+", "", s)  # 去掉空格与分隔符
    s = re.sub(r"(测定|检测|定量|浓度)$", "", s)
    return s.strip()


def _alias_score(norm: str, alias: str) -> int:
    a = _norm_name(alias)
    if not a:
        return 0
    if norm == a:
        return 1000 + len(a)
    # 单字（钾/钠）只允许精确命中，避免「脑钠肽」误吃「钠」
    if len(a) <= 1:
        return 0
    # 2~3 个字母的缩写只允许精确命中，避免 "ck" 误吃 "ckmb"、"pt" 误吃 "aptt"
    if a.isascii() and len(a) <= 3:
        return 0
    if a in norm:
        return 100 + len(a)
    return 0


def _match_spec(item_name: str):
    norm = _norm_name(item_name)
    if not norm:
        return None
    best, best_score = None, 0
    for spec in SPECS:
        if any(_norm_name(x) in norm for x in spec.get("exclude", []) if x):
            continue
        score = max((_alias_score(norm, a) for a in spec["aliases"]), default=0)
        if score > best_score:
            best, best_score = spec, score
    return best


# ================= 数值 / 单位 / 参考范围 =================
def _num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = unicodedata.normalize("NFKC", str(value or "")).replace(",", "")
    m = _NUM_RE.search(s)
    return float(m.group()) if m else None


def _last_num(value):
    """取字符串里最后一个数：QT/QTc 的 380/420 要 QTc=420，不是 QT=380。"""
    s = unicodedata.normalize("NFKC", str(value or "")).replace(",", "")
    nums = _NUM_RE.findall(s)
    return float(nums[-1]) if nums else None


def _parse_range(text):
    """返回 (下限, 上限)，缺失为 None。支持 2.6-3.4 / 0~1.7 / <5.2 / 阴性 等。"""
    if text is None:
        return None, None
    s = unicodedata.normalize("NFKC", str(text)).strip()
    if not s:
        return None, None
    s = re.split(r"\s+", s)[0].replace(" ", "")
    m = _RANGE_LO_HI.match(s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = _RANGE_UPPER.match(s)
    if m:
        return None, float(m.group(1))
    m = _RANGE_LOWER.match(s)
    if m:
        return float(m.group(1)), None
    return None, None


def _norm_unit(unit: str) -> str:
    s = unicodedata.normalize("NFKC", str(unit or "")).lower()
    s = s.replace("μ", "u").replace("µ", "u").replace("²", "2")
    # ×10^9/L、10*9/L、10^9/L 统一成 109/l
    s = s.replace("×", "").replace("*", "").replace("^", "")
    return re.sub(r"\s+", "", s)


def _flag_of(value, ref_range, given, number=None):
    """优先用参考范围算；算不出再用模型给的箭头；最后按文字兜底。

    number 允许调用方传入「按 spec 选好的数」（例如 QTc 取 380/420 的 420）。
    """
    v = number if number is not None else _num(value)
    lo, hi = _parse_range(ref_range)
    if v is not None and (lo is not None or hi is not None):
        if hi is not None and v > hi:
            return "high"
        if lo is not None and v < lo:
            return "low"
        return "normal"
    g = str(given or "").strip().lower()
    if g in ("high", "low", "normal"):
        return g
    t = unicodedata.normalize("NFKC", str(value or "")).strip()
    if t in ("高", "低"):
        return "high" if t == "高" else "low"
    if any(k in t for k in ("↑", "阳性", "(+)", "＋", "升高", "偏高", "增高")):
        return "high"
    if any(k in t for k in ("↓", "降低", "偏低", "减低")):
        return "low"
    return "normal"


def _sinus_from_conclusion(text):
    """从心电图结论原文判断是否窦性心律；没有明确措辞就不填（返回 None）。"""
    t = _norm_name(text)
    if not t:
        return None
    if "非窦性" in t:
        return False
    if any(k in t for k in ("窦性心律", "窦性节律", "窦性心动过缓", "窦性心动过速", "窦性心律不齐")):
        return True
    if any(k in t for k in ("心房颤动", "房颤", "心房扑动", "房扑")):
        return False
    return None


def _unit_issue(spec, unit: str):
    """数值型字段的单位与表单单位不一致时，不自动换算，交给医生。"""
    u = _norm_unit(unit)
    if not u:
        return None
    expected = spec.get("expect_units") or []
    if any(u.startswith(e) or e.startswith(u) for e in expected):
        return None
    return "单位「%s」与表单单位「%s」不一致，未自动换算，请手动录入" % (
        str(unit).strip(), spec["unit"],
    )


# ================= 值推导 =================
def _status_value(spec, value, flag, ref_range):
    key = spec["field"]
    v = _num(value)
    _, hi = _parse_range(ref_range)
    ratio = (v / hi) if (v is not None and hi) else None

    if key == "alt_ast_status":
        if flag != "high":
            return "正常", None
        if ratio is not None and ratio >= 3:
            return "重度升高", "ALT/AST 约为参考上限的 %.1f 倍" % ratio
        note = "未识别到参考范围上限，按「轻度升高」回填" if ratio is None else "ALT/AST 约为参考上限的 %.1f 倍" % ratio
        return "轻度升高", note

    if key == "ck_status":
        if flag != "high":
            return "正常", None
        if ratio is not None and ratio >= 5:
            return "重度升高", "CK 约为参考上限的 %.1f 倍" % ratio
        note = "未识别到参考范围上限，按「中度升高」回填" if ratio is None else "CK 约为参考上限的 %.1f 倍" % ratio
        return "中度升高", note

    if key == "jaundice_hint":
        if flag == "high":
            return "轻度升高", "总胆红素升高，请人工核对是否「皮肤巩膜黄染」"
        return "正常", None

    if key == "plt_status":
        return ("降低" if flag == "low" else "正常"), None

    if key in ("potassium_status", "fbg_status"):
        return {"high": "高", "low": "低"}.get(flag, "正常"), None

    return "正常", None


def _bool_value(spec, value, flag):
    key = spec["field"]
    if key == "brown_urine":
        t = unicodedata.normalize("NFKC", str(value or ""))
        if any(k in t for k in ("阳性", "(+)", "＋", "+")):
            return True
        if any(k in t for k in ("阴性", "正常", "未见", "-")):
            return False
        return flag == "high"
    if key == "hb_low":
        return flag == "low"
    return flag == "high"  # troponin_elevated / coag_abnormal


# ================= 主入口 =================
def _apply_derives(accum, spec, source, flag):
    """把一条识别项派生到附加字段（例如 钾 6.5 → potassium + potassium_status）。

    派生只依赖 OCR 自己给出的 flag（相对参考范围的高/低），不做任何医学判断。
    """
    for derive in spec.get("derive", []):
        target = SPEC_BY_FIELD.get(derive["field"])
        if target is None:
            continue
        value = derive["values"].get(flag)
        if value is None:
            continue
        entry = accum.setdefault(target["field"], {"spec": target, "rows": []})
        entry["rows"].append({
            "source": source,
            "number": None,
            "flag": flag,
            "ref_range": source["ref_range"],
            "derived_value": value,
            "derived_from": spec["field"],
            "derived_item": source["item"],
            "derived_source_value": source["value"],
        })


def map_items(items, conclusion="") -> dict:
    if not isinstance(items, list):
        items = []

    accum: dict[str, dict] = {}
    unmatched: list[dict] = []
    warnings: list[str] = []

    for raw in items:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("item") or "").strip()
        if not name:
            continue

        spec = _match_spec(name)
        if spec is None:
            unmatched.append({
                "item": name,
                "value": str(raw.get("value") or "").strip(),
                "unit": str(raw.get("unit") or "").strip(),
                "ref_range": str(raw.get("ref_range") or "").strip(),
                "flag": str(raw.get("flag") or "").strip().lower(),
                "reason": "未收录的检测项",
            })
            continue

        value = str(raw.get("value") or "").strip()
        unit = str(raw.get("unit") or "").strip()
        ref_range = str(raw.get("ref_range") or "").strip()
        number = _num(value)
        if spec.get("number_pick") == "last":
            number = _last_num(value)
        flag = _flag_of(value, ref_range, raw.get("flag"), number)

        source = {
            "item": name,
            "value": value,
            "unit": unit,
            "ref_range": ref_range,
            "flag": flag,
        }

        # 只提示、不自动回填的项（例如总胆红素不能直接等价于「皮肤巩膜黄染」）
        if spec.get("hint_only"):
            reason = "仅作提示，不自动回填，请人工判断"
            unmatched.append({**source, "reason": reason})
            if flag != "normal":
                warnings.append("%s 异常（%s %s），请人工核对「黄疸」等体征" % (name, value, unit))
            continue

        primary_ok = True
        if spec["kind"] == "number":
            issue = _unit_issue(spec, unit)
            if issue:
                unmatched.append({**source, "reason": issue})
                warnings.append("%s：%s" % (name, issue))
                primary_ok = False
            elif number is None:
                unmatched.append({**source, "reason": "结果不是数值"})
                warnings.append("%s：结果「%s」不是数值，未回填" % (name, value))
                primary_ok = False
            elif number < spec.get("min", -1e9) or number > spec.get("max", 1e9):
                reason = "数值超出合理范围（%s ~ %s）" % (spec.get("min"), spec.get("max"))
                unmatched.append({**source, "reason": reason})
                warnings.append("%s：%s，请人工录入" % (name, reason))
                primary_ok = False

        if primary_ok:
            entry = accum.setdefault(spec["field"], {"spec": spec, "rows": []})
            entry["rows"].append({
                "source": source,
                "number": number,
                "flag": flag,
                "ref_range": ref_range,
            })

        # 数值回填失败（单位不对 / 不是数值 / 超范围）时仍从箭头派生状态或开关，
        # 保证「血红蛋白 13 g/dL」这类情况至少不会丢掉异常状态
        if spec.get("derive"):
            _apply_derives(accum, spec, source, flag)

    # 心电图结论：只从报告结论原文判断「窦性心律」，没有明确措辞就不填
    if conclusion:
        sinus = _sinus_from_conclusion(conclusion)
        if sinus is not None:
            spec = SPEC_BY_FIELD["sinus_rhythm"]
            text = str(conclusion).strip()[:120]
            entry = accum.setdefault(spec["field"], {"spec": spec, "rows": []})
            entry["rows"].append({
                "source": {
                    "item": "心电图结论",
                    "value": text,
                    "unit": "",
                    "ref_range": "",
                    "flag": "normal",
                },
                "number": None,
                "flag": "normal",
                "ref_range": "",
                "derived_value": sinus,
                "derived_from": "conclusion",
                "derived_item": "心电图结论",
                "derived_source_value": text,
            })

    fields = []
    for spec in SPECS:
        entry = accum.get(spec["field"])
        if not entry:
            continue
        rows = entry["rows"]
        sources = [r["source"] for r in rows]
        notes = []

        if spec["kind"] == "number":
            primary_rows = [r for r in rows if "derived_value" not in r]
            if not primary_rows:
                continue
            value = primary_rows[0]["number"]
            if len(primary_rows) > 1:
                notes.append("多处出现（%s），取第一条" % "、".join(r["source"]["item"] for r in primary_rows))
            if not any(r["source"]["unit"] for r in primary_rows):
                notes.append("化验单未印单位，已按表单单位回填")
        elif spec["kind"] == "status":
            best, best_note = "正常", None
            for r in rows:
                if "derived_value" in r:
                    v = r["derived_value"]
                    note = "由「%s %s」数值派生" % (r["derived_item"], r["derived_source_value"])
                else:
                    v, note = _status_value(spec, r["source"]["value"], r["flag"], r["ref_range"])
                if STATUS_RANK.get(spec["field"], {}).get(v, 0) > STATUS_RANK.get(spec["field"], {}).get(best, 0):
                    best, best_note = v, note
            value = best
            if best_note:
                notes.append(best_note)
            if len(rows) > 1:
                notes.append("合并 %d 条结果取最重" % len(rows))
        else:
            def _row_bool(r):
                if "derived_value" in r:
                    return bool(r["derived_value"])
                return _bool_value(spec, r["source"]["value"], r["flag"])

            value = any(_row_bool(r) for r in rows)
            derived = [r for r in rows if "derived_value" in r]
            if derived:
                if all(r.get("derived_from") == "conclusion" for r in derived):
                    notes.append("由心电图结论「%s」派生" % derived[0]["derived_source_value"][:40])
                else:
                    notes.append("由「%s」数值派生" % "、".join(
                        "%s %s" % (r["derived_item"], r["derived_source_value"]) for r in derived
                    ))
            if len(rows) > 1:
                notes.append("合并 %d 条结果（任一阳性即为是）" % len(rows))

        caution = FIELD_CAUTION.get(spec["field"])
        if caution:
            notes.append(caution)
            warnings.append(caution)

        extra_note = FIELD_NOTE.get(spec["field"])
        if extra_note:
            notes.append(extra_note)

        fields.append({
            "field": spec["field"],
            "label": spec["label"],
            "kind": spec["kind"],
            "card": spec["card"],
            "value": value,
            "unit": spec["unit"],
            "sources": sources,
            "note": "；".join(n for n in notes if n),
        })

    # 按卡片顺序输出，方便前端按检查单分组展示
    fields.sort(key=lambda f: CARD_ORDER.index(f["card"]) if f["card"] in CARD_ORDER else 99)

    if not items:
        warnings.append("模型没有返回任何检测项，请确认图片清晰、方向正确。")
    elif not fields:
        warnings.append("识别到检测项，但没有一项命中字段字典，请手动录入或补充别名。")

    return {
        "fields": fields,
        "unmatched": unmatched,
        "warnings": list(dict.fromkeys(warnings)),
    }