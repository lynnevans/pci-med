<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue'
import {
  WarningFilled,
  InfoFilled,
  Document,
  RefreshLeft,
  FirstAidKit,
  Camera,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ChatView from './ChatView.vue'

// ==================== 类型定义 ====================
type FieldType = 'number' | 'boolean' | 'date' | 'select' | 'text' | 'multi'

interface Field {
  key: string
  label: string
  type: FieldType
  unit?: string
  min?: number
  max?: number
  options?: string[]
  dangerOptions?: string[]  // 需要红色标高的选项（出血征象）
  placeholder?: string
  required?: boolean
  note?: string
  dependsOn?: string
  multiMap?: boolean  // 多选字段需要拆分翻译（症状/ADR/出血）
}

interface ExamSub {
  key: string
  label: string
  type: 'bool' | 'status' | 'number'
  options?: string[]
  unit?: string
}

interface ExamCard {
  name: string
  items: string
  fields: ExamSub[]
}

interface MedSingleGroup {
  key: string
  name: string
  desc: string
  options: string[]  // 首项为「未使用」
  note?: string
}

interface MedMultiGroup {
  key: string
  name: string
  desc: string
  options: string[]
}

interface Antiplatelet {
  key: string
  label: string
  std: string
  discharge: number | null
  now: number | null
}

interface Advice {
  id: string
  level: string
  source: string
  action: string
}

interface Redline {
  id: string
  name: string
  action: string
}

interface AnalyzeResult {
  tags: Record<string, boolean>
  redlines: Redline[]
  advices: Advice[]
  disclaimer?: string
}

// ==================== 界面 1 · 基本信息 ====================
const step1Fields: Field[] = [
  { key: 'age', label: '年龄', type: 'number', unit: '岁', min: 0, max: 120, required: true },
  { key: 'sex', label: '性别', type: 'select', options: ['男', '女'], required: true },
  { key: 'weight', label: '体重', type: 'number', unit: 'kg', min: 0, max: 300 },
  { key: 'post_pci', label: '是否 PCI 术后', type: 'boolean', required: true, note: '本系统针对 PCI 术后，默认开启' },
  { key: 'emergency_pci', label: '是否急诊 PCI', type: 'boolean' },
  { key: 'surgery_date', label: '手术日期', type: 'date', required: true, note: '填日期后自动计算术后时长' },
  { key: 'post_pci_months', label: '术后时长', type: 'number', unit: '月', min: 0, max: 240, required: true, note: '由手术日期自动计算，可手动修正' },
  { key: 'diagnosis', label: '出院诊断', type: 'select', required: true, options: ['急性ST段抬高型心梗', '急性非ST段抬高型心梗', '不稳定型心绞痛', '稳定型心绞痛', '缺血性心肌病'], note: '前三种为 ACS 场景，后两种为 CCS 场景' },
  { key: 'vessels', label: '病变支数', type: 'select', options: ['单支', '双支', '三支'], note: '双支及以上记为多支病变' },
  { key: 'target_vessel', label: '干预血管', type: 'multi', options: ['左主干', '左前降支', '回旋支', '右冠'], note: '左主干纳入高缺血风险' },
  { key: 'dcb_count', label: '药物涂层球囊 DCB（个）', type: 'number', min: 0, max: 20 },
  { key: 'brs_count', label: '可吸收支架 BRS（枚）', type: 'number', min: 0, max: 20 },
  { key: 'des_count', label: '药物洗脱支架 DES（枚）', type: 'number', min: 0, max: 20, note: '支架类型由数量自动生成' },
  { key: 'ascvd_risk', label: 'ASCVD 危险分层', type: 'select', options: ['极高危', '超高危'], note: '用于降脂目标判断' },
  { key: 'discharge_plan', label: '出院抗栓方案', type: 'text', required: true, placeholder: '如：DAPT 12 个月' },
]

// ==================== 界面 2 · 合并症与既往史 ====================
const step2Fields: Field[] = [
  { key: 'hypertension_grade', label: '高血压分级', type: 'select', options: ['无', '1级', '2级', '3级', '单纯收缩期'] },
  { key: 'bp_high', label: '规范服药下血压仍 ≥140/90', type: 'boolean' },
  { key: 'comorbidities', label: '其他合并症', type: 'multi', multiMap: true, options: ['糖尿病', '高脂血症', '房颤', '心衰', 'COPD', '哮喘', 'CKD'], note: '哮喘与 COPD 均归入气道疾病' },
  { key: 'cha2ds2_vasc', label: 'CHA₂DS₂-VASc 评分', type: 'number', min: 0, max: 9, note: '合并房颤时填写（用于抗凝决策）' },
  { key: 'has_bled', label: 'HAS-BLED 评分', type: 'number', min: 0, max: 9 },
  { key: 'precis_dapt', label: 'PRECISE-DAPT 评分', type: 'number', min: 0, max: 60 },
  { key: 'cv_history', label: '心脑血管既往史', type: 'multi', multiMap: true, options: ['既往心梗史', '既往卒中/TIA史'] },
  { key: 'other_history', label: '其他相关既往史', type: 'multi', multiMap: true, options: ['痛风史', '消化道溃疡/出血史', '颅内出血史'] },
  { key: 'clinical', label: '临床判断', type: 'multi', multiMap: true, options: ['无新发缺血事件', '残余炎症/事件高风险'] },
  { key: 'other_pmh', label: '其他既往史', type: 'text', placeholder: '选填' },
]

// ==================== 界面 3 · 辅助检查（状态化卡片） ====================
const examCards: ExamCard[] = [
  { name: '血常规', items: 'Hb / WBC / PLT', fields: [
    { key: 'hb_low', label: '血红蛋白降低', type: 'bool' },
    { key: 'plt_status', label: '血小板', type: 'status', options: ['正常', '降低'] },
    { key: 'plt_drop_over_50pct', label: 'PLT 较基线下降>50%', type: 'bool' },
  ]},
  { name: '尿常规', items: '蛋白 / 潜血', fields: [
    { key: 'brown_urine', label: '潜血 / 褐色尿', type: 'bool' },
  ]},
  { name: '肝功能', items: 'ALT / AST / 总胆红素', fields: [
    { key: 'alt_ast_status', label: 'ALT/AST', type: 'status', options: ['正常', '轻度升高', '重度升高'] },
    { key: 'jaundice', label: '皮肤巩膜黄染', type: 'bool' },
  ]},
  { name: '肾功能', items: '肌酐 / eGFR', fields: [
    { key: 'scr', label: '血肌酐 Scr', type: 'number', unit: 'μmol/L' },
    { key: 'egfr', label: 'eGFR', type: 'number', unit: 'ml/min/1.73m²' },
    { key: 'crcl', label: '肌酐清除率 CrCl', type: 'number', unit: 'ml/min' },
  ]},
  { name: '凝血功能', items: 'PT / APTT / INR', fields: [
    { key: 'coag_abnormal', label: '凝血功能异常', type: 'bool' },
  ]},
  { name: '心肌酶谱', items: 'CK / CK-MB', fields: [
    { key: 'ck_status', label: 'CK', type: 'status', options: ['正常', '中度升高', '重度升高'] },
  ]},
  { name: '肌钙蛋白', items: 'cTnI / cTnT', fields: [
    { key: 'troponin_elevated', label: '肌钙蛋白升高', type: 'bool' },
  ]},
  { name: '电解质', items: 'K⁺ / Na⁺ / Mg²⁺', fields: [
    { key: 'potassium_status', label: '血钾', type: 'status', options: ['正常', '高', '低'] },
  ]},
  { name: '血脂', items: 'LDL-C / TG / HDL-C', fields: [
    { key: 'baseline_ldl', label: 'LDL-C', type: 'number', unit: 'mmol/L' },
  ]},
  { name: '空腹血糖和糖化', items: 'FPG / HbA1c', fields: [
    { key: 'fbg_status', label: '空腹血糖', type: 'status', options: ['正常', '高', '低'] },
    { key: 'hba1c', label: '糖化血红蛋白', type: 'number', unit: '%' },
  ]},
  { name: '十二导联心电图', items: 'ST-T / 心律失常', fields: [
    { key: 'sinus_rhythm', label: '窦性心律', type: 'bool' },
  ]},
  { name: '超声心动图', items: 'EF / 室壁瘤 / 室壁运动', fields: [
    { key: 'lvef', label: 'LVEF', type: 'number', unit: '%' },
    { key: 'wall_abnormality', label: '室壁瘤/室壁运动异常', type: 'bool' },
  ]},
]

// ==================== 界面 4 · 用药 ====================
const antiplatelets = reactive<Antiplatelet[]>([
  { key: 'aspirin', label: '阿司匹林', std: '标准 100 mg qd', discharge: null, now: null },
  { key: 'clopidogrel', label: '氯吡格雷', std: '标准 75 mg qd', discharge: null, now: null },
  { key: 'ticagrelor', label: '替格瑞洛', std: '标准 90 mg bid', discharge: null, now: null },
  { key: 'indobufen', label: '吲哚布芬', std: '标准 100 mg bid', discharge: null, now: null },
])

const medSingleGroups: MedSingleGroup[] = [
  { key: 'noac', name: '口服抗凝药', desc: '利伐沙班 / 达比加群 / 阿哌沙班 / 艾多沙班 / 华法林', options: ['未使用', '利伐沙班', '达比加群', '阿哌沙班', '艾多沙班', '华法林'], note: 'NOAC 品种（利伐沙班/达比加群/阿哌沙班）参与肾功能减量阈值判断' },
  { key: 'beta_blocker', name: 'β 受体阻滞剂', desc: '美托洛尔 / 比索洛尔 / 卡维地洛', options: ['未使用', '美托洛尔', '比索洛尔', '卡维地洛'] },
  { key: 'arni', name: 'ARNI / ACEI / ARB', desc: '肾素-血管紧张素系统抑制剂', options: ['未使用', 'ARNI', 'ACEI', 'ARB'] },
  { key: 'diuretic', name: '利尿剂', desc: '呋塞米 / 螺内酯 / 氢氯噻嗪 / 吲达帕胺', options: ['未使用', '呋塞米', '螺内酯', '氢氯噻嗪', '吲达帕胺'] },
  { key: 'ppi', name: 'PPI 类（质子泵抑制剂）', desc: '护胃 / 预防消化道出血', options: ['未使用', '奥美拉唑', '艾司奥美拉唑', '泮托拉唑', '雷贝拉唑'] },
  { key: 'ccb', name: 'CCB 类（钙通道阻滞剂）', desc: '氨氯地平 / 硝苯地平 / 维拉帕米 / 地尔硫䓬', options: ['未使用', '氨氯地平', '硝苯地平', '维拉帕米', '地尔硫䓬'] },
]

const medMultiGroups: MedMultiGroup[] = [
  { key: 'lipid', name: '降脂类', desc: '他汀 / 依折麦布 / PCSK9', options: ['他汀类', '依折麦布', 'PCSK9抑制剂'] },
  { key: 'glucose', name: '降糖类', desc: '口服降糖药 / GLP-1RA / 胰岛素', options: ['二甲双胍', 'SGLT2i', 'GLP-1RA', '磺脲类', 'DPP-4i', '胰岛素'] },
  { key: 'others', name: '其他', desc: '硝酸酯 / 胺碘酮 / PDE5i / NSAIDs / 未列药品', options: ['硝酸酯类', '胺碘酮', 'PDE5抑制剂', 'NSAIDs或激素', '其他（填药名）'] },
]

const lipidPhases = [
  { key: '', label: '无特殊阶段' },
  { key: 'start', label: '首次启动降脂' },
  { key: 'w46', label: '中等强度他汀4-6周未达标' },
  { key: 'comb', label: '他汀+依折麦布仍未达标' },
  { key: 'intol', label: '他汀不耐受' },
]

// 用药相关特殊情况（耐受性/禁忌/抵抗/三联抗栓，后端规则硬依赖）
const medSpecialFields: Field[] = [
  { key: 'aspirin_intolerant', label: '阿司匹林过敏/不耐受', type: 'boolean' },
  { key: 'ticagrelor_intolerant', label: '替格瑞洛不耐受/禁忌', type: 'boolean' },
  { key: 'cyp2c19_loss', label: '氯吡格雷抵抗（CYP2C19 功能缺失）', type: 'boolean' },
  { key: 'beta_blocker_contra', label: 'β 阻滞剂禁忌', type: 'boolean' },
  { key: 'beta_blocker_intolerant', label: 'β 阻滞剂不耐受', type: 'boolean' },
  { key: 'acei_contra', label: 'ACEI 禁忌', type: 'boolean' },
  { key: 'triple_therapy_months', label: '三联抗栓已叠加月数', type: 'number', unit: '月', min: 0, note: 'DAPT + 口服抗凝同用时填写' },
]

// ==================== 界面 5 · 症状与用药行为 ====================
const step5Fields: Field[] = [
  { key: 'symptoms', label: '症状表现', type: 'multi', multiMap: true, options: ['胸痛', '胸闷气短', '晕厥', '活动耐量下降'], note: '任一存在按红旗症状处理，优先转诊' },
  { key: 'adr', label: '药物相关表现', type: 'multi', multiMap: true, options: ['干咳', '踝部/下肢水肿', '静息心动过缓', '心率仍偏快', '抗缺血控制不佳'] },
  { key: 'bleeding', label: '出血征象', type: 'multi', multiMap: true, options: ['淤青', '牙龈出血', '呕血', '尿血', '黑便', '近期致命出血史', '颅内出血史'], dangerOptions: ['呕血', '尿血', '黑便', '近期致命出血史', '颅内出血史'], note: '标红项为严重/致命出血，需紧急处理' },
  { key: 'miss_single_dose', label: '单次漏服抗血小板/他汀', type: 'boolean' },
  { key: 'self_stop_days', label: '自行停药天数', type: 'number', unit: '天', min: 0 },
  { key: 'want_stop_antiplatelet', label: '患者拟停用抗血小板药', type: 'boolean' },
  { key: 'blood_activating', label: '自服活血中成药/鱼油/纳豆激酶', type: 'boolean' },
  { key: 'need_analgesic', label: '需用镇痛药', type: 'boolean' },
  { key: 'enhance_ct', label: '拟行增强 CT / 造影', type: 'boolean' },
  { key: 'planned_surgery', label: '拟行其他手术', type: 'text', placeholder: '选填' },
  { key: 'referral_plan_confirmed', label: '上级方案下转已确认', type: 'boolean' },
  { key: 'recent_symptom_after_referral', label: '下转后 1 个月内再发症状', type: 'boolean' },
]

// ==================== 步骤 ====================
const steps = [
  { title: '基本信息', desc: '年龄、性别、手术记录、出院诊断' },
  { title: '合并症与既往史', desc: '既往病史、共病、危险因素' },
  { title: '辅助检查', desc: '按本实验室参考范围判定升高/降低' },
  { title: '用药', desc: '抗血小板对比出院时/现在，其余记录当前用药' },
  { title: '症状与用药行为', desc: '红旗症状、出血征象、漏服停药' },
]

// ==================== 表单状态 ====================
const form = reactive<Record<string, any>>({})

function initField(f: Field, container: Record<string, any>): void {
  if (f.type === 'boolean') container[f.key] = false
  else if (f.type === 'multi') container[f.key] = []
  else if (f.type === 'number') container[f.key] = null
  else container[f.key] = null
}

for (const f of [...step1Fields, ...step2Fields, ...step5Fields]) initField(f, form)
for (const c of examCards) {
  for (const f of c.fields) {
    if (f.type === 'bool') form[f.key] = false
    else if (f.type === 'status') form[f.key] = '正常'
    else form[f.key] = null
  }
}
for (const g of medSingleGroups) form[g.key] = '未使用'
for (const g of medMultiGroups) form[g.key] = []
for (const f of medSpecialFields) initField(f, form)
form.lipid_phase = ''
form.other_med_name = ''
form.post_pci = true // PCI 术后默认开启

const view = ref<'form' | 'chat'>('form')
const openGroups = ref<string[]>([])
const currentStep = ref<number>(0)
const loading = ref<boolean>(false)
const result = ref<AnalyzeResult | null>(null)
const errorMsg = ref<string>('')

const currentFields = computed<Field[]>(() => {
  if (currentStep.value === 0) return step1Fields
  if (currentStep.value === 1) return step2Fields
  if (currentStep.value === 4) return step5Fields
  return []
})

// 手术日期自动计算术后时长（月）
watch(
  () => form.surgery_date,
  (d) => {
    if (!d) return
    const date = new Date(d as string)
    const months = Math.max(0, Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24 * 30)))
    form.post_pci_months = months
  }
)

