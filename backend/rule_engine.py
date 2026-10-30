# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 —— 规则引擎 V2（全量 68 条：13 红线 + 55 常规，确定性，零自由发挥）

设计原则：数据驱动。
  - REDLINES：红线库（13 条），命中即拦截/转诊，优先级最高，绝不进 LLM。
  - RULES：常规规则表（55 条，覆盖 v3.2 全部 14 个域），逐条对应 v3.2 的 IF/THEN/出处/级别。
  - match(patient)：唯一入口，输入患者字段字典，返回 {tags, redlines, advices}。

冲突消解（引擎内实现，对应 v3.2 第三部分第 6 条）：
  - 红线库 > 一切常规建议（命中红线即不输出常规）。
  - EL-02 优先于 WT-01（≥80 岁降压目标放宽，覆盖 WT-01 的 140/90）。

用法：
  python rule_engine.py            # 跑内置 3 个演示
  from rule_engine import match    # 供 FastAPI 接口调用
"""


# =====================================================================
# 患者输入字段说明（前端表单 -> 字典 key，供 SY1949 写 FastAPI 时对齐）
# ---------------------------------------------------------------------
# scenario            'ACS' / 'CCS'（入院/复诊场景）
# post_pci            是否 PCI 术后（bool）
# post_pci_months     当前术后月数（数值，复诊时点）
# dcb                 药物涂层球囊治疗（bool）
# precis_dapt         PRECISE-DAPT 评分（数值）
# ticagrelor_intolerant  替格瑞洛不耐受/禁忌（bool）
# cyp2c19_loss        氯吡格雷抵抗（CYP2C19 功能缺失）（bool）
# aspirin_intolerant  阿司匹林过敏/不耐受（bool）
# dapt_expired        DAPT 是否期满（bool）
# no_new_ischemia     无新发缺血事件（bool）
# long_term_phase     长期维持阶段（bool）
# ascvd_risk          '极高危' / '超高危'
# need_start_lipid    需启动降脂（bool）
# statin_4_6w_not_goal  中等强度他汀 4-6 周未达标（bool）
# statin_ezetimibe_not_goal  他汀+依折麦布仍未达标（bool）
# baseline_ldl        基线 LDL-C（mmol/L，数值）
# on_statin           是否已在服他汀（bool）
# statin_intolerant   他汀不耐受（bool）
# beta_blocker_contra β 阻滞剂禁忌（低血压/严重心动过缓/高度房室传导阻滞/急性心衰失代偿）（bool）
# beta_blocker_intolerant  β 阻滞剂不耐受（bool）
# acei_contra         ACEI 禁忌（bool）
# dry_cough           干咳不耐受（ACEI）（bool）
# angina_inadequate   抗缺血单药症状控制不佳（bool）
# hf                  心衰（bool）
# lvef                LVEF 数值（%）
# lvef_reduced        LVEF 降低（bool）
# sinus_rhythm        窦性心律（bool）
# rate_still_fast     β 阻滞剂后仍心率偏快（bool）
# residual_inflammation  动脉粥样硬化性 CCS、残余炎症/事件风险高（bool）
# af                  房颤（bool）
# cha2ds2_vasc        CHA2DS2-VASc 评分（数值）
# sex                 '男' / '女'（房颤抗凝阈值用）
# has_bled            HAS-BLED 评分（数值）
# emergency_pci       急诊 PCI（bool）
# diabetes            2 型糖尿病（bool）
# ckd                 CKD（bool）
# egfr                eGFR（ml/min/1.73m2，数值）
# crcl                肌酐清除率（ml/min，数值）
# on_metformin        用二甲双胍（bool）
# on_noac             用 NOAC（bool）
# noac_type           '利伐沙班' / '达比加群' / '阿哌沙班'
# weight              体重（kg，数值）
# scr                 血肌酐（μmol/L，数值）
# asthma_copd         哮喘/COPD（bool）
# gout_history        痛风史（bool）
# stroke_tia_history  缺血性卒中/TIA 史（bool）
# prior_mi_stroke     既往心梗/卒中史（bool）
# multivessel         多支病变（bool）
# on_amiodarone       长期用胺碘酮（bool）
# hb                  血红蛋白（g/L，数值）
# on_dapt             DAPT 用药期间（bool）
# miss_single_dose    单次漏服（bool）
# self_stop_days      自行停药天数（数值）
# blood_activating    自服活血中成药/鱼油/纳豆激酶（bool）
# mild_bleed          轻微出血（牙龈/瘀斑，无 Hb 下降）（bool）
# ulcer_bleed_history 消化道溃疡/出血史（bool）
# ich_history         颅内出血史（bool）
# recent_fatal_bleed  近期致命性出血（bool）
# on_nsaid_steroid    同时用 NSAIDs/激素（bool）
# need_analgesic      需镇痛药（bool）
# enhance_ct          拟行增强 CT/造影（bool）
# on_metformin        用二甲双胍（bool）
# referral_plan_confirmed  上级方案下转已确认（bool）
# recent_symptom_after_referral  下转后 1 个月内再发症状（bool）
# bp_high             规范服药下血压 ≥140/90（bool）
# age                 年龄（岁，数值）
# ---------------------------------------------------------------------
# 红线库专用字段：
# want_stop_antiplatelet  患者拟停抗血小板（bool）
# triple_therapy_months   三联抗栓已叠加月数（数值）
# aspirin_dose / clopidogrel_dose / ticagrelor_dose  处方剂量（mg，数值）
# on_clopidogrel / on_ticagrelor  用氯吡格雷/替格瑞洛（bool）
# ppi                  当前 PPI 品种（'奥美拉唑'/'艾司奥美拉唑'/'泮托拉唑'/...）
# on_nitrate / on_pde5i  用硝酸酯 / PDE5 抑制剂（bool）
# red_flag             红旗症状（再发胸痛/黑便呕血/晕厥/活动耐量明显下降）（bool）
# surgery_date / stent_type / discharge_plan  手术日期/支架类型/出院方案（缺失为 None/空）
# alt_ast_ratio        ALT/AST 相对正常上限倍数（数值）
# ck_ratio             CK 相对正常上限倍数（数值）
# plt                  血小板（×10^9/L，数值）
# jaundice / coag_abnormal / brown_urine / plt_drop_over_50pct  黄疸/凝血异常/褐色尿/PLT 降>50%（bool）
# ---------------------------------------------------------------------
# 扩展字段（v4 新增，状态型 = 录入时按本实验室判定）：
# hypertension_grade    高血压分级（'1级'/'2级'/'3级'/'单纯收缩期'）
# potassium_status      血钾（'高'/'正常'/'低'，状态型）
# troponin_elevated     肌钙蛋白升高（bool，状态型）
# alt_ast_status        肝酶（'正常'/'轻度升高'/'重度升高'，状态型）
# ck_status             心肌酶（'正常'/'中度升高'/'重度升高'，状态型）
# plt_status            血小板（'正常'/'降低'，状态型）
# hb_low                血红蛋白降低（bool，状态型）
# fbg_status            空腹血糖（'高'/'正常'/'低'，状态型）
# hba1c                 糖化血红蛋白（%，数值型）
# on_acei_arb           用 ACEI/ARB/ARNI（bool）
# acei_arb_type         类型（'ACEI'/'ARB'/'ARNI'）
# on_ccb                用 CCB（bool）
# ccb_type              类型（'二氢吡啶类'/'非二氢吡啶类'）
# on_diuretic           用利尿剂（bool）
# diuretic_type         类型（'呋塞米'/'螺内酯'/'氢氯噻嗪'/'吲达帕胺'）
# on_beta_blocker       用 β 阻滞剂（bool）
# beta_blocker_type     类型（美托洛尔/比索洛尔/卡维地洛）
# edema                 踝部/下肢水肿（bool）
# bradycardia           静息心动过缓（bool，心率<60）
# discharge_meds        出院抗血小板药列表（['阿司匹林','替格瑞洛']）
# on_aspirin            当前用阿司匹林（bool）
# on_indobufen          当前用吲哚布芬（bool）
# vessel_count          病变支数（1/2/3）
# target_vessel         干预血管列表（['左主干','前降支','回旋支','右冠']）
# wall_abnormality      室壁瘤/室壁运动障碍（bool）
# planned_surgery       拟行其他手术（文本/日期）
# dyslipidemia          高脂血症（bool）
# other_pmh             其他既往史（文本）
# ---------------------------------------------------------------------
# 危急值监视字段（v5 新增，仅供 CRITICAL_VALUES 模块报警，不参与 RULES 推理）：
# potassium             血钾（mmol/L，数值）
# sodium                血钠（mmol/L，数值）
# calcium_corrected     校正钙（mmol/L，数值）
# heart_rate            心率（次/分，数值）
# qtc                   QTc（ms，数值）
# qtc_baseline          基线 QTc（ms，数值，判「较基线增>60ms」）
# hs_ctnt               高敏肌钙蛋白T（ng/mL，数值）
# chest_pain            胸痛（bool，配合 hs_ctnt 判危急）
# inr                   INR（数值，华法林者用）
# on_warfarin           用华法林（bool）
# fibrinogen            纤维蛋白原（g/L，数值）
# co2cp                 二氧化碳结合率（mmol/L，数值）
# baseline_scr          基线肌酐（μmol/L，数值，判 AKI）
# hb_prev               24h前血红蛋白（g/L，数值，判「24h下降>20」）
# ---------------------------------------------------------------------
# =====================================================================


# ================= 人群标签计算 =================
def compute_tags(p):
    """计算 TAG-BR（高出血）/ TAG-IR（高缺血）/ TAG-EL（老年≥75）"""
    tags = {"tag_br": False, "tag_ir": False, "tag_el": False}
    age = p.get("age", 0)
    anemia = p.get("hb_low")
    bleed_history = p.get("ulcer_bleed_history") or p.get("ich_history")

    # 高出血风险：HAS-BLED≥3，或（年龄≥65 且 贫血/CKD/既往出血 任一）
    if p.get("has_bled", 0) >= 3:
        tags["tag_br"] = True
    elif age >= 65 and (anemia or p.get("ckd") or bleed_history):
        tags["tag_br"] = True

    # 高缺血风险：ACS入院 / 多支病变 / 既往MI·卒中 / 糖尿病合并CKD
    if (p.get("scenario") == "ACS" or p.get("multivessel")
            or (p.get("target_vessel") and "左主干" in (p.get("target_vessel") or ()))
            or p.get("prior_mi_stroke") or (p.get("diabetes") and p.get("ckd"))):
        tags["tag_ir"] = True

    # 老年：年龄≥75
    if age >= 75:
        tags["tag_el"] = True

    return tags


# ================= 红线库（硬拦截，优先级最高，13 条） =================
REDLINES = [
    {"id": "RL-01", "name": "术后<12个月拟停抗血小板",
     "cond": lambda x: x.get("post_pci_months", 999) < 12 and x.get("want_stop_antiplatelet"),
     "action": "强制阻断：术后未满12个月，未经上级医师/专科确认不得停用抗血小板；禁止降级/换药，仅维持原方案。"},
    {"id": "RL-02", "name": "三联抗栓叠加>6个月",
     "cond": lambda x: x.get("triple_therapy_months", 0) > 6,
     "action": "预警：三联抗栓（DAPT+抗凝）叠加超过6个月，长期出血风险升高，建议降级评估为抗凝+单抗。"},
    {"id": "RL-03", "name": "剂量越界",
     "cond": lambda x: (x.get("aspirin_dose", 100) > 100
                        or (x.get("clopidogrel_dose") is not None and x.get("clopidogrel_dose") != 75)
                        or (x.get("ticagrelor_dose") is not None and x.get("ticagrelor_dose") != 90)),
     "action": "拦截：剂量越界（阿司匹林>100mg，或氯吡格雷≠75mg，或替格瑞洛维持≠90mg bid），回退为规则标准剂量。"},
    {"id": "RL-04", "name": "氯吡格雷+奥美拉唑/艾司奥美拉唑",
     "cond": lambda x: x.get("on_clopidogrel") and x.get("ppi") in ("奥美拉唑", "艾司奥美拉唑"),
     "action": "不推荐合用：氯吡格雷与奥美拉唑/艾司奥美拉唑（CYP2C19强抑制）同用降低抗栓效果，建议换泮托拉唑或调整抗血小板。"},
    {"id": "RL-05", "name": "红旗症状",
     "cond": lambda x: bool(x.get("red_flag")),
     "action": "转诊优先：再发胸痛/黑便呕血/晕厥/活动耐量明显下降，立即建议转诊/急诊，先于一切用药建议。"},
    {"id": "RL-06", "name": "两种P2Y12抑制剂同用",
     "cond": lambda x: x.get("on_clopidogrel") and x.get("on_ticagrelor"),
     "action": "拦截：处方同时含两种P2Y12抑制剂，P2Y12仅保留一种（替格瑞洛或氯吡格雷二选一）。"},
    {"id": "RL-07", "name": "硝酸酯+PDE5抑制剂",
     "cond": lambda x: x.get("on_nitrate") and x.get("on_pde5i"),
     "action": "拦截：硝酸酯类与PDE5抑制剂合用可致严重低血压，禁止同用，需上级确认。"},
    {"id": "XJ-01", "name": "手术信息缺失",
     "cond": lambda x: not (x.get("surgery_date") and x.get("stent_type") and x.get("discharge_plan")),
     "action": "保守假设：手术日期/支架类型/出院方案任一缺失，按DAPT未满12个月处理，禁止降级/换药，仅续方；并输出《信息补全清单》：手术医院+日期、支架类型与数量、出院方案、近期化验、出院小结。"},
    {"id": "XZ-03", "name": "下转后1个月内再发症状",
     "cond": lambda x: bool(x.get("recent_symptom_after_referral")),
     "action": "不因刚看过上级而降级：下转后1个月内再发症状，红旗直接触发转诊（衔接RL-05）。"},
    {"id": "CX-04", "name": "颅内出血史/近期致命性出血",
     "cond": lambda x: x.get("ich_history") or x.get("recent_fatal_bleed"),
     "action": "红线：颅内出血史或近期致命性出血，基层不输出抗栓再启动建议，方案由上级专科制定。"},
    {"id": "LB-02", "name": "肝酶重度升高/黄疸",
     "cond": lambda x: (x.get("alt_ast_status") == "重度升高") or x.get("jaundice") or x.get("coag_abnormal"),
     "action": "红线：ALT/AST>5倍正常上限或伴黄疸/凝血异常，暂停他汀，触发严重肝损伤转诊指征。"},
    {"id": "LB-04", "name": "肌酶重度升高",
     "cond": lambda x: (x.get("ck_status") == "重度升高") or x.get("brown_urine"),
     "action": "红线：CK>10倍正常上限或褐色尿，立即停他汀，触发横纹肌溶解转诊指征。"},
    {"id": "LB-05", "name": "严重血小板减少",
     "cond": lambda x: (x.get("plt") is not None and x.get("plt") < 50) or x.get("plt_drop_over_50pct")
                        or (x.get("plt") is None and x.get("plt_status") == "降低"),
     "action": "红线：PLT<50或较基线下降>50%，疑HIT/DIT，停肝素类，触发严重血小板减少转诊指征。"},
]


# ================= 危急值库（13 项，出现即刻处理，优先级最高） =================
# 说明：危急值用「数值字段」判读，独立于上方的「状态化」用药规则。
# 前八类阈值按《分析结果报告输出模板 V1.0》统一；其余为既有扩展监测项。
# 危急值监视字段（OCR/录入追加，仅供本模块报警，不参与 RULES 推理）：
#   potassium 血钾(mmol/L) / sodium 血钠(mmol/L) / calcium_corrected 校正钙(mmol/L)
#   heart_rate 心率(次/分) / qtc QTc(ms) / qtc_baseline 基线QTc(ms)
#   hs_ctnt 高敏肌钙蛋白T(ng/mL) / chest_pain 胸痛(bool)
#   inr INR / on_warfarin 用华法林(bool) / fibrinogen 纤维蛋白原(g/L)
#   co2cp 二氧化碳结合率(mmol/L) / baseline_scr 基线肌酐(μmol/L) / hb_prev 24h前血红蛋白(g/L)
#   fpg 空腹血糖(mmol/L)
# 复用现有字段：hb / plt / scr / plt_drop_over_50pct
CRITICAL_VALUES = [
    {"id": "CV-01", "name": "血钾危急值",
     "cond": lambda x: x.get("potassium") is not None and (x["potassium"] <= 2.5 or x["potassium"] >= 6.5),
     "action": "危急值：血钾 ≤2.5 或 ≥6.5 mmol/L。显著增加心律失常风险；立即复查确认并纠正诱因，处理后 4–6 小时复查。"},
    {"id": "CV-02", "name": "血钠危急值",
     "cond": lambda x: x.get("sodium") is not None and (x["sodium"] <= 120 or x["sodium"] >= 160),
     "action": "危急值：血钠 ≤120 或 ≥160 mmol/L。意识障碍、抽搐风险；立即复查并谨慎纠正，避免纠正过快。"},
    {"id": "CV-03", "name": "校正钙危急值",
     "cond": lambda x: x.get("calcium_corrected") is not None and (x["calcium_corrected"] < 1.9 or x["calcium_corrected"] > 2.9),
     "action": "危急值：校正钙 <1.9 或 >2.9 mmol/L。手足搐搦、意识改变；立即复查并处理。"},
    {"id": "CV-04", "name": "血红蛋白危急值",
     "cond": lambda x: (x.get("hb") is not None and x["hb"] < 60)
                        or (x.get("hb") is not None and x.get("hb_prev") is not None and x["hb_prev"] - x["hb"] > 20),
     "action": "危急值：血红蛋白 <60 g/L，或 24 h 内下降 >20 g/L。警惕活动性出血；立即评估出血原因与抗栓方案。"},
    {"id": "CV-05", "name": "血小板危急值",
     "cond": lambda x: (x.get("plt") is not None and x["plt"] < 30) or x.get("plt_drop_over_50pct"),
     "action": "危急值：血小板 <30×10⁹/L，或较基线下降 >50%。自发出血风险；立即复查并由专科评估抗栓方案。"},
    {"id": "CV-06", "name": "肌酐升高(AKI)危急值",
     "cond": lambda x: (x.get("scr") is not None and x.get("baseline_scr") is not None
                        and x["scr"] >= 1.5 * x["baseline_scr"]),
     "action": "危急值：血肌酐较 48–72 h 基线上升 ≥50%。警惕急性肾损伤；立即复核肾功能并评估肾毒性药物。"},
    {"id": "CV-07", "name": "INR 危急值(华法林者)",
     "cond": lambda x: x.get("on_warfarin") and x.get("inr") is not None and x["inr"] > 4.5,
     "action": "危急值：INR >4.5（用华法林者）。出血风险升高；立即复查并由医师调整抗凝方案。"},
    {"id": "CV-08", "name": "纤维蛋白原危急值",
     "cond": lambda x: x.get("fibrinogen") is not None and x["fibrinogen"] < 1.0,
     "action": "危急值：纤维蛋白原 <1.0 g/L。出血倾向；立即复查并评估处理。"},
    {"id": "CV-09", "name": "QTc 危急值",
     "cond": lambda x: (x.get("qtc") is not None and x["qtc"] > 500)
                        or (x.get("qtc") is not None and x.get("qtc_baseline") is not None and x["qtc"] - x["qtc_baseline"] > 60),
     "action": "危急值：QTc >500 ms，或较基线增加 >60 ms。尖端扭转型室速风险；立即复核心电图并评估 QT 延长药物。"},
    {"id": "CV-10", "name": "心率危急值",
     "cond": lambda x: x.get("heart_rate") is not None and (x["heart_rate"] < 40 or x["heart_rate"] > 130),
     "action": "危急值：心率 <40 或 >130 次/分。严重传导阻滞或快速心律失常风险；立即复查心电图和电解质。"},
    {"id": "CV-11", "name": "hs-cTnT+胸痛危急值",
     "cond": lambda x: x.get("chest_pain") and x.get("hs_ctnt") is not None and x["hs_ctnt"] > 0.07,
     "action": "危急值：hs-cTnT >0.07 ng/mL 且伴胸痛。警惕急性心肌损伤；立即转诊评估。"},
    {"id": "CV-12", "name": "二氧化碳结合率危急值",
     "cond": lambda x: x.get("co2cp") is not None and x["co2cp"] <= 10,
     "action": "危急值：二氧化碳结合率 ≤10 mmol/L。警惕严重代谢性酸中毒；立即复查并评估病因。"},
    {"id": "CV-13", "name": "血糖危急值",
     "cond": lambda x: x.get("fpg") is not None and (x["fpg"] <= 2.8 or x["fpg"] >= 22.2),
     "action": "危急值：空腹血糖 ≤2.8 或 ≥22.2 mmol/L。警惕严重低血糖或高血糖急症；立即复查血糖并处理。"},
]


def check_critical(p):
    """危急值检查：返回命中列表 [{id, name, action}]，优先于一切用药建议。"""
    return [{"id": c["id"], "name": c["name"], "action": c["action"]}
            for c in CRITICAL_VALUES if c["cond"](p)]


# ================= 常规规则表（55 条，覆盖 v3.2 全部 14 域） =================
RULES = []

# ---------- 域1：抗血小板（AP，11 条） ----------
RULES += [
    {"id": "AP-01", "domain": "抗血小板", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("scenario") == "ACS" and x.get("post_pci"),
     "action": "DAPT 维持 12 个月（阿司匹林 + P2Y12 抑制剂）。"},
    {"id": "AP-02", "domain": "抗血小板", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("scenario") == "CCS" and x.get("post_pci"),
     "action": "DAPT 维持 6 个月。"},
    {"id": "AP-03", "domain": "抗血小板", "level": "审核级", "source": "CN-01",
     "cond": lambda x: x.get("tag_ir") and not x.get("tag_br"),
     "action": "高缺血风险且无高出血风险，可评估 DAPT 延长至 2~3 年。"},
    {"id": "AP-04", "domain": "抗血小板", "level": "审核级", "source": "CN-01",
     "cond": lambda x: (x.get("precis_dapt", 0) >= 25 and x.get("post_pci_months", 0) >= 3) or x.get("tag_br"),
     "action": "PRECISE-DAPT≥25 且术后≥3个月，或高出血风险，可评估缩短 DAPT、转单药抗血小板。"},
    {"id": "AP-05", "domain": "抗血小板", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("dcb"),
     "action": "药物涂层球囊（DCB）治疗，DAPT 维持 6 个月。"},
    {"id": "AP-06", "domain": "抗血小板", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("scenario") == "ACS" or x.get("tag_ir"),
     "action": "ACS 或高缺血风险，P2Y12 首选替格瑞洛；不能耐受/禁忌则用氯吡格雷。"},
    {"id": "AP-07", "domain": "抗血小板", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("scenario") == "CCS" or x.get("ticagrelor_intolerant"),
     "action": "CCS 或替格瑞洛不耐受，P2Y12 用氯吡格雷。"},
    {"id": "AP-08", "domain": "抗血小板", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("cyp2c19_loss"),
     "action": "氯吡格雷不耐受/禁忌，由专科评估替代抗血小板方案。"},
    {"id": "AP-09", "domain": "抗血小板", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("aspirin_intolerant"),
     "action": "阿司匹林不耐受/禁忌，由专科评估吲哚布芬等替代方案。"},
    {"id": "AP-10", "domain": "抗血小板", "level": "常规", "source": "CN-02/CN-03",
     "cond": lambda x: x.get("dapt_expired") and x.get("no_new_ischemia"),
     "action": "DAPT 期满且无新发缺血事件，转单药抗血小板长期维持（阿司匹林或 P2Y12 单药）。"},
    {"id": "AP-11", "domain": "抗血小板", "level": "审核级", "source": "CN-03",
     "cond": lambda x: x.get("long_term_phase"),
     "action": "长期维持阶段，可选 P2Y12 抑制剂单药替代阿司匹林。"},
]

# ---------- 域2：调脂（LP，8 条） ----------
RULES += [
    {"id": "LP-01", "domain": "调脂", "level": "常规", "source": "CN-04",
     "cond": lambda x: x.get("ascvd_risk") == "极高危",
     "action": "ASCVD 极高危，LDL-C 目标 <1.8 mmol/L 且较基线降幅 >50%。"},
    {"id": "LP-02", "domain": "调脂", "level": "常规", "source": "CN-04",
     "cond": lambda x: x.get("ascvd_risk") == "超高危",
     "action": "ASCVD 超高危，LDL-C 目标 <1.4 mmol/L 且较基线降幅 >50%。"},
    {"id": "LP-03", "domain": "调脂", "level": "常规", "source": "CN-04",
     "cond": lambda x: x.get("need_start_lipid"),
     "action": "需启动降脂，中等强度他汀起始（年龄≥75岁见 EL-01）。"},
    {"id": "LP-04", "domain": "调脂", "level": "常规", "source": "CN-04",
     "cond": lambda x: x.get("statin_4_6w_not_goal"),
     "action": "中等强度他汀 4~6 周仍未达标，联合依折麦布（或他汀-依折麦布复方）。"},
    {"id": "LP-05", "domain": "调脂", "level": "审核级", "source": "CN-04",
     "cond": lambda x: x.get("statin_ezetimibe_not_goal"),
     "action": "他汀+依折麦布仍未达标，联合 PCSK9 抑制剂。"},
    {"id": "LP-06", "domain": "调脂", "level": "审核级", "source": "CN-04",
     "cond": lambda x: x.get("ascvd_risk") == "超高危" and (
         (x.get("on_statin") and (x.get("baseline_ldl") or 0) >= 2.6)
         or (not x.get("on_statin") and (x.get("baseline_ldl") or 0) >= 4.9)),
     "action": "超高危且基线 LDL-C 高（服他汀≥2.6 或未服≥4.9 mmol/L）预计难达标，可直接启动他汀 + PCSK9 抑制剂。"},
    {"id": "LP-07", "domain": "调脂", "level": "审核级", "source": "CN-04",
     "cond": lambda x: x.get("statin_intolerant"),
     "action": "他汀不耐受，换用依折麦布或 PCSK9 抑制剂。"},
    {"id": "LP-08", "domain": "调脂", "level": "常规", "source": "CN-04",
     "cond": lambda x: x.get("need_start_lipid") or x.get("statin_4_6w_not_goal") or x.get("statin_ezetimibe_not_goal"),
     "action": "启动/调整降脂后，4~6 周复查血脂、肝酶、CK，达标后规律随访。"},
]

# ---------- 域3：抗缺血与心脏保护（IC，6 条） ----------
RULES += [
    {"id": "IC-01", "domain": "抗缺血", "level": "常规", "source": "CN-02/CN-06",
     "cond": lambda x: not x.get("beta_blocker_contra"),
     "action": "无禁忌（低血压/严重心动过缓/高度房室传导阻滞/急性心衰失代偿），β受体阻滞剂初始治疗（美托洛尔、比索洛尔）。"},
    {"id": "IC-02", "domain": "抗缺血", "level": "常规", "source": "CN-06",
     "cond": lambda x: not x.get("acei_contra"),
     "action": "无禁忌，长期使用 ACEI；干咳不耐受则改用 ARB。"},
    {"id": "IC-03", "domain": "抗缺血", "level": "审核级", "source": "CN-01/心衰指南",
     "cond": lambda x: x.get("hf") and x.get("lvef_reduced"),
     "action": "合并心衰且 LVEF 降低，评估「新四联」（ARNI/ACEI + β阻滞剂 + SGLT2i + 螺内酯）。"},
    {"id": "IC-04", "domain": "抗缺血", "level": "审核级", "source": "EN-01",
     "cond": lambda x: x.get("sinus_rhythm") and (x.get("lvef") or 999) < 40
             and (x.get("beta_blocker_contra") or x.get("rate_still_fast")),
     "action": "窦性心律、LVEF<40%、β阻滞剂禁忌或仍心率偏快，可加用伊伐布雷定（二线）。"},
    {"id": "IC-05", "domain": "抗缺血", "level": "常规", "source": "CN-06",
     "cond": lambda x: x.get("beta_blocker_intolerant") or x.get("angina_inadequate"),
     "action": "β阻滞剂不耐受或单药症状控制不佳，加用 CCB 或长效硝酸酯类。"},
    {"id": "IC-06", "domain": "抗缺血", "level": "审核级", "source": "EN-01",
     "cond": lambda x: x.get("residual_inflammation"),
     "action": "动脉粥样硬化性 CCS、残余炎症/事件风险高，可考虑低剂量秋水仙碱 0.5 mg qd。"},
]

# ---------- 域4：合并症用药协调（CM，12 条） ----------
def _cm07(x):
    """CM-07：房颤用 NOAC 且肾功能低于品种阈值"""
    if not x.get("on_noac"):
        return False
    t = x.get("noac_type")
    if t == "利伐沙班":
        return 15 <= (x.get("crcl") or 999) <= 49
    if t == "达比加群":
        return (x.get("crcl") or 999) < 30
    if t == "阿哌沙班":
        n = sum([x.get("age", 0) >= 80, (x.get("weight") or 999) <= 60, (x.get("scr") or 0) >= 133])
        return n >= 2
    return False


RULES += [
    {"id": "CM-01", "domain": "合并症", "level": "常规", "source": "CN-05",
     "cond": lambda x: x.get("af") and (
         (x.get("sex") == "男" and x.get("cha2ds2_vasc", 0) >= 2)
         or (x.get("sex") == "女" and x.get("cha2ds2_vasc", 0) >= 3)),
     "action": "合并房颤，CHA₂DS₂-VASc ≥2（男）/≥3（女），启动口服抗凝，首选 NOAC。"},
    {"id": "CM-02", "domain": "合并症", "level": "审核级", "source": "CN-01/CN-05",
     "cond": lambda x: x.get("af") and x.get("cha2ds2_vasc", 0) >= 2 and x.get("has_bled", 99) <= 2,
     "action": "合并房颤需抗凝+抗血小板，CHA₂DS₂-VASc≥2 且 HAS-BLED≤2：三联抗栓（DAPT+NOAC）1~6个月 → 双联（单抗+NOAC）至12个月。"},
    {"id": "CM-03", "domain": "合并症", "level": "审核级", "source": "CN-01",
     "cond": lambda x: x.get("af") and x.get("emergency_pci"),
     "action": "急诊 PCI 术后合并房颤，优先 DAPT，延迟 1~2 个月启动 NOAC。"},
    {"id": "CM-04", "domain": "合并症", "level": "审核级", "source": "EN-01/CN",
     "cond": lambda x: x.get("diabetes"),
     "action": "合并 2 型糖尿病 / ASCVD 高风险，优选 SGLT2i 或 GLP-1RA。"},
    {"id": "CM-05", "domain": "合并症", "level": "审核级", "source": "CN-01/说明书",
     "cond": lambda x: x.get("ckd") or (x.get("egfr") is not None and x.get("egfr") < 60),
     "action": "合并 CKD（eGFR 下降），抗栓、他汀等按肾功能调整；NOAC 评估减量或禁用（阈值见 CM-06/07）。"},
    {"id": "CM-06", "domain": "合并症", "level": "审核级", "source": "CN-08",
     "cond": lambda x: x.get("on_metformin") and (x.get("egfr") is not None and x.get("egfr") < 30),
     "action": "用二甲双胍且 eGFR<30，建议停用或换方案（慢性禁忌；与 JC-03 区分）。"},
    {"id": "CM-07", "domain": "合并症", "level": "审核级", "source": "CN-05",
     "cond": _cm07,
     "action": "房颤用 NOAC 且肾功能低于品种阈值：利伐沙班 CrCl 15~49 → 15 mg qd；达比加群 CrCl<30 → 禁用；阿哌沙班满足 2/3 项（≥80岁、≤60kg、Scr≥133 μmol/L）→ 2.5 mg bid。"},
    {"id": "CM-08", "domain": "合并症", "level": "常规", "source": "CN-02/CN-06",
     "cond": lambda x: x.get("asthma_copd"),
     "action": "哮喘/COPD 且需用 β受体阻滞剂，选高选择性 β1（美托洛尔/比索洛尔）；拦截非选择性品种。"},
    {"id": "CM-09", "domain": "合并症", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("gout_history") and x.get("dapt_expired"),
     "action": "痛风史且 DAPT 期满转单药，优选氯吡格雷；提示阿司匹林长期单药可升高尿酸。"},
    {"id": "CM-10", "domain": "合并症", "level": "常规", "source": "CN-01/CN-05",
     "cond": lambda x: x.get("stroke_tia_history"),
     "action": "既往缺血性卒中/TIA 史，标记高出血风险：复查频率提一档（≤1个月）；慎用三联；触发 HAS-BLED 复评。"},
    {"id": "CM-11", "domain": "合并症", "level": "常规", "source": "CN-02",
     "cond": lambda x: x.get("on_amiodarone"),
     "action": "长期用胺碘酮，每 6 个月查甲功（TSH±T4）；心悸/消瘦/畏寒随时提前复查。"},
    {"id": "CM-12", "domain": "合并症", "level": "常规", "source": "CN-07",
     "cond": lambda x: x.get("hb_low") and (x.get("post_pci") or x.get("on_antiplatelet")),
     "action": "基线 Hb<100 g/L 且仍需抗栓，强化监测：1 个月查血常规+粪隐血；纠正病因后复评。"},
]

# ---------- 域5：随访与监测（FU，3 条） ----------
RULES += [
    {"id": "FU-01", "domain": "随访", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("post_pci"),
     "action": "PCI 术后按 1/3/6/12 个月节点随访，查血脂、肝肾功能、血常规、凝血。"},
    {"id": "FU-02", "domain": "随访", "level": "常规", "source": "CN-04",
     "cond": lambda x: x.get("post_pci_months") == 6,
     "action": "术后 6 个月复查 LDL-C 评估降脂达标情况。"},
    {"id": "FU-03", "domain": "随访", "level": "常规", "source": "CN-01",
     "cond": lambda x: x.get("on_dapt"),
     "action": "DAPT 用药期间关注出血征象（牙龈/皮肤/消化道），定期血常规。"},
]

# ---------- 域7：用药行为管理（AD，3 条） ----------
RULES += [
    {"id": "AD-01", "domain": "用药行为", "level": "常规", "source": "CN-01/CN-04",
     "cond": lambda x: x.get("miss_single_dose"),
     "action": "单次漏服抗血小板药/他汀，无需补双倍剂量，下一剂按原计划服用；记录漏服事件。"},
    {"id": "AD-02", "domain": "用药行为", "level": "审核级", "source": "CN-01/CN-07",
     "cond": lambda x: x.get("want_stop_antiplatelet") and (x.get("antiplatelet_stop_days") or 0) >= 3,
     "action": "自行停用抗血小板≥3天且无症状，立即恢复原方案；术后<12个月标记「事实性停药」，建议联系上级心内科确认。"},
    {"id": "AD-05", "domain": "用药行为", "level": "常规", "source": "CN-07",
     "cond": lambda x: x.get("blood_activating"),
     "action": "自服活血类中成药/鱼油/纳豆激酶，行出血风险宣教；建议停用无循证获益品种；纳入出血监测。"},
]

# ---------- 域8：外院信息不全（XJ，1 条常规；XJ-01 在红线库） ----------
RULES += [
    {"id": "XJ-02", "domain": "接诊信息", "level": "常规", "source": "CN-01",
     "cond": lambda x: not (x.get("surgery_date") and x.get("stent_type") and x.get("discharge_plan")),
     "action": "输出《信息补全清单》：手术医院+日期、支架类型与数量、出院方案、近期化验、出院小结。"},
]

# ---------- 域9：出血事件处理（CX，2 条常规；CX-04 在红线库） ----------
RULES += [
    {"id": "CX-02", "domain": "出血处理", "level": "常规", "source": "CN-07",
     "cond": lambda x: x.get("mild_bleed"),
     "action": "轻微出血（牙龈/瘀斑，无 Hb 下降），不停抗栓；局部处理+宣教；1~2 周复查血常规+粪隐血。"},
    {"id": "CX-05", "domain": "出血处理", "level": "常规", "source": "CN-07",
     "cond": lambda x: x.get("on_dapt") and (x.get("ulcer_bleed_history") or x.get("on_nsaid_steroid")),
     "action": "服 DAPT 且（消化道溃疡/出血史 或 同时用 NSAIDs/激素），输出「建议联合 PPI（泮托拉唑）」，列入随访监测。"},
]

# ---------- 域10：临时用药与检查干扰（JC，2 条） ----------
RULES += [
    {"id": "JC-01", "domain": "临时用药", "level": "常规", "source": "CN-07",
     "cond": lambda x: x.get("need_analgesic"),
     "action": "需用镇痛药，避免 NSAIDs 与抗栓长期合用；优先对乙酰氨基酚；必须用时最小剂量 ≤3~5 天 + PPI。"},
    {"id": "JC-03", "domain": "临时用药", "level": "常规", "source": "CN-08",
     "cond": lambda x: x.get("enhance_ct") and x.get("on_metformin"),
     "action": "拟行增强 CT/造影且用二甲双胍：eGFR<30 检查前 48h 停、检查后 48h 复查肾功能再恢复；≥30 不停。"},
]

# ---------- 域11：下转接续（XZ，1 条常规；XZ-03 在红线库） ----------
RULES += [
    {"id": "XZ-02", "domain": "下转衔接", "level": "常规", "source": "CN-01/CN-06",
     "cond": lambda x: x.get("referral_plan_confirmed"),
     "action": "上级方案下转执行确认后，生成接续监测计划：复查项目+时间点+红旗症状回执单。"},
]

# ---------- 域12：血压协同（WT，1 条） ----------
RULES += [
    {"id": "WT-01", "domain": "血压协同", "level": "常规", "source": "CN-06",
     "cond": lambda x: x.get("bp_high"),
     "action": "规范服药下血压仍 ≥140/90，核依从性后以 ACEI/ARB 为基础优化，最多三联；仍不达标触发难治性高血压转诊。"},
]

# ---------- 域13：老年人群（EL，3 条） ----------
RULES += [
    {"id": "EL-01", "domain": "老年", "level": "常规", "source": "CN-04",
     "cond": lambda x: x.get("tag_el") and (x.get("need_start_lipid") or x.get("statin_4_6w_not_goal")),
     "action": "年龄≥75岁且启动/调整他汀，一律中强度起始；4~6 周复查血脂+肝酶+CK 后评估。"},
    {"id": "EL-02", "domain": "老年", "level": "常规", "source": "CN-06",
     "cond": lambda x: (x.get("age", 0) >= 80) and x.get("bp_high"),
     "action": "年龄≥80岁且高血压，降压目标放宽至 <150/90；与 WT-01 冲突时优先本条。"},
    {"id": "EL-03", "domain": "老年", "level": "常规", "source": "CN-06",
     "cond": lambda x: x.get("tag_el") and x.get("diabetes"),
     "action": "年龄≥75岁且合并2型糖尿病，避免长效磺脲；优先 DPP-4i 或低剂量短效；低血糖宣教。"},
]

# ---------- 域14：ADR 实验室判读（LB，2 条常规；LB-02/04/05 在红线库） ----------
RULES += [
    {"id": "LB-01", "domain": "ADR判读", "level": "常规", "source": "CN-04/CN-06",
     "cond": lambda x: x.get("alt_ast_status") == "轻度升高",
     "action": "ALT/AST ≥1× 且 <3× 正常上限、无症状，他汀继续原剂量，4 周复查肝功能；无需停药/转诊。"},
    {"id": "LB-03", "domain": "ADR判读", "level": "审核级", "source": "CN-04",
     "cond": lambda x: x.get("ck_status") == "中度升高",
     "action": "CK 4~10× 正常上限且无症状，暂停他汀；复查 CK；评估症状后再启动。"},
]


# ---------- 域15：降压药不良反应关联（HT，5 条） ----------
def _ht03(x):
    return x.get("on_acei_arb") and x.get("acei_arb_type") == "ACEI" and x.get("dry_cough")

RULES += [
    {"id": "HT-01", "domain": "降压药ADR", "level": "审核级", "source": "CN-06/说明书",
     "cond": lambda x: x.get("potassium_status") == "高",
     "action": "血钾升高（高钾血症）：建议立即复查血钾+心电图；若在用 ACEI/ARB/螺内酯，考虑药物相关并减量/停药。"},
    {"id": "HT-02", "domain": "降压药ADR", "level": "常规", "source": "CN-06/说明书",
     "cond": lambda x: x.get("potassium_status") == "低",
     "action": "血钾降低（低钾血症）：建议补钾并复查电解质；若在用袢利尿剂/噻嗪类，考虑药物相关。"},
    {"id": "HT-03", "domain": "降压药ADR", "level": "常规", "source": "CN-06",
     "cond": _ht03,
     "action": "干咳且在用 ACEI，考虑 ACEI 相关不良反应，建议更换为 ARB。"},
    {"id": "HT-04", "domain": "降压药ADR", "level": "常规", "source": "说明书",
     "cond": lambda x: x.get("on_ccb") and x.get("ccb_type") == "二氢吡啶类" and x.get("edema"),
     "action": "踝部/下肢水肿且在用二氢吡啶类 CCB，考虑 CCB 相关，可评估减量或联合 ACEI/ARB。"},
    {"id": "HT-05", "domain": "降压药ADR", "level": "审核级", "source": "说明书",
     "cond": lambda x: x.get("on_beta_blocker") and x.get("bradycardia"),
     "action": "静息心动过缓且在用 β 阻滞剂，警惕 β 阻滞剂相关（剂量过大/传导阻滞），建议评估减量并复查心电图。"},
]

# ---------- 域16：用药变化预警（MC，1 条） ----------
def _mc01(x):
    dc = set(x.get("discharge_meds") or [])
    p2y12 = {"氯吡格雷", "替格瑞洛"}
    was_dapt = len(dc & (p2y12 | {"阿司匹林", "吲哚布芬"})) >= 2
    cur = sum([bool(x.get("on_aspirin")), bool(x.get("on_clopidogrel")),
               bool(x.get("on_ticagrelor")), bool(x.get("on_indobufen"))])
    now_single = cur == 1
    months = x.get("post_pci_months", 0)
    not_expired = months < (6 if x.get("scenario") == "CCS" else 12)
    return was_dapt and now_single and not_expired

RULES += [
    {"id": "MC-01", "domain": "用药变化", "level": "审核级", "source": "CN-01/CN-07",
     "cond": _mc01,
     "action": "检测到抗血小板由出院 DAPT 降级为单药且术后未满疗程（<12 个月，CCS<6 个月）："
               "若为擅自停药，请立即恢复原方案并联系上级；若为医嘱调整，请确认疗程依据；"
               "若同时存在出血征象或红旗症状，系统将另行提示转诊/处理（见对应红线与出血规则）。"},
]

# ---------- 域17：新增实验室判读（LB 追加，3 条，状态型） ----------
RULES += [
    {"id": "LB-06", "domain": "ADR判读", "level": "审核级", "source": "心内/EN-01",
     "cond": lambda x: bool(x.get("troponin_elevated")),
     "action": "肌钙蛋白升高：提示心肌损伤/再梗死可能，建议复查肌钙蛋白+心电图，评估是否 ACS 再发（结合近期 PCI 基线判断）。"},
    {"id": "LB-07", "domain": "ADR判读", "level": "常规", "source": "CN-08",
     "cond": lambda x: x.get("fbg_status") == "高" or (x.get("hba1c") is not None and x.get("hba1c") >= 6.5),
     "action": "血糖未达标（空腹血糖升高或 HbA1c ≥6.5%）：提示糖尿病管理需优化，结合 CM-04 优选 SGLT2i/GLP-1RA。"},
    {"id": "LB-08", "domain": "ADR判读", "level": "审核级", "source": "CN-08",
     "cond": lambda x: x.get("fbg_status") == "低",
     "action": "低血糖（空腹血糖降低）：警惕（尤其磺脲/胰岛素时），立即纠正并评估诱因，低血糖可诱发心肌缺血。"},
]

# ================= 匹配引擎 =================
def resolve_conflicts(hit_ids):
    """规则间冲突消解（v3.2 第三部分第 6 条）"""
    if "EL-02" in hit_ids and "WT-01" in hit_ids:
        hit_ids.discard("WT-01")  # EL-02（≥80岁降压放宽）优先于 WT-01
    return hit_ids


def match(patient):
    tags = compute_tags(patient)
    ctx = {**patient, **tags}  # 合并：患者字段 + 人群标签

    criticals = check_critical(patient)  # 危急值检查（最高优先级，独立于用药规则）
    hit_red = [r for r in REDLINES if r["cond"](ctx)]
    # 危急值 / 红线命中时，不输出常规建议（危急值、红线库 > 一切生成建议）
    hit_rules = [] if (criticals or hit_red) else [r for r in RULES if r["cond"](ctx)]

    if hit_rules:
        ids = resolve_conflicts({r["id"] for r in hit_rules})
        hit_rules = [r for r in hit_rules if r["id"] in ids]

    return {
        "tags": tags,
        "critical": criticals,
        "redlines": [{"id": r["id"], "name": r["name"], "action": r["action"]} for r in hit_red],
        "advices": [{"id": r["id"], "domain": r["domain"], "source": r["source"], "level": r["level"],
                     "action": r["action"]} for r in hit_rules],
    }


# ================= 内置演示 =================
if __name__ == "__main__":
    def _show(r):
        print("标签：", r["tags"])
        if r["redlines"]:
            for x in r["redlines"]:
                print(f"  [红线 {x['id']}] {x['name']}\n      → {x['action']}")
        else:
            print("红线：无")
            for x in r["advices"]:
                print(f"  [{x['id']}｜{x['level']}] {x['action']}  （出处 {x['source']}）")
            if not r["advices"]:
                print("  （无命中规则）")

    print("=" * 62)
    print("演示1：ACS、PCI术后8个月，患者想停抗血小板药 → 命中 RL-01 硬拦截")
    _show(match({"scenario": "ACS", "post_pci": True, "post_pci_months": 8,
                 "want_stop_antiplatelet": True,
                 "surgery_date": "2026-08-01", "stent_type": "药物洗脱支架×1",
                 "discharge_plan": "DAPT 12个月"}))

    print("\n" + "=" * 62)
    print("演示2：CCS、PCI术后，极高危复诊（无红线）→ 输出 DAPT 时长 + LDL 目标")
    _show(match({"scenario": "CCS", "post_pci": True, "post_pci_months": 2,
                 "ascvd_risk": "极高危", "age": 55, "on_dapt": True,
                 "surgery_date": "2026-08-01", "stent_type": "药物洗脱支架×1",
                 "discharge_plan": "DAPT 6个月"}))

    print("\n" + "=" * 62)
    print("演示3：ACS 术后 + 房颤 + 糖尿病 → 多规则联动（CM-01 抗凝、AP-06 首选替格瑞洛等）")
    _show(match({
        "scenario": "ACS", "post_pci": True, "post_pci_months": 1, "age": 62,
        "sex": "男", "af": True, "cha2ds2_vasc": 3, "has_bled": 2,
        "diabetes": True, "ascvd_risk": "超高危", "on_dapt": True,
        "surgery_date": "2026-09-10", "stent_type": "药物洗脱支架×2",
        "discharge_plan": "DAPT 12个月",
    }))