// ==================== 提交流程：字段翻译 ====================
const DIAG_TO_SCENARIO: Record<string, string> = {
  急性ST段抬高型心梗: 'ACS',
  急性非ST段抬高型心梗: 'ACS',
  不稳定型心绞痛: 'ACS',
  稳定型心绞痛: 'CCS',
  缺血性心肌病: 'CCS',
}

const VESSEL_TO_NUM: Record<string, number> = { 单支: 1, 双支: 2, 三支: 3 }

const ADR_MAP: Record<string, string> = {
  干咳: 'dry_cough',
  '踝部/下肢水肿': 'edema',
  静息心动过缓: 'bradycardia',
  心率仍偏快: 'rate_still_fast',
  抗缺血控制不佳: 'angina_inadequate',
}

const BLEED_MILD = ['淤青', '牙龈出血']
const BLEED_SEVERE = ['呕血', '尿血', '黑便']

function setIf(p: Record<string, any>, k: string, v: any, cond = true): void {
  if (cond && v !== null && v !== undefined && v !== '' && v !== false) p[k] = v
}

function buildAntiplateletPayload(p: Record<string, any>): void {
  const nowKey: Record<string, string> = {
    aspirin: 'on_aspirin', clopidogrel: 'on_clopidogrel',
    ticagrelor: 'on_ticagrelor', indobufen: 'on_indobufen',
  }
  const doseKey: Record<string, string> = {
    aspirin: 'aspirin_dose', clopidogrel: 'clopidogrel_dose', ticagrelor: 'ticagrelor_dose',
  }
  const discharge: string[] = []
  for (const a of antiplatelets) {
    if (a.discharge && a.discharge > 0) discharge.push(a.label)
    if (a.now && a.now > 0) {
      p[nowKey[a.key]] = true
      if (doseKey[a.key]) p[doseKey[a.key]] = a.now
    }
  }
  if (discharge.length) p['discharge_meds'] = discharge
  const curAps = ['aspirin', 'clopidogrel', 'ticagrelor', 'indobufen'].filter((k) => p[nowKey[k]] === true)
  if (curAps.length >= 1) p['on_antiplatelet'] = true
  if (curAps.length >= 2) p['on_dapt'] = true
}

function buildPayload(): Record<string, any> {
  const p: Record<string, any> = {}

  // ---------- 界面 1 ----------
  setIf(p, 'age', form.age)
  setIf(p, 'sex', form.sex)
  setIf(p, 'weight', form.weight)
  setIf(p, 'post_pci', form.post_pci, form.post_pci === true)
  setIf(p, 'emergency_pci', form.emergency_pci, form.emergency_pci === true)
  if (form.surgery_date) p['surgery_date'] = form.surgery_date
  setIf(p, 'post_pci_months', form.post_pci_months)
  if (form.ascvd_risk) p['ascvd_risk'] = form.ascvd_risk
  if (form.discharge_plan) p['discharge_plan'] = form.discharge_plan
  // 出院诊断 → scenario + discharge_diagnosis
  if (form.diagnosis) {
    p['discharge_diagnosis'] = form.diagnosis
    const sc = DIAG_TO_SCENARIO[form.diagnosis]
    if (sc) p['scenario'] = sc
  }
  // 病变支数 → vessel_count + multivessel
  if (form.vessels && VESSEL_TO_NUM[form.vessels]) {
    p['vessel_count'] = VESSEL_TO_NUM[form.vessels]
    if (VESSEL_TO_NUM[form.vessels] >= 2) p['multivessel'] = true
  }
  // 干预血管 → target_vessel（左前降支→前降支）
  if (Array.isArray(form.target_vessel) && form.target_vessel.length) {
    p['target_vessel'] = form.target_vessel.map((v: string) => (v === '左前降支' ? '前降支' : v))
  }
  // 干预方式 → dcb + stent_type
  if (form.dcb_count && form.dcb_count > 0) p['dcb'] = true
  const stents: string[] = []
  if (form.des_count && form.des_count > 0) stents.push(`药物洗脱支架×${form.des_count}`)
  if (form.brs_count && form.brs_count > 0) stents.push(`可吸收支架×${form.brs_count}`)
  if (stents.length) p['stent_type'] = stents.join('、')

  // ---------- 界面 2 ----------
  if (form.hypertension_grade && form.hypertension_grade !== '无') p['hypertension_grade'] = form.hypertension_grade
  setIf(p, 'bp_high', form.bp_high, form.bp_high === true)
  const comorbMap: Record<string, string> = {
    糖尿病: 'diabetes', 高脂血症: 'dyslipidemia', 房颤: 'af', 心衰: 'hf',
    COPD: 'asthma_copd', 哮喘: 'asthma_copd', CKD: 'ckd',
  }
  for (const c of (form.comorbidities || []) as string[]) {
    if (comorbMap[c]) p[comorbMap[c]] = true
  }
  setIf(p, 'cha2ds2_vasc', form.cha2ds2_vasc)
  setIf(p, 'has_bled', form.has_bled)
  setIf(p, 'precis_dapt', form.precis_dapt)
  const cvMap: Record<string, string> = { 既往心梗史: 'prior_mi_stroke', '既往卒中/TIA史': 'stroke_tia_history' }
  for (const c of (form.cv_history || []) as string[]) if (cvMap[c]) p[cvMap[c]] = true
  const otherMap: Record<string, string> = { 痛风史: 'gout_history', '消化道溃疡/出血史': 'ulcer_bleed_history', 颅内出血史: 'ich_history' }
  for (const c of (form.other_history || []) as string[]) if (otherMap[c]) p[otherMap[c]] = true
  const clinicalMap: Record<string, string> = { 无新发缺血事件: 'no_new_ischemia', '残余炎症/事件高风险': 'residual_inflammation' }
  for (const c of (form.clinical || []) as string[]) if (clinicalMap[c]) p[clinicalMap[c]] = true
  if (form.other_pmh) p['other_pmh'] = form.other_pmh

  // ---------- 界面 3：状态字段直接收集（key 与后端一致） ----------
  for (const c of examCards) {
    for (const f of c.fields) {
      const v = form[f.key]
      if (f.type === 'bool') {
        if (v === true) p[f.key] = true
      } else if (f.type === 'status') {
        if (v && v !== '正常') p[f.key] = v
      } else if (f.type === 'number') {
        if (v !== null && v !== undefined && v !== '') p[f.key] = Number(v)
      }
    }
  }
  // LVEF 降低推导
  if (form.lvef !== null && form.lvef !== undefined && form.lvef !== '') {
    if (Number(form.lvef) < 40) p['lvef_reduced'] = true
  }

  // ---------- 界面 4：用药翻译 ----------
  buildAntiplateletPayload(p)
  const singleMap: Record<string, { on: string; type: string }> = {
    noac: { on: 'on_noac', type: 'noac_type' },
    beta_blocker: { on: 'on_beta_blocker', type: 'beta_blocker_type' },
    arni: { on: 'on_acei_arb', type: 'acei_arb_type' },
    diuretic: { on: 'on_diuretic', type: 'diuretic_type' },
    ppi: { on: '', type: 'ppi' },  // ppi 无 on_ 前缀
    ccb: { on: 'on_ccb', type: 'ccb_type' },
  }
  const CCB_TYPE: Record<string, string> = { 氨氯地平: '二氢吡啶类', 硝苯地平: '二氢吡啶类', 维拉帕米: '非二氢吡啶类', 地尔硫䓬: '非二氢吡啶类' }
  for (const g of medSingleGroups) {
    const v = form[g.key]
    if (!v || v === '未使用') continue
    const m = singleMap[g.key]
    if (g.key === 'ppi') p['ppi'] = v
    else {
      p[m.on] = true
      p[m.type] = g.key === 'ccb' ? CCB_TYPE[v] : v
    }
  }
  // 降脂类
  if ((form.lipid || []).includes('他汀类')) p['on_statin'] = true
  if (form.lipid_phase === 'start') p['need_start_lipid'] = true
  else if (form.lipid_phase === 'w46') p['statin_4_6w_not_goal'] = true
  else if (form.lipid_phase === 'comb') p['statin_ezetimibe_not_goal'] = true
  else if (form.lipid_phase === 'intol') p['statin_intolerant'] = true
  // 降糖类
  if ((form.glucose || []).includes('二甲双胍')) p['on_metformin'] = true
  // 其他
  const othersMap: Record<string, string> = { 硝酸酯类: 'on_nitrate', 胺碘酮: 'on_amiodarone', 'PDE5抑制剂': 'on_pde5i', 'NSAIDs或激素': 'on_nsaid_steroid' }
  for (const o of (form.others || []) as string[]) if (othersMap[o]) p[othersMap[o]] = true
  // 「其他（填药名）」：未列药品统一记录留痕（后端无对应规则字段，仅作用药记录，不扩充降压药列表）
  if ((form.others || []).includes('其他（填药名）') && form.other_med_name) p['other_med_name'] = form.other_med_name
  // 用药特殊情况（耐受性/禁忌/抵抗/三联抗栓）
  for (const f of medSpecialFields) {
    const v = form[f.key]
    if (f.type === 'boolean') { if (v === true) p[f.key] = true }
    else if (f.type === 'number' && v !== null && v !== '' && v !== undefined) p[f.key] = Number(v)
  }

  // ---------- 界面 5：症状/出血翻译 + 直接字段 ----------
  if ((form.symptoms || []).length) p['red_flag'] = true
  for (const a of (form.adr || []) as string[]) if (ADR_MAP[a]) p[ADR_MAP[a]] = true
  for (const b of (form.bleeding || []) as string[]) {
    if (BLEED_MILD.includes(b)) p['mild_bleed'] = true
    else if (BLEED_SEVERE.includes(b)) p['red_flag'] = true
    else if (b === '近期致命出血史') p['recent_fatal_bleed'] = true
    else if (b === '颅内出血史') p['ich_history'] = true
  }
  setIf(p, 'miss_single_dose', form.miss_single_dose, form.miss_single_dose === true)
  setIf(p, 'self_stop_days', form.self_stop_days)
  setIf(p, 'want_stop_antiplatelet', form.want_stop_antiplatelet, form.want_stop_antiplatelet === true)
  setIf(p, 'blood_activating', form.blood_activating, form.blood_activating === true)
  setIf(p, 'need_analgesic', form.need_analgesic, form.need_analgesic === true)
  setIf(p, 'enhance_ct', form.enhance_ct, form.enhance_ct === true)
  if (form.planned_surgery) p['planned_surgery'] = form.planned_surgery
  setIf(p, 'referral_plan_confirmed', form.referral_plan_confirmed, form.referral_plan_confirmed === true)
  setIf(p, 'recent_symptom_after_referral', form.recent_symptom_after_referral, form.recent_symptom_after_referral === true)

  // ---------- 时间推导 ----------
  const months = Number(p['post_pci_months']) || 0
  const daptTarget = p['scenario'] === 'CCS' ? 6 : 12
  if (months >= daptTarget) p['dapt_expired'] = true
  if (months >= 12) p['long_term_phase'] = true

  return p
}

async function submit(): Promise<void> {
  loading.value = true
  errorMsg.value = ''
  result.value = null
  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPayload()),
    })
    if (!resp.ok) throw new Error('接口返回 ' + resp.status)
    result.value = (await resp.json()) as AnalyzeResult
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    errorMsg.value = '调用后端失败：' + msg + '。请确认 uvicorn 已在 backend 目录启动。'
  } finally {
    loading.value = false
  }
}

function reset(): void {
  for (const f of [...step1Fields, ...step2Fields, ...step5Fields]) initField(f, form)
  for (const c of examCards) {
    for (const f of c.fields) {
      if (f.type === 'bool') form[f.key] = false
      else if (f.type === 'status') form[f.key] = '正常'
      else form[f.key] = null
    }
  }
  for (const g of medSingleGroups) form[g.key] = '未使用'
  for (const g of medMultiGroups) form[g.key] = []
  for (const f of medSpecialFields) initField(f, form)
  form.lipid_phase = ''
  form.post_pci = true
  for (const a of antiplatelets) { a.discharge = null; a.now = null }
  currentStep.value = 0
  result.value = null
  errorMsg.value = ''
}

const tagText: Record<string, string> = { tag_br: '高出血风险', tag_ir: '高缺血风险', tag_el: '老年(≥75)' }
const activeTags = computed<string[]>(() => {
  if (!result.value || !result.value.tags) return []
  return Object.entries(result.value.tags)
    .filter(([, v]) => v)
    .map(([k]) => tagText[k] ?? k)
})

const levelType = (level: string): 'success' | 'warning' =>
  level === '审核级' ? 'warning' : 'success'

function onCamera(): void {
  ElMessage.info('拍照 OCR 识别开发中，请先按本实验室参考范围手动录入异常值')
}
</script>

<template>
  <div class="page">
    <!-- ===== 顶部品牌区 ===== -->
    <header class="brand">
      <div class="brand-icon"><el-icon :size="30"><FirstAidKit /></el-icon></div>
      <div class="brand-text">
        <h1>PCI 术后用药管理助手</h1>
        <p>基于分级诊疗指南的规则引擎 · 零自由发挥 · 每一条建议可溯源</p>
      </div>
      <span class="brand-tag">基层辅助决策</span>
    </header>

    <!-- ===== 视图切换 Tab ===== -->
    <div class="view-tabs">
      <button :class="['view-tab', { on: view === 'form' }]" @click="view = 'form'">智能用药方案</button>
      <button :class="['view-tab', { on: view === 'chat' }]" @click="view = 'chat'">AI 用药问答</button>
    </div>

    <ChatView v-if="view === 'chat'" />

    <template v-else>
    <template v-if="!result && !errorMsg">
      <el-card class="panel" shadow="never">
        <el-steps :active="currentStep" finish-status="success" align-center class="steps">
          <el-step v-for="(s, i) in steps" :key="i" :title="s.title" :description="s.desc" />
        </el-steps>
      </el-card>

      <el-card class="panel form-panel" shadow="never">
        <div class="form-head">
          <span class="form-badge">{{ currentStep + 1 }}</span>
          <div>
            <h2>{{ steps[currentStep].title }}</h2>
            <p>{{ steps[currentStep].desc }}</p>
          </div>
        </div>

        <!-- ===== 界面 1 / 2 / 5：通用字段循环 ===== -->
        <template v-if="currentStep === 0 || currentStep === 1 || currentStep === 4">
          <el-form label-width="170px" label-position="left" class="form">
            <el-form-item v-for="f in currentFields" :key="f.key" v-show="!(f.dependsOn && form[f.dependsOn] !== true)">
              <template #label>
                <span class="field-label" :class="{ 'label-danger': f.dangerOptions && f.dangerOptions.length }">
                  <span v-if="f.required" class="req">*</span>{{ f.label }}
                </span>
              </template>
              <div class="field-wrap">
                <el-switch v-if="f.type === 'boolean'" v-model="form[f.key]" active-text="是" inactive-text="否" />
                <el-input-number v-else-if="f.type === 'number'" v-model="form[f.key]" :min="f.min" :max="f.max" :placeholder="f.placeholder" controls-position="right" class="ctrl">
                  <template #suffix v-if="f.unit">{{ f.unit }}</template>
                </el-input-number>
                <el-date-picker v-else-if="f.type === 'date'" v-model="form[f.key]" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" class="ctrl" />
                <div v-else-if="f.type === 'select'" class="option-group">
                  <label v-for="op in f.options" :key="op" class="opt">
                    <input type="radio" :name="f.key" :value="op" v-model="form[f.key]" />
                    <span>{{ op }}</span>
                  </label>
                </div>
                <div v-else-if="f.type === 'multi'" class="option-group">
                  <label v-for="op in f.options" :key="op" class="opt" :class="{ danger: f.dangerOptions && f.dangerOptions.includes(op) }">
                    <input type="checkbox" :value="op" v-model="form[f.key]" />
                    <span>{{ op }}</span>
                  </label>
                </div>
                <el-input v-else v-model="form[f.key]" :placeholder="f.placeholder || '选填'" class="ctrl-text" />
                <p v-if="f.note" class="field-note">{{ f.note }}</p>
              </div>
            </el-form-item>
          </el-form>
        </template>

        <!-- ===== 界面 3：辅助检查状态化卡片 ===== -->
        <div v-else-if="currentStep === 2">
          <div class="section-tip">
            <el-icon :size="15"><Camera /></el-icon>
            辅助检查异常判定：请按「本实验室参考范围」判断升高/正常/降低。第一期支持手动录入，拍照 OCR 识别开发中，失败可回落手动，不阻塞主流程。
          </div>
          <div class="exam-grid">
            <div v-for="c in examCards" :key="c.name" class="exam-card">
              <div class="exam-head">
                <div class="exam-title">{{ c.name }}<span class="exam-items">{{ c.items }}</span></div>
                <el-button size="small" text type="primary" @click="onCamera"><el-icon :size="14"><Camera /></el-icon>拍照识别</el-button>
              </div>
              <div class="exam-body">
                <div v-for="f in c.fields" :key="f.key" class="exam-field">
                  <span class="exam-label">{{ f.label }}</span>
                  <el-switch v-if="f.type === 'bool'" v-model="form[f.key]" />
                  <div v-else-if="f.type === 'status'" class="option-group">
                    <label v-for="op in f.options" :key="op" class="opt opt-sm">
                      <input type="radio" :name="f.key" :value="op" v-model="form[f.key]" />
                      <span>{{ op }}</span>
                    </label>
                  </div>
                  <el-input-number v-else v-model="form[f.key]" :min="0" controls-position="right" class="ctrl-sm">
                    <template #suffix v-if="f.unit">{{ f.unit }}</template>
                  </el-input-number>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ===== 界面 4：用药分组 ===== -->
        <div v-else-if="currentStep === 3">
          <div class="ap-block">
            <h3 class="ap-title">抗血小板药 · 出院时 vs 现在</h3>
            <p class="ap-sub">出院时剂量留空表示未使用；系统自动对比出院方案与当前用药，识别擅自降级/停药。</p>
            <el-table :data="antiplatelets" class="ap-table" :show-header="true">
              <el-table-column label="药物" width="190">
                <template #default="{ row }">
                  <div class="ap-name">{{ row.label }}</div>
                  <div class="ap-std">{{ row.std }}</div>
                </template>
              </el-table-column>
              <el-table-column label="出院时剂量（mg）">
                <template #default="{ row }">
                  <el-input-number v-model="row.discharge" :min="0" controls-position="right" placeholder="未用" />
                </template>
              </el-table-column>
              <el-table-column label="现在剂量（mg）">
                <template #default="{ row }">
                  <el-input-number v-model="row.now" :min="0" controls-position="right" placeholder="未用" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-collapse v-model="openGroups" class="med-collapse">
            <el-collapse-item v-for="g in medSingleGroups" :key="g.key" :name="g.key">
              <template #title>
                <span class="med-name">{{ g.name }}</span>
                <span class="med-desc">{{ g.desc }}</span>
              </template>
              <div class="med-body">
                <div class="option-group">
                  <label v-for="op in g.options" :key="op" class="opt">
                    <input type="radio" :name="g.key" :value="op" v-model="form[g.key]" />
                    <span>{{ op }}</span>
                  </label>
                </div>
                <p v-if="g.note" class="field-note">{{ g.note }}</p>
              </div>
            </el-collapse-item>
            <el-collapse-item v-for="g in medMultiGroups" :key="g.key" :name="g.key">
              <template #title>
                <span class="med-name">{{ g.name }}</span>
                <span class="med-desc">{{ g.desc }}</span>
              </template>
              <div class="med-body">
                <div class="option-group">
                  <label v-for="op in g.options" :key="op" class="opt">
                    <input type="checkbox" :value="op" v-model="form[g.key]" />
                    <span>{{ op }}</span>
                  </label>
                </div>
                <template v-if="g.key === 'others' && (form.others || []).includes('其他（填药名）')">
                  <el-input v-model="form.other_med_name" placeholder="请填写未列出的药品名称，多个用顿号分隔（如：α阻滞剂、其他降压药等）" clearable />
                </template>
                <template v-if="g.key === 'lipid'">
                  <div class="med-subtitle">当前降脂治疗阶段</div>
                  <div class="option-group">
                    <label v-for="ph in lipidPhases" :key="ph.key" class="opt">
                      <input type="radio" name="lipid_phase" :value="ph.key" v-model="form.lipid_phase" />
                      <span>{{ ph.label }}</span>
                    </label>
                  </div>
                </template>
              </div>
            </el-collapse-item>
          </el-collapse>

          <div class="med-special">
            <h4 class="med-subtitle">用药特殊情况（耐受性 / 禁忌 / 抵抗 / 抗栓强度）</h4>
            <el-form label-width="220px" label-position="left" class="form">
              <el-form-item v-for="f in medSpecialFields" :key="f.key">
                <template #label><span class="field-label">{{ f.label }}</span></template>
                <div class="field-wrap">
                  <el-switch v-if="f.type === 'boolean'" v-model="form[f.key]" active-text="是" inactive-text="否" />
                  <el-input-number v-else v-model="form[f.key]" :min="f.min" :max="f.max" controls-position="right" class="ctrl">
                    <template #suffix v-if="f.unit">{{ f.unit }}</template>
                  </el-input-number>
                  <p v-if="f.note" class="field-note">{{ f.note }}</p>
                </div>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div class="nav">
          <el-button v-if="currentStep > 0" size="large" @click="currentStep--">上一步</el-button>
          <el-button v-if="currentStep < steps.length - 1" type="primary" size="large" @click="currentStep++">下一步</el-button>
          <el-button v-else type="primary" size="large" :loading="loading" @click="submit">
            <el-icon class="btn-icon"><Document /></el-icon>提交分析
          </el-button>
        </div>
        <p class="hint"><span class="req">*</span> 为核心字段，其余按实际可获取情况选填</p>
      </el-card>
    </template>

    <!-- ===== 错误提示 ===== -->
    <template v-else-if="errorMsg">
      <el-card class="panel" shadow="never">
        <el-alert :title="errorMsg" type="error" show-icon :closable="false" />
        <div class="nav"><el-button type="primary" size="large" @click="reset">返回重填</el-button></div>
      </el-card>
    </template>

    <!-- ===== 分析结果 ===== -->
    <template v-else>
      <el-card class="panel result-panel" shadow="never">
        <div class="result-head">
          <h2>分析结果</h2>
          <div class="tags" v-if="activeTags.length">
            <span v-for="t in activeTags" :key="t" class="tag-chip">{{ t }}</span>
          </div>
        </div>

        <div v-if="result.redlines && result.redlines.length" class="redline-list">
          <div v-for="r in result.redlines" :key="r.id" class="redline-item">
            <div class="redline-head">
              <el-icon :size="20" color="#dc2626"><WarningFilled /></el-icon>
              <span class="redline-title">【红线 {{ r.id }}】{{ r.name }}</span>
            </div>
            <p class="redline-action">{{ r.action }}</p>
          </div>
        </div>

        <div v-else class="advice-list">
          <template v-if="result.advices && result.advices.length">
            <div class="advice-item" v-for="a in result.advices" :key="a.id">
              <div class="advice-head">
                <span class="advice-id">{{ a.id }}</span>
                <el-tag :type="levelType(a.level)" size="small" effect="light">{{ a.level }}</el-tag>
              </div>
              <p class="advice-text">{{ a.action }}</p>
              <p class="advice-src"><el-icon :size="13"><Document /></el-icon> 出处 {{ a.source }}</p>
            </div>
          </template>
          <el-empty v-else description="未命中任何规则，请核对录入信息" />
        </div>

        <p class="disclaimer"><el-icon :size="14"><InfoFilled /></el-icon> {{ result.disclaimer }}</p>
        <div class="nav">
          <el-button type="primary" size="large" @click="reset">
            <el-icon class="btn-icon"><RefreshLeft /></el-icon>重新填写
          </el-button>
        </div>
      </el-card>
    </template>
    </template>
  </div>
</template>

<style>
:root {
  --primary: #0369a1;
  --primary-dark: #075985;
  --primary-50: #f0f7fb;
  --danger: #dc2626;
  --danger-bg: #fef2f2;
  --success: #16a34a;
  --warning: #d97706;
  --bg: #f6f8fa;
  --card: #ffffff;
  --text: #0f172a;
  --text-2: #475569;
  --text-3: #94a3b8;
  --border: #e2e8f0;
}

body { margin: 0; background: var(--bg); font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif; }
* { box-sizing: border-box; }

.page { max-width: 960px; margin: 0 auto; padding: 28px 18px 70px; }

/* ===== 品牌区 ===== */
.brand { display: flex; align-items: center; gap: 16px; margin-bottom: 22px; }
.brand-icon {
  width: 56px; height: 56px; border-radius: 14px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: #fff; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(3, 105, 161, 0.25);
}
.brand-text h1 { margin: 0 0 6px; font-size: 24px; color: var(--text); letter-spacing: 0.5px; }
.brand-text p { margin: 0; color: var(--text-2); font-size: 13.5px; }
.brand-tag {
  margin-left: auto; flex-shrink: 0; font-size: 12px; padding: 5px 12px; border-radius: 20px;
  background: rgba(3, 105, 161, 0.08); color: var(--primary); border: 1px solid rgba(3, 105, 161, 0.2);
}

/* ===== 视图切换 Tab ===== */
.view-tabs { display: flex; gap: 8px; margin-bottom: 18px; background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 5px; }
.view-tab { flex: 1; padding: 10px 0; border: none; background: transparent; border-radius: 9px; font-size: 14.5px; color: var(--text-2); cursor: pointer; font-weight: 500; transition: all 0.2s; font-family: inherit; }
.view-tab.on { background: var(--primary); color: #fff; box-shadow: 0 2px 6px rgba(3, 105, 161, 0.25); }

/* ===== 卡片面板 ===== */
.panel { border: 1px solid var(--border); border-radius: 14px; margin-bottom: 18px; }
.panel :deep(.el-card__body) { padding: 22px 26px; }
.steps { padding: 4px 0 2px; }
.steps :deep(.el-step__title.is-process) { color: var(--primary); font-weight: 600; }
.steps :deep(.el-step__head.is-process) { color: var(--primary); border-color: var(--primary); }

/* ===== 表单区 ===== */
.form-head { display: flex; align-items: center; gap: 14px; padding-bottom: 16px; margin-bottom: 18px; border-bottom: 1px solid var(--border); }
.form-badge {
  width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
  background: var(--primary); color: #fff; font-size: 18px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.form-head h2 { margin: 0 0 3px; font-size: 19px; color: var(--text); }
.form-head p { margin: 0; font-size: 13px; color: var(--text-3); }

.field-label { color: var(--text-2); font-weight: 500; }
.field-label.label-danger { color: var(--danger); font-weight: 600; }
.req { color: var(--danger); margin-right: 3px; }
.field-wrap { width: 100%; }
.ctrl { width: 240px; }
.ctrl-text { width: 380px; }

/* 胶囊选择按钮 */
.option-group { display: flex; flex-wrap: wrap; gap: 9px; }
.opt { position: relative; }
.opt input { position: absolute; opacity: 0; pointer-events: none; }
.opt span {
  display: inline-block; padding: 8px 17px; border: 1px solid var(--border);
  border-radius: 9px; font-size: 13.5px; color: var(--text-2); cursor: pointer;
  background: #fff; transition: all 0.15s; user-select: none; line-height: 1.5;
}
.opt:hover span { border-color: var(--primary); }
.opt input:checked + span { background: var(--primary-50); border-color: var(--primary); color: var(--primary); font-weight: 600; }
.opt input:checked + span::after { content: ' ✓'; }
.opt input:focus-visible + span { outline: 2px solid var(--primary); outline-offset: 2px; }
/* 红色胶囊（出血征象严重项） */
.opt.danger span { color: var(--danger); border-color: #fecaca; }
.opt.danger input:checked + span { background: var(--danger-bg); border-color: var(--danger); color: var(--danger); font-weight: 600; }
.opt-sm span { padding: 5px 12px; font-size: 12.5px; }

.field-note { margin: 6px 0 0; color: var(--text-3); font-size: 12.5px; line-height: 1.5; }
.form :deep(.el-form-item) { margin-bottom: 20px; }

/* 界面 3 · 拍照提示条 */
.section-tip {
  display: flex; align-items: center; gap: 8px; padding: 11px 15px; margin-bottom: 18px;
  background: rgba(3, 105, 161, 0.06); color: var(--primary); border: 1px solid rgba(3, 105, 161, 0.18);
  border-radius: 9px; font-size: 13px; line-height: 1.6;
}

/* 界面 3 · 检查卡片 */
.exam-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.exam-card { border: 1px solid var(--border); border-radius: 11px; padding: 14px 15px; background: #fff; }
.exam-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding-bottom: 10px; margin-bottom: 10px; border-bottom: 1px dashed var(--border); }
.exam-title { font-size: 15px; font-weight: 600; color: var(--text); }
.exam-items { display: block; font-size: 12px; color: var(--text-3); font-weight: 400; margin-top: 2px; }
.exam-body { display: flex; flex-direction: column; gap: 10px; }
.exam-field { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.exam-field .option-group { justify-content: flex-end; }
.exam-label { font-size: 13px; color: var(--text-2); flex-shrink: 0; }
.ctrl-sm { width: 150px; }

/* 界面 4 · 抗血小板表 */
.ap-block { margin-bottom: 22px; }
.ap-title { margin: 0 0 6px; font-size: 15.5px; color: var(--text); }
.ap-sub { margin: 0 0 12px; font-size: 12.5px; color: var(--text-3); }
.ap-table { margin-bottom: 20px; }
.ap-table :deep(.el-input-number) { width: 140px; }
.ap-name { font-weight: 600; color: var(--text); }
.ap-std { font-size: 12px; color: var(--text-3); margin-top: 2px; }

/* 界面 4 · 用药折叠 */
.med-collapse { border: 1px solid var(--border); border-radius: 11px; }
.med-collapse :deep(.el-collapse-item__header) { padding: 0 16px; height: auto; min-height: 52px; }
.med-collapse :deep(.el-collapse-item__content) { padding-bottom: 14px; }
.med-name { font-size: 15px; font-weight: 600; color: var(--text); margin-right: 12px; }
.med-desc { font-size: 12.5px; color: var(--text-3); }
.med-body { padding: 4px 16px 0; }
.med-subtitle { font-size: 13px; color: var(--text-2); font-weight: 500; margin: 14px 0 8px; }

.nav { display: flex; justify-content: center; gap: 14px; margin-top: 26px; }
.btn-icon { margin-right: 5px; vertical-align: -2px; }
.hint { text-align: center; color: var(--text-3); font-size: 12.5px; margin: 16px 0 0; }

/* ===== 结果区 ===== */
.result-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding-bottom: 14px; margin-bottom: 18px; border-bottom: 1px solid var(--border); }
.result-head h2 { margin: 0; font-size: 20px; color: var(--text); }
.tag-chip { font-size: 12px; padding: 4px 12px; border-radius: 16px; margin-left: 8px; background: rgba(217, 119, 6, 0.1); color: var(--warning); border: 1px solid rgba(217, 119, 6, 0.25); }

.redline-item { background: var(--danger-bg); border: 1px solid #fecaca; border-left: 4px solid var(--danger); border-radius: 10px; padding: 15px 18px; margin-bottom: 14px; }
.redline-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.redline-title { font-weight: 700; color: var(--danger); font-size: 15.5px; }
.redline-action { margin: 0; color: #7f1d1d; line-height: 1.7; font-size: 14.5px; }

.advice-item { background: var(--card); border: 1px solid var(--border); border-left: 4px solid var(--primary); border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; transition: box-shadow 0.2s; }
.advice-item:hover { box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06); }
.advice-head { display: flex; align-items: center; gap: 9px; margin-bottom: 8px; }
.advice-id { font-weight: 700; color: var(--primary); font-size: 14.5px; }
.advice-text { margin: 0 0 8px; color: var(--text); line-height: 1.7; font-size: 14.5px; }
.advice-src { margin: 0; color: var(--text-3); font-size: 12.5px; display: flex; align-items: center; gap: 4px; }

.disclaimer { display: flex; align-items: center; justify-content: center; gap: 5px; color: var(--text-3); font-size: 12.5px; margin: 24px 0 6px; }

@media (max-width: 640px) {
  .brand-tag { display: none; }
  .form :deep(.el-form-item__label) { width: 100% !important; text-align: left; }
  .ctrl, .ctrl-text { width: 100%; }
  .exam-grid { grid-template-columns: 1fr; }
  .med-desc { display: none; }
}
</style>