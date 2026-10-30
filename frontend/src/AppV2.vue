<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  RefreshLeft,
  FirstAidKit,
  Camera,
  Printer,
  Download,
} from '@element-plus/icons-vue'
import ChatView from './ChatView.vue'
import OcrDialog from './components/OcrDialog.vue'
import AnalysisReport from './components/AnalysisReport.vue'

interface CriticalValue { id: string; name: string; action: string }
interface Redline { id: string; name: string; action: string }
interface Advice { id: string; level: string; source: string; action: string }
interface AnalyzeResult {
  tags: Record<string, boolean>
  critical?: CriticalValue[]
  redlines: Redline[]
  advices: Advice[]
  disclaimer?: string
  report?: any
}

type ExamKind = 'number' | 'status' | 'bool' | 'text' | 'pair'
interface ExamField {
  key: string
  secondKey?: string
  label: string
  kind: ExamKind
  options?: string[]
  unit?: string
  placeholder?: string
  default?: any
}
interface ExamCard { key: string; name: string; hint?: string; fields: ExamField[] }

interface ComorbField {
  key: string
  label: string
  kind: 'select' | 'number' | 'text' | 'date'
  options?: string[]
  unit?: string
  placeholder?: string
  shared?: boolean
}
interface ComorbItem { key: string; label: string; hint?: string; sub?: ComorbField[] }

interface Drug { key: string; name: string; std?: string; stdValue?: number; stdFrequency?: string }
interface MedCategory { key: string; label: string; note?: string; custom?: boolean; drugs: Drug[] }
interface CustomMed { id: number; name: string; discharge: number | null; dischargeFrequency: string; now: number | null; nowFrequency: string }
interface AdherenceEntry { id: number; drug: string; days: number | null }

const DIAGNOSES = [
  { label: '急性 ST 段抬高型心肌梗死', scenario: 'ACS' },
  { label: '急性非 ST 段抬高型心肌梗死', scenario: 'ACS' },
  { label: '不稳定型心绞痛', scenario: 'ACS' },
  { label: '稳定型心绞痛', scenario: 'CCS' },
  { label: '缺血性心肌病', scenario: 'CCS' },
]
const VESSELS = [
  { key: 'left_main', label: '左主干', backend: '左主干' },
  { key: 'lad', label: '左前降支', backend: '前降支' },
  { key: 'lcx', label: '回旋支', backend: '回旋支' },
  { key: 'rca', label: '右冠', backend: '右冠' },
]
const VESSEL_NUM: Record<string, number> = { 单支: 1, 双支: 2, 三支: 3 }

const COMORB: ComorbItem[] = [
  {
    key: 'hypertension', label: '高血压',
    sub: [
      { key: 'hypertension_grade', label: '分级', kind: 'select', options: ['1级', '2级', '3级', '单纯收缩期高血压'] },
      { key: 'current_sbp', label: '目前收缩压', kind: 'number', unit: 'mmHg' },
      { key: 'current_dbp', label: '目前舒张压', kind: 'number', unit: 'mmHg' },
      { key: 'bp_high', label: '规范服药下血压仍 ≥140/90', kind: 'select', options: ['否', '是'] },
    ],
  },
  { key: 'af', label: '心房颤动' },
  {
    key: 'hf', label: '心力衰竭',
    sub: [{ key: 'lvef', label: '患者 EF 值', kind: 'number', unit: '%', shared: true }],
  },
  {
    key: 'diabetes', label: '糖尿病',
    sub: [
      { key: 'dm_fpg', label: '空腹血糖', kind: 'number', unit: 'mmol/L' },
      { key: 'dm_hba1c', label: '糖化血红蛋白', kind: 'number', unit: '%' },
    ],
  },
  {
    key: 'dyslipidemia', label: '高脂血症',
    sub: [{
      key: 'lipid_goal', label: '当前降脂方案达标情况', kind: 'select',
      options: ['未服药', '达标', '未达标'],
    }],
  },
  { key: 'copd', label: 'COPD' },
  { key: 'asthma', label: '哮喘' },
  {
    key: 'liver', label: '肝功能异常',
    sub: [{ key: 'liver_degree', label: '程度', kind: 'select', options: ['轻度', '中度', '重度'] }],
  },
  {
    key: 'ckd', label: '慢性肾脏病',
    sub: [{ key: 'ckd_stage', label: '分期', kind: 'select', options: ['1期', '2期', '3期', '4期', '5期'] }],
  },
  { key: 'prior_mi', label: '既往心肌梗死', sub: [{ key: 'prior_mi_date', label: '发生日期', kind: 'date', placeholder: '选择日期' }] },
  { key: 'prior_stroke', label: '既往脑梗死', sub: [{ key: 'prior_stroke_date', label: '发生日期', kind: 'date', placeholder: '选择日期' }] },
  { key: 'ich', label: '颅内出血史' },
  { key: 'ulcer', label: '消化道溃疡 / 出血史' },
]

const EXAM_CARDS: ExamCard[] = [
  {
    key: 'cbc', name: '血常规',
    fields: [
      { key: 'hb', label: '血红蛋白', kind: 'number', unit: 'g/L', placeholder: '数值' },
      { key: 'hb_prev', label: '24 小时前血红蛋白', kind: 'number', unit: 'g/L', placeholder: '选填' },
      { key: 'plt', label: '血小板', kind: 'number', unit: '×10^9/L', placeholder: '数值' },
      { key: 'wbc', label: '白细胞', kind: 'number', unit: '×10^9/L', placeholder: '数值' },
    ],
  },
  {
    key: 'urine', name: '尿常规',
    fields: [
      { key: 'urine_protein', label: '蛋白阳性', kind: 'bool', default: false },
      { key: 'brown_urine', label: '潜血 / 褐色尿', kind: 'bool', default: false },
    ],
  },
  {
    key: 'liver', name: '肝功能',
    fields: [
      { key: 'alt', secondKey: 'ast', label: 'ALT / AST', kind: 'pair', unit: 'U/L', placeholder: '数值' },
      { key: 'bilirubin', label: '胆红素', kind: 'number', unit: 'μmol/L', placeholder: '数值' },
      { key: 'albumin', label: '白蛋白', kind: 'number', unit: 'g/L', placeholder: '数值' },
    ],
  },
  {
    key: 'renal', name: '肾功能',
    fields: [
      { key: 'scr', label: '血肌酐（Scr）', kind: 'number', unit: 'μmol/L', placeholder: '数值' },
      { key: 'egfr', label: 'eGFR', kind: 'number', unit: 'ml/min/1.73m²', placeholder: '数值' },
    ],
  },
  {
    key: 'coag', name: '凝血功能',
    fields: [
      { key: 'pt', label: '凝血酶原时间（PT）', kind: 'number', unit: 's', placeholder: '数值' },
      { key: 'aptt', label: '活化部分凝血活酶时间（APTT）', kind: 'number', unit: 's', placeholder: '数值' },
      { key: 'tt', label: '凝血酶时间（TT）', kind: 'number', unit: 's', placeholder: '数值' },
      { key: 'fibrinogen', label: '纤维蛋白原', kind: 'number', unit: 'g/L', placeholder: '数值' },
      { key: 'inr', label: '国际标准化比值（INR）', kind: 'number', unit: '', placeholder: '数值' },
      { key: 'd_dimer', label: 'D-二聚体', kind: 'number', unit: 'mg/L', placeholder: '数值' },
    ],
  },
  {
    key: 'enzyme', name: '心肌酶谱',
    fields: [{ key: 'ck_mb', label: 'CK-MB', kind: 'number', unit: 'U/L', placeholder: '数值' }],
  },
  {
    key: 'troponin', name: '肌钙蛋白',
    fields: [{ key: 'troponin_value', label: '肌钙蛋白（cTnI / cTnT）', kind: 'number', unit: 'ng/mL', placeholder: '数值' }],
  },
  {
    key: 'potassium', name: '电解质',
    fields: [{ key: 'potassium', label: '血钾（K⁺）', kind: 'number', unit: 'mmol/L', placeholder: '数值' }],
  },
  {
    key: 'lipid', name: '血脂',
    fields: [
      { key: 'ldl', label: '基线低密度脂蛋白胆固醇（LDL-C）', kind: 'number', unit: 'mmol/L', placeholder: '基线值' },
      { key: 'current_ldl', label: '本次低密度脂蛋白胆固醇（LDL-C）', kind: 'number', unit: 'mmol/L', placeholder: '本次值' },
      { key: 'tc', label: '总胆固醇（TC）', kind: 'number', unit: 'mmol/L', placeholder: '数值' },
      { key: 'tg', label: '甘油三酯（TG）', kind: 'number', unit: 'mmol/L', placeholder: '数值' },
      { key: 'hdl', label: '高密度脂蛋白胆固醇（HDL-C）', kind: 'number', unit: 'mmol/L', placeholder: '数值' },
    ],
  },
  {
    key: 'glucose', name: '空腹血糖和糖化血红蛋白',
    fields: [
      { key: 'fpg', label: '空腹血糖（FPG）', kind: 'number', unit: 'mmol/L', placeholder: '数值' },
      { key: 'hba1c', label: '糖化血红蛋白（HbA1c）', kind: 'number', unit: '%', placeholder: '数值' },
    ],
  },
  {
    key: 'bnp', name: 'B型前脑尿钠肽',
    fields: [{ key: 'bnp', label: 'B型前脑尿钠肽', kind: 'number', unit: 'pg/mL', placeholder: '数值' }],
  },
  {
    key: 'ecg', name: '十二导联心电图',
    fields: [
      { key: 'heart_rate', label: '心率', kind: 'number', unit: '次/分', placeholder: '数值' },
      { key: 'arrhythmia_type', label: '心律失常', kind: 'text', placeholder: '填写心律失常类型' },
      { key: 'pr_interval', label: 'PR 间期', kind: 'number', unit: 'ms', placeholder: '数值' },
      { key: 'qrs_duration', label: 'QRS 波', kind: 'number', unit: 'ms', placeholder: '数值' },
      { key: 'st_t', label: 'ST-T 改变', kind: 'bool', default: false },
    ],
  },
  {
    key: 'echo', name: '超声心动图',
    fields: [
      { key: 'lvef', label: '射血分数（EF）', kind: 'number', unit: '%', placeholder: '数值' },
      { key: 'wall_aneurysm', label: '室壁瘤', kind: 'bool', default: false },
      { key: 'wall_motion', label: '室壁运动障碍', kind: 'bool', default: false },
      { key: 'echo_other', label: '其他显著异常', kind: 'text', placeholder: '选填' },
    ],
  },
]

const FREQUENCIES = ['qd', 'bid', 'tid', 'qid', 'qod', 'qw', 'biw', 'tiw', 'qow', '2w', '3w', '4w', 'q1/2h', 'qh', 'q2h', 'q3h', 'q4h', 'q6h', 'q8h', 'q12h']
const CUSTOM_CATEGORIES = new Set(['anticoagulant', 'lipid', 'glucose', 'ppi', 'other'])
const MED_CATEGORIES: MedCategory[] = [
  {
    key: 'antiplatelet', label: '抗血小板药物',
    drugs: [
      { key: 'aspirin', name: '阿司匹林', std: '100 mg qd', stdValue: 100, stdFrequency: 'qd' },
      { key: 'indobufen', name: '吲哚布芬', std: '100 mg bid', stdValue: 100, stdFrequency: 'bid' },
      { key: 'clopidogrel', name: '氯吡格雷', std: '75 mg qd', stdValue: 75, stdFrequency: 'qd' },
      { key: 'ticagrelor', name: '替格瑞洛', std: '90 mg bid', stdValue: 90, stdFrequency: 'bid' },
    ],
  },
  {
    key: 'anticoagulant', label: '口服抗凝药', custom: true,
    drugs: [
      { key: 'rivaroxaban', name: '利伐沙班' },
      { key: 'warfarin', name: '华法林' },
    ],
  },
  {
    key: 'beta', label: 'β 受体阻滞剂',
    drugs: [
      { key: 'metoprolol', name: '美托洛尔' },
      { key: 'bisoprolol', name: '比索洛尔' },
      { key: 'carvedilol', name: '卡维地洛' },
    ],
  },
  {
    key: 'raas', label: '肾素-血管紧张素系统抑制剂（ARNI / ACEI / ARB）',
    drugs: [
      { key: 'sacubitril_valsartan', name: '沙库巴曲缬沙坦' },
      { key: 'perindopril', name: '培哚普利' },
      { key: 'enalapril', name: '依那普利' },
      { key: 'benazepril', name: '贝那普利' },
      { key: 'fosinopril', name: '福辛普利' },
      { key: 'valsartan', name: '缬沙坦' },
      { key: 'losartan', name: '氯沙坦' },
      { key: 'irbesartan', name: '厄贝沙坦' },
      { key: 'telmisartan', name: '替米沙坦' },
      { key: 'candesartan', name: '坎地沙坦' },
    ],
  },
  {
    key: 'lipid', label: '降脂药物', custom: true,
    drugs: [
      { key: 'atorvastatin', name: '阿托伐他汀' },
      { key: 'rosuvastatin', name: '瑞舒伐他汀' },
      { key: 'ezetimibe', name: '依折麦布' },
      { key: 'fenofibrate', name: '非诺贝特' },
      { key: 'evolocumab', name: '依洛尤单抗' },
      { key: 'tafolecimab', name: '托莱西单抗' },
      { key: 'inclisiran', name: '英克司兰' },
    ],
  },
  {
    key: 'glucose', label: '降糖药物', custom: true,
    drugs: [
      { key: 'metformin', name: '二甲双胍' },
      { key: 'acarbose', name: '阿卡波糖' },
      { key: 'dapagliflozin', name: '达格列净' },
      { key: 'empagliflozin', name: '恩格列净' },
      { key: 'glimepiride', name: '格列美脲' },
      { key: 'sitagliptin', name: '西格列汀' },
      { key: 'alogliptin', name: '阿格列汀' },
      { key: 'insulin_glargine', name: '甘精胰岛素' },
      { key: 'insulin_aspart', name: '门冬胰岛素' },
      { key: 'insulin_degludec', name: '德谷胰岛素' },
      { key: 'semaglutide', name: '司美格鲁肽' },
    ],
  },
  {
    key: 'diuretic', label: '利尿剂',
    drugs: [
      { key: 'furosemide', name: '呋塞米' },
      { key: 'spironolactone', name: '螺内酯' },
    ],
  },
  {
    key: 'ppi', label: '质子泵抑制剂（PPI）', custom: true,
    drugs: [
      { key: 'rabeprazole', name: '雷贝拉唑' },
      { key: 'pantoprazole', name: '泮托拉唑' },
      { key: 'omeprazole', name: '奥美拉唑' },
    ],
  },
  {
    key: 'ccb', label: '钙通道阻滞剂（CCB）',
    drugs: [
      { key: 'amlodipine', name: '氨氯地平' },
      { key: 'nifedipine', name: '硝苯地平' },
      { key: 'levamlodipine', name: '左氨氯地平' },
      { key: 'felodipine', name: '非洛地平' },
      { key: 'diltiazem', name: '地尔硫䓬' },
    ],
  },
  {
    key: 'other', label: '其他药物', custom: true,
    drugs: [
      { key: 'isosorbide', name: '单硝酸异山梨酯' },
      { key: 'irbesartan_hctz', name: '厄贝沙坦氢氯噻嗪' },
      { key: 'nicorandil', name: '尼可地尔' },
      { key: 'ivabradine', name: '伊伐布雷定' },
      { key: 'vericiguat', name: '维立西呱' },
      { key: 'tolvaptan', name: '托伐普坦' },
      { key: 'colchicine', name: '秋水仙碱' },
      { key: 'mosapride', name: '莫沙必利' },
      { key: 'potassium_magnesium', name: '门冬氨酸钾镁' },
      { key: 'hydrotalcite', name: '铝镁加' },
      { key: 'xuezhikang', name: '血脂康胶囊' },
      { key: 'danshen', name: '复方丹参滴丸' },
      { key: 'shensong', name: '参松养心胶囊' },
      { key: 'xinsuning', name: '心速宁胶囊' },
      { key: 'qili', name: '芪苈强心胶囊' },
      { key: 'nuodikang', name: '诺迪康颗粒' },
      { key: 'niaoduqing', name: '尿毒清颗粒' },
      { key: 'bailing', name: '百令胶囊' },
      { key: 'polyene', name: '多烯磷脂酰胆碱片' },
      { key: 'levothyroxine', name: '左甲状腺素钠' },
    ],
  },
]

const DRUG_BY_KEY: Record<string, Drug> = {}
for (const cat of MED_CATEGORIES) for (const drug of cat.drugs) DRUG_BY_KEY[drug.key] = drug

const SPECIAL = [
  { key: 'aspirin_intolerant', label: '阿司匹林不耐受 / 禁忌' },
  { key: 'ticagrelor_intolerant', label: '替格瑞洛不耐受 / 禁忌' },
  { key: 'cyp2c19_loss', label: '氯吡格雷不耐受 / 禁忌' },
  { key: 'beta_blocker_contra', label: 'β 受体阻滞剂不耐受 / 禁忌' },
  { key: 'acei_contra', label: '血管紧张素转化酶抑制剂禁忌' },
]
const SYMPTOM_GROUPS = [
  { severity: 'red', title: '立即急诊', items: [
    { key: 'sym_chest', label: '持续胸痛', bleeding: false },
    { key: 'sym_cold_sweat', label: '恶心冷汗', bleeding: false },
    { key: 'sym_syncope', label: '黑矇晕厥', bleeding: false },
    { key: 'sym_consciousness', label: '意识改变', bleeding: false },
    { key: 'sym_seizure', label: '抽搐', bleeding: false },
    { key: 'bleed_hematemesis', label: '呕血', bleeding: true },
    { key: 'bleed_melena', label: '黑便', bleeding: true },
    { key: 'bleed_hematuria', label: '血尿', bleeding: true },
    { key: 'sym_headache', label: '头痛', bleeding: false },
    { key: 'sym_airway', label: '喉头水肿', bleeding: false },
  ] },
  { severity: 'yellow', title: '尽快转诊', items: [
    { key: 'sym_dyspnea', label: '胸闷气短加重', bleeding: false },
    { key: 'sym_edema', label: '下肢水肿', bleeding: false, adr: 'edema' },
    { key: 'sym_fatigue', label: '乏力', bleeding: false },
    { key: 'sym_dizzy', label: '头晕', bleeding: false },
    { key: 'sym_palpitation', label: '心悸', bleeding: false },
    { key: 'sym_dry_cough', label: '干咳', bleeding: false, adr: 'dry_cough' },
  ] },
  { severity: 'green', title: '基层随访', items: [
    { key: 'sym_reflux', label: '反酸恶心', bleeding: false },
    { key: 'bleed_bruise', label: '轻度瘀斑', bleeding: true },
    { key: 'bleed_gum', label: '牙龈出血', bleeding: true },
    { key: 'sym_palpitation_mild', label: '偶发心悸', bleeding: false },
    { key: 'sym_fatigue_mild', label: '轻度乏力', bleeding: false },
  ] },
]
const SYMPTOMS = SYMPTOM_GROUPS.flatMap((g) => g.items.map((s) => ({ ...s, severity: g.severity })))
const ADR = [
  { key: 'adr_bradycardia', label: '静息心动过缓' },
  { key: 'adr_rate_fast', label: '心率仍偏快' },
  { key: 'adr_angina', label: '抗缺血控制不佳' },
]
const STEPS = [
  { title: '基本信息' },
  { title: '合并症与既往史' },
  { title: '辅助检查' },
  { title: '用药' },
  { title: '症状与用药行为' },
]

const TERM_TIPS: Record<string, string> = {
  DAPT: '双联抗血小板治疗：阿司匹林/吲哚布芬 + 氯吡格雷/替格瑞洛的联合方案',
  'hs-cTnT': '高敏肌钙蛋白 T，心肌损伤标志物',
  室壁瘤: '心室壁局部变薄并向外膨出，常见于心肌梗死后',
  ARNI: '血管紧张素受体-脑啡肽酶抑制剂',
  ACEI: '血管紧张素转换酶抑制剂',
  ARB: '血管紧张素受体拮抗剂',
  PPI: '质子泵抑制剂，用于护胃 / 预防消化道出血',
  CCB: '钙通道阻滞剂',
  QTc: '按心率校正的 QT 间期',
  eGFR: '估算肾小球滤过率',
  'LDL-C': '低密度脂蛋白胆固醇',
  HbA1c: '糖化血红蛋白',
  BNP: 'B 型利钠肽，心功能标志物',
  INR: '国际标准化比值',
}

function termTip(label: string): string {
  for (const [key, value] of Object.entries(TERM_TIPS)) {
    if (label.includes(key)) return value
  }
  return ''
}

function labelMain(label: string): string {
  return label.split('（')[0]
}

function labelAbbr(label: string): string {
  const index = label.indexOf('（')
  return index >= 0 ? label.slice(index) : ''
}

function makeForm(): Record<string, any> {
  const f: Record<string, any> = {
    age: null, sex: '', emergency_pci: false, surgery_date: '', post_pci_months: null,
    diagnosis: '', vessels: '', discharge_plan: '', other_pmh: '', lvef: null,
    // OCR 依据参考范围产生的状态作为隐藏数据保留，无需重复手工选择。
    hb_low: false, plt_status: '正常', plt_drop_over_50pct: false,
    alt_ast_status: '正常', jaundice: false, crcl: null, coag_abnormal: false,
    ck: null, ck_status: '正常', troponin_elevated: false, potassium_status: '正常',
    lipid_abnormal: '', fbg_status: '正常', bnp_state: '正常', arrhythmia: false,
    hr_abnormal: false, qtc_prolonged: false, sinus_rhythm: false,
    qtc: null, qtc_baseline: null, sodium: null, hs_ctnt: null, co2cp: null,
    baseline_scr: null, calcium: null, troponin_reference_known: false,
    med_used: {}, med_sel: {}, med_discharge: {}, med_discharge_freq: {},
    med_now: {}, med_now_freq: {}, med_custom: {}, med_special: {},
    other_intolerance: false, other_intolerance_names: [''],
    temp_meds: '', adherence: [{ id: 1, drug: '', days: null } as AdherenceEntry],
    surgery_name: '', surgery_date_planned: '', referral_confirmed: false, recent_symptom: false,
  }
  for (const card of EXAM_CARDS) for (const field of card.fields) {
    const keys = field.kind === 'pair' ? [field.key, field.secondKey!] : [field.key]
    for (const key of keys) f[key] = field.kind === 'bool' ? false : field.kind === 'number' || field.kind === 'pair' ? null : ''
  }
  for (const item of COMORB) {
    f['c_' + item.key] = false
    for (const sub of item.sub ?? []) if (!sub.shared) f['c_' + sub.key] = sub.kind === 'number' ? null : ''
  }
  for (const v of VESSELS) {
    f['vessel_' + v.key] = false
    f['iv_' + v.key] = { dcb: 0, brs: 0, des: 0 }
  }
  for (const cat of MED_CATEGORIES) {
    f.med_used[cat.key] = false
    f.med_custom[cat.key] = [] as CustomMed[]
    for (const drug of cat.drugs) {
      f.med_sel[drug.key] = false
      f.med_discharge[drug.key] = null
      f.med_discharge_freq[drug.key] = drug.stdFrequency || 'qd'
      f.med_now[drug.key] = null
      f.med_now_freq[drug.key] = drug.stdFrequency || 'qd'
    }
  }
  for (const s of SPECIAL) f.med_special[s.key] = false
  for (const s of SYMPTOMS) f[s.key] = false
  for (const a of ADR) f[a.key] = false
  return f
}

const form = reactive<Record<string, any>>(makeForm())
const currentStep = ref(0)
const screen = ref<'form' | 'review' | 'result'>('form')
const view = ref<'form' | 'chat'>('form')
const loading = ref(false)
const result = ref<AnalyzeResult | null>(null)
const errorMsg = ref('')
const errors = ref<string[]>([])
const ocrVisible = ref(false)
const ocrHint = ref('')

const DRAFT_KEY = 'pci-med-draft-v4'
const LEGACY_DRAFT_KEY = 'pci-med-draft-v3'
let saveTimer: number | null = null
let restoring = false

const selectedVessels = computed(() => VESSELS.filter((v) => form['vessel_' + v.key]))
const selectedDrugs = computed(() => MED_CATEGORIES.flatMap((cat) => {
  if (!form.med_used[cat.key]) return []
  const regular = cat.drugs.filter((d) => form.med_sel[d.key]).map((d) => ({
    ...d, category: cat.label, discharge: form.med_discharge[d.key], now: form.med_now[d.key],
    dischargeFrequency: form.med_discharge_freq[d.key], nowFrequency: form.med_now_freq[d.key],
  }))
  const custom = (form.med_custom[cat.key] || []).filter((d: CustomMed) => d.name.trim()).map((d: CustomMed) => ({
    ...d, key: `custom-${d.id}`, category: cat.label,
  }))
  return [...regular, ...custom]
}))
const medChanges = computed(() => selectedDrugs.value.flatMap((d) => {
  const discharge = Number(d.discharge)
  const now = Number(d.now)
  if (discharge > 0 && (!now || now <= 0)) return [{ name: d.name, text: '出院时使用，现在未填 / 可能已停' }]
  if (discharge > 0 && now > 0 && now < discharge) return [{ name: d.name, text: `剂量下降：${discharge} → ${now} mg` }]
  return []
}))
const ocrCurrent = computed(() => ({ ...form, baseline_ldl: form.ldl }))
let nextEntryId = 100

function addCustomMed(cat: MedCategory): void {
  form.med_custom[cat.key].push({ id: nextEntryId++, name: '', discharge: null, dischargeFrequency: 'qd', now: null, nowFrequency: 'qd' })
}
function removeCustomMed(cat: MedCategory, id: number): void {
  form.med_custom[cat.key] = form.med_custom[cat.key].filter((d: CustomMed) => d.id !== id)
}
function addAdherence(): void {
  form.adherence.push({ id: nextEntryId++, drug: '', days: null })
}
function removeAdherence(id: number): void {
  if (form.adherence.length > 1) form.adherence = form.adherence.filter((d: AdherenceEntry) => d.id !== id)
}
function addIntoleranceName(): void { form.other_intolerance_names.push('') }
function removeIntoleranceName(index: number): void {
  if (form.other_intolerance_names.length > 1) form.other_intolerance_names.splice(index, 1)
}
function elapsedDate(value: string): string {
  if (!value) return ''
  const start = new Date(value)
  if (Number.isNaN(start.getTime()) || start > new Date()) return ''
  let months = (new Date().getFullYear() - start.getFullYear()) * 12 + new Date().getMonth() - start.getMonth()
  if (new Date().getDate() < start.getDate()) months--
  return months >= 12 ? `距今 ${Math.floor(months / 12)} 年${months % 12 ? ` ${months % 12} 个月` : ''}` : `距今 ${Math.max(0, months)} 个月`
}

function interventionTotal(key: string): number {
  const x = form['iv_' + key] ?? {}
  return (x.dcb || 0) + (x.brs || 0) + (x.des || 0)
}

function hasValue(v: any): boolean {
  return v !== null && v !== undefined && v !== '' && v !== false
}

function isExamDefault(field: ExamField): boolean {
  if (field.kind === 'pair') return !hasValue(form[field.key]) && !hasValue(form[field.secondKey!])
  if (field.kind === 'bool') return !form[field.key]
  if (field.kind === 'number') return form[field.key] === null || form[field.key] === ''
  if (field.kind === 'status') return form[field.key] === field.default
  return !form[field.key]
}

function filledCount(step: number): number {
  if (step === 0) {
    let n = 0
    for (const key of ['age', 'sex', 'surgery_date', 'diagnosis', 'vessels']) if (hasValue(form[key])) n++
    for (const v of VESSELS) if (form['vessel_' + v.key]) n++
    for (const key of ['emergency_pci', 'discharge_plan']) if (hasValue(form[key])) n++
    return n
  }
  if (step === 1) {
    let n = 0
    for (const item of COMORB) {
      if (!form['c_' + item.key]) continue
      n++
      for (const sub of item.sub ?? []) if (hasValue(sub.shared ? form[sub.key] : form['c_' + sub.key])) n++
    }
    if (hasValue(form.other_pmh)) n++
    return n
  }
  if (step === 2) {
    let n = 0
    for (const card of EXAM_CARDS) for (const field of card.fields) if (!isExamDefault(field)) n++
    return n
  }
  if (step === 3) {
    let n = selectedDrugs.value.length
    for (const s of SPECIAL) if (form.med_special[s.key]) n++
    if (form.other_intolerance) n++
    return n
  }
  let n = SYMPTOMS.filter((s) => form[s.key]).length + ADR.filter((a) => form[a.key]).length
  if (form.temp_meds) n++
  n += form.adherence.filter((a: AdherenceEntry) => a.drug.trim()).length
  if (form.surgery_name) n++
  return n
}

const summaryGroups = computed(() => [
  { step: 0, title: '基本信息', count: filledCount(0), desc: `${form.age || '—'} 岁 · ${form.sex || '—'} · ${form.diagnosis || '未填诊断'}` },
  { step: 1, title: '合并症与既往史', count: filledCount(1), desc: COMORB.filter((i) => form['c_' + i.key]).map((i) => i.label).join('、') || '未勾选合并症' },
  { step: 2, title: '辅助检查', count: filledCount(2), desc: `已填 ${filledCount(2)} 项异常 / 数值` },
  { step: 3, title: '用药', count: filledCount(3), desc: selectedDrugs.value.map((d) => d.name).join('、') || '未选择药物' },
  { step: 4, title: '症状与用药行为', count: filledCount(4), desc: SYMPTOMS.filter((s) => form[s.key]).map((s) => s.label).join('、') || '未勾选症状' },
])

watch(
  () => form.surgery_date,
  (d) => {
    if (!d) {
      form.post_pci_months = null
      return
    }
    const date = new Date(d as string)
    if (Number.isNaN(date.getTime())) return
    form.post_pci_months = Math.max(0, Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24 * 30)))
  },
)

function validateStep(step: number): boolean {
  const e: string[] = []
  if (step === 0) {
    if (form.age === null || form.age === '') e.push('年龄为核心必填')
    else if (Number(form.age) < 18) e.push('本页面用于成年患者，年龄不能小于 18 岁')
    if (!form.sex) e.push('性别为核心必填')
    if (!form.surgery_date) e.push('PCI 手术日期为核心必填')
    if (!form.diagnosis) e.push('出院诊断为核心必填')
    if (!form.vessels) e.push('病变支数为核心必填')
    if (!selectedVessels.value.length) e.push('请至少选择一条干预血管')
    else if (selectedVessels.value.length > (VESSEL_NUM[form.vessels] || 0)) e.push('干预血管数量不能超过所选病变支数')
    for (const v of selectedVessels.value) {
      if (interventionTotal(v.key) <= 0) e.push(`「${v.label}」请填写干预方式（药物洗脱支架 / 药物球囊 / 可吸收支架，至少一项 > 0）`)
    }
  }
  if (step === 1) {
    if (form.c_hypertension && !form.c_hypertension_grade) e.push('已勾选高血压，请选择高血压分级（条件必填）')
  }
  if (step === 3) {
    for (const cat of MED_CATEGORIES) for (const drug of form.med_custom[cat.key] || []) {
      if (Number(drug.discharge) > 0 && !drug.dischargeFrequency) e.push(`请为「${drug.name || '其他药物'}」选择出院频次`)
      if (Number(drug.now) > 0 && !drug.nowFrequency) e.push(`请为「${drug.name || '其他药物'}」选择当前频次`)
    }
    if (form.other_intolerance && !form.other_intolerance_names.some((n: string) => n.trim())) e.push('请填写至少一种不耐受 / 禁忌药物名称')
  }
  if (step === 4) {
    for (const entry of form.adherence) {
      if (entry.drug.trim() && (entry.days === null || Number(entry.days) < 0)) e.push(`请填写「${entry.drug}」停药 / 漏服天数`)
      if (!entry.drug.trim() && entry.days !== null) e.push('已填写停药天数，请补充具体药名')
    }
  }
  errors.value = e
  if (e.length) {
    ElMessage.warning(e[0])
    return false
  }
  return true
}

function validateAll(): boolean {
  for (const step of [0, 1, 3, 4]) {
    if (!validateStep(step)) {
      currentStep.value = step
      screen.value = 'form'
      return false
    }
  }
  errors.value = []
  return true
}

async function next(): Promise<void> {
  if (!validateStep(currentStep.value)) return
  if (currentStep.value < STEPS.length - 1) currentStep.value++
  else goReview()
  await nextTick()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function prev(): Promise<void> {
  if (currentStep.value > 0) currentStep.value--
  await nextTick()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function goReview(): void {
  if (!validateAll()) return
  screen.value = 'review'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function editStep(step: number): void {
  currentStep.value = step
  screen.value = 'form'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function onCategoryToggle(cat: MedCategory): void {
  if (form.med_used[cat.key]) return
  for (const drug of cat.drugs) {
    form.med_sel[drug.key] = false
    form.med_discharge[drug.key] = null
    form.med_now[drug.key] = null
    form.med_discharge_freq[drug.key] = drug.stdFrequency || 'qd'
    form.med_now_freq[drug.key] = drug.stdFrequency || 'qd'
  }
  form.med_custom[cat.key] = []
}

function fillStd(drug: Drug): void {
  if (!drug.stdValue) return
  form.med_now[drug.key] = drug.stdValue
  form.med_now_freq[drug.key] = drug.stdFrequency || 'qd'
}

function openOcr(card = ''): void {
  ocrHint.value = card
  ocrVisible.value = true
}

function applyOcr(payload: { patch: Record<string, any>; labels: string[] }): void {
  const patch = { ...payload.patch }
  if ('baseline_ldl' in patch) {
    form.ldl = patch.baseline_ldl
    delete patch.baseline_ldl
  }
  Object.assign(form, patch)
  const shown = payload.labels.slice(0, 6).join('、')
  const more = payload.labels.length > 6 ? ` 等 ${payload.labels.length} 项` : ''
  ElMessage.success(`已回填 ${payload.labels.length} 项：${shown}${more}`)
  ocrVisible.value = false
}

function buildPayload(): Record<string, any> {
  const p: Record<string, any> = { post_pci: true }
  const setIf = (key: string, value: any) => {
    if (value !== null && value !== undefined && value !== '') p[key] = value
  }

  setIf('age', form.age)
  setIf('sex', form.sex)
  if (form.emergency_pci) p.emergency_pci = true
  setIf('surgery_date', form.surgery_date)
  setIf('post_pci_months', form.post_pci_months)
  if (form.diagnosis) {
    p.discharge_diagnosis = form.diagnosis
    p.scenario = DIAGNOSES.find((d) => d.label === form.diagnosis)?.scenario ?? ''
  }
  if (form.vessels) {
    p.vessel_count = VESSEL_NUM[form.vessels]
    if (p.vessel_count >= 2) p.multivessel = true
  }
  const vessels = selectedVessels.value.filter((v) => interventionTotal(v.key) > 0)
  if (vessels.length) {
    p.target_vessel = vessels.map((v) => v.backend)
    p.dcb = vessels.some((v) => (form['iv_' + v.key].dcb || 0) > 0)
    let dcb = 0
    let brs = 0
    let des = 0
    const stents: string[] = []
    for (const v of vessels) {
      const x = form['iv_' + v.key]
      dcb += x.dcb || 0
      brs += x.brs || 0
      des += x.des || 0
      if (x.des) stents.push(`${v.label}药物洗脱支架×${x.des}`)
      if (x.brs) stents.push(`${v.label}可吸收支架×${x.brs}`)
    }
    if (dcb) p.dcb_count = dcb
    if (brs) p.brs_count = brs
    if (des) p.des_count = des
    if (stents.length) p.stent_type = stents.join('、')
  }
  setIf('discharge_plan', form.discharge_plan)
  if (form.c_hypertension) {
    p.hypertension = true
    setIf('hypertension_grade', form.c_hypertension_grade)
    setIf('systolic_bp', form.c_current_sbp)
    setIf('diastolic_bp', form.c_current_dbp)
    if (form.c_bp_high) p.bp_high = form.c_bp_high === '是'
  }
  if (form.c_af) p.af = true
  if (form.c_hf) p.hf = true
  if (form.c_diabetes) p.diabetes = true
  if (form.c_dyslipidemia) {
    p.dyslipidemia = true
    setIf('lipid_goal', form.c_lipid_goal)
    if (form.c_lipid_goal === '未服药') p.need_start_lipid = true
    if (form.c_lipid_goal === '未达标') p.statin_4_6w_not_goal = true
  }
  if (form.c_copd || form.c_asthma) p.asthma_copd = true
  if (form.c_ckd) {
    p.ckd = true
    setIf('ckd_stage', form.c_ckd_stage)
  }
  if (form.c_prior_mi) {
    p.prior_mi_event = true
    setIf('prior_mi_date', form.c_prior_mi_date)
  }
  if (form.c_prior_stroke) {
    p.prior_mi_stroke = true
    p.stroke_tia_history = true
    setIf('prior_stroke_date', form.c_prior_stroke_date)
  }
  if (form.c_ulcer) p.ulcer_bleed_history = true
  if (form.c_ich) p.ich_history = true
  setIf('other_pmh', form.other_pmh)
  if (form.c_liver) {
    p.c_liver = true
    setIf('liver_degree', form.c_liver_degree)
  }
  if (form.c_dm_fpg !== null) p.fpg = Number(form.c_dm_fpg)
  if (form.c_dm_hba1c) p.hba1c = Number(form.c_dm_hba1c)

  p.hb_low = !!form.hb_low
  p.plt_status = form.plt_status === '降低' ? '降低' : '正常'
  if (form.plt_drop_over_50pct) p.plt_drop_over_50pct = true
  p.brown_urine = !!form.brown_urine
  p.jaundice = !!form.jaundice
  if (form.alt_ast_status !== '正常') p.alt_ast_status = form.alt_ast_status
  setIf('scr', form.scr)
  setIf('egfr', form.egfr)
  setIf('crcl', form.crcl)
  p.coag_abnormal = !!form.coag_abnormal
  p.ck_status = form.ck_status
  p.troponin_elevated = !!form.troponin_elevated
  p.potassium_status = form.potassium_status
  setIf('baseline_ldl', form.ldl)
  setIf('current_ldl', form.current_ldl)
  if (form.fbg_status !== '正常') p.fbg_status = form.fbg_status
  else if (form.fpg !== null) p.fbg_status = Number(form.fpg) >= 6.1 ? '高' : Number(form.fpg) < 3.9 ? '低' : '正常'
  setIf('hba1c', form.hba1c)
  p.sinus_rhythm = !!form.sinus_rhythm
  setIf('heart_rate', form.heart_rate)
  setIf('qtc', form.qtc)
  setIf('qtc_baseline', form.qtc_baseline)
  setIf('lvef', form.lvef)
  if (form.lvef !== null && form.lvef !== '' && Number(form.lvef) <= 40) p.lvef_reduced = true
  p.wall_abnormality = !!(form.wall_aneurysm || form.wall_motion)
  setIf('bnp', form.bnp)

  setIf('hb', form.hb)
  setIf('hb_prev', form.hb_prev)
  setIf('plt', form.plt)
  setIf('alt', form.alt)
  setIf('ast', form.ast)
  setIf('ck', form.ck)
  setIf('troponin_value', form.troponin_value)
  setIf('potassium', form.potassium)
  setIf('sodium', form.sodium)
  setIf('inr', form.inr)
  setIf('fibrinogen', form.fibrinogen)
  setIf('hs_ctnt', form.hs_ctnt)
  setIf('co2cp', form.co2cp)
  setIf('baseline_scr', form.baseline_scr)
  setIf('calcium_corrected', form.calcium)
  setIf('fpg', form.fpg ?? form.c_dm_fpg)
  setIf('tc', form.tc)
  setIf('tg', form.tg)
  setIf('hdl', form.hdl)
  if (form.lipid_abnormal) p.lipid_abnormal = form.lipid_abnormal
  p.urine_protein = !!form.urine_protein
  p.st_t = !!form.st_t
  p.arrhythmia = !!form.arrhythmia
  p.hr_abnormal = !!form.hr_abnormal
  p.qtc_prolonged = !!form.qtc_prolonged
  p.wall_aneurysm = !!form.wall_aneurysm
  p.wall_motion = !!form.wall_motion
  if (form.echo_other) p.echo_other = form.echo_other
  for (const key of ['wbc', 'bilirubin', 'albumin', 'pt', 'aptt', 'tt', 'd_dimer', 'ck_mb',
    'pr_interval', 'qrs_duration']) setIf(key, form[key])
  setIf('arrhythmia_type', form.arrhythmia_type)
  p.troponin_reference_known = !!form.troponin_reference_known

  const ap = ['aspirin', 'clopidogrel', 'ticagrelor', 'indobufen']
  const apNow: string[] = []
  const apDischarge: string[] = []
  for (const key of ap) {
    const now = form.med_now[key]
    const discharge = form.med_discharge[key]
    if (form.med_sel[key] && now > 0) {
      apNow.push(key)
      p[`on_${key}`] = true
      if (key !== 'indobufen') p[`${key}_dose`] = now
    }
    if (form.med_sel[key] && discharge > 0) apDischarge.push(key)
  }
  if (apNow.length) p.on_antiplatelet = true
  if (apNow.length >= 2) p.on_dapt = true
  if (apDischarge.length) {
    p.discharge_meds = apDischarge.map((k) => DRUG_BY_KEY[k]?.name ?? k)
    if (apDischarge.length >= 2) p.discharge_dapt = true
  }
  if (form.med_used.anticoagulant) {
    const customAnticoagulants = form.med_custom.anticoagulant.filter((d: CustomMed) => d.name.trim())
    if (customAnticoagulants.some((d: CustomMed) => Number(d.discharge) > 0)) p.discharge_anticoagulant = true
    if (Number(form.med_discharge.rivaroxaban) > 0 || Number(form.med_discharge.warfarin) > 0) p.discharge_anticoagulant = true
    if (Number(form.med_now.rivaroxaban) > 0) {
      p.on_noac = true
      p.noac_type = '利伐沙班'
    }
    if (Number(form.med_now.warfarin) > 0) p.on_warfarin = true
    if (customAnticoagulants.some((d: CustomMed) => Number(d.now) > 0)) p.on_anticoagulant = true
    if (p.on_noac || p.on_warfarin) p.on_anticoagulant = true
  }
  const nowDose = (key: string) => Number(form.med_now[key]) > 0
  const firstNow = (cat: string) => MED_CATEGORIES.find((c) => c.key === cat)?.drugs.find((d) => form.med_sel[d.key] && nowDose(d.key))
  const beta = firstNow('beta')
  if (form.med_used.beta && beta) {
    p.on_beta_blocker = true
    p.beta_blocker_type = beta.name
  }
  const raas = firstNow('raas')
  if (form.med_used.raas && raas) {
    p.on_acei_arb = true
    p.acei_arb_type = raas.key === 'sacubitril_valsartan' ? 'ARNI' : raas.key.endsWith('sartan') ? 'ARB' : 'ACEI'
  }
  const diuretic = firstNow('diuretic')
  if (form.med_used.diuretic && diuretic) {
    p.on_diuretic = true
    p.diuretic_type = diuretic.name
  }
  const ppi = firstNow('ppi')
  if (form.med_used.ppi && ppi) p.ppi = ppi.name
  const ccb = firstNow('ccb')
  if (form.med_used.ccb && ccb) {
    p.on_ccb = true
    p.ccb_type = ccb.key === 'diltiazem' ? '非二氢吡啶类' : '二氢吡啶类'
  }
  if (form.med_used.lipid && nowDose('atorvastatin')) p.on_statin = true
  if (form.med_used.lipid && nowDose('rosuvastatin')) p.on_statin = true
  if (form.med_used.glucose && nowDose('metformin')) p.on_metformin = true
  if (form.med_used.other && nowDose('isosorbide')) p.on_nitrate = true
  const customOtherNames = form.med_custom.other.filter((d: CustomMed) => Number(d.now) > 0).map((d: CustomMed) => d.name.trim()).filter(Boolean)
  p.other_med_name = customOtherNames.join('、')
  const otherNames = customOtherNames.join('、')
  if (otherNames.includes('胺碘酮')) p.on_amiodarone = true
  if (/西地那非|他达拉非|PDE5/i.test(otherNames)) p.on_pde5i = true
  if (/布洛芬|激素|NSAIDs|双氯芬酸/i.test(otherNames)) p.on_nsaid_steroid = true
  if (selectedDrugs.value.some((d) => d.category === '降脂药物' && Number(d.now) > 0 && /他汀/.test(d.name))) p.on_statin = true
  if (form.med_custom.ppi.some((d: CustomMed) => Number(d.now) > 0 && d.name.trim())) p.ppi = form.med_custom.ppi.find((d: CustomMed) => Number(d.now) > 0).name
  if (form.med_special.beta_blocker_contra) p.beta_blocker_intolerant = true
  for (const s of SPECIAL) if (form.med_special[s.key]) p[s.key] = true
  p.other_drug_intolerances = form.other_intolerance ? form.other_intolerance_names.map((n: string) => n.trim()).filter(Boolean) : []

  const activeSymptoms = SYMPTOMS.filter((s) => form[s.key])
  if (activeSymptoms.some((s) => s.severity === 'red')) p.red_flag = true
  if (form.sym_chest) p.chest_pain = true
  if (form.bleed_bruise || form.bleed_gum) p.mild_bleed = true
  if (form.sym_dry_cough) p.dry_cough = true
  if (form.sym_edema) p.edema = true
  const temp = form.temp_meds || ''
  if (/鱼油|纳豆|活血|中成药/.test(temp)) p.blood_activating = true
  if (/对乙酰氨基酚|镇痛|止痛|布洛芬|双氯芬酸/.test(temp)) p.need_analgesic = true
  if (/布洛芬|双氯芬酸|激素|NSAIDs/.test(temp)) p.on_nsaid_steroid = true
  if (form.surgery_name) p.planned_surgery = form.surgery_name + (form.surgery_date_planned ? `（${form.surgery_date_planned}）` : '')
  for (const a of ADR) if (form[a.key]) {
    const map: Record<string, string> = {
      adr_bradycardia: 'bradycardia', adr_rate_fast: 'rate_still_fast', adr_angina: 'angina_inadequate',
    }
    if (map[a.key]) p[map[a.key]] = true
  }
  if (form.referral_confirmed) p.referral_plan_confirmed = true
  if (form.recent_symptom) p.recent_symptom_after_referral = true

  const months = Number(p.post_pci_months) || 0
  const target = p.scenario === 'CCS' ? 6 : 12
  if (months >= target) p.dapt_expired = true
  if (months >= 12) p.long_term_phase = true

  const coreChecks = [
    hasValue(form.age), hasValue(form.sex), hasValue(form.surgery_date), hasValue(form.diagnosis),
    hasValue(form.vessels), selectedVessels.value.length > 0,
    selectedVessels.value.every((v) => interventionTotal(v.key) > 0),
  ]
  p.report_context = {
    core_completed: coreChecks.filter(Boolean).length,
    exam_cards: EXAM_CARDS.filter((card) => card.fields.some((field) => !isExamDefault(field))).map((card) => card.key),
    exam_fields: EXAM_CARDS.flatMap((card) => card.fields.filter((field) => !isExamDefault(field)).flatMap((field) => [field.key, ...(field.secondKey ? [field.secondKey] : [])])), 
    medications: selectedDrugs.value.map((d) => ({
      key: d.key, name: d.name, category: d.category, discharge: d.discharge, now: d.now,
      dischargeFrequency: d.dischargeFrequency, nowFrequency: d.nowFrequency,
    })),
    symptoms: activeSymptoms.map((s) => ({ key: s.key, label: s.label, severity: s.severity, bleeding: s.bleeding })),
    bleeding_events: activeSymptoms.filter((s) => s.bleeding).map((s) => ({ key: s.key, label: s.label, severe: s.severity === 'red' })),
    adherence_events: form.adherence.filter((a: AdherenceEntry) => a.drug.trim()).map((a: AdherenceEntry) => ({ drug: a.drug.trim(), days: a.days })),
    adrs: ADR.filter((a) => form[a.key]).map((a) => ({ key: a.key, label: a.label })),
    temp_meds: form.temp_meds || '',
  }
  return p
}

async function submit(): Promise<void> {
  if (!validateAll()) return
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
    screen.value = 'result'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    errorMsg.value = '调用后端失败：' + msg + '。请确认 uvicorn 已在 backend 目录启动。'
    screen.value = 'result'
  } finally {
    loading.value = false
  }
}

function saveDraft(): void {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ version: 4, form, step: currentStep.value, savedAt: Date.now() }))
  } catch { /* ignore quota */ }
}

function resetForm(): void {
  const fresh = makeForm()
  Object.keys(form).forEach((key) => delete (form as any)[key])
  Object.assign(form, fresh)
}

function loadDraft(): void {
  const raw = localStorage.getItem(DRAFT_KEY) || localStorage.getItem(LEGACY_DRAFT_KEY)
  if (!raw) return
  try {
    const draft = JSON.parse(raw)
    if (![3, 4].includes(draft.version) || !draft.form) return
    restoring = true
    const saved = draft.form
    resetForm()
    Object.assign(form, saved)
    for (const cat of MED_CATEGORIES) {
      form.med_custom[cat.key] = Array.isArray(saved.med_custom?.[cat.key]) ? saved.med_custom[cat.key] : []
      for (const drug of cat.drugs) {
        form.med_discharge_freq[drug.key] = saved.med_discharge_freq?.[drug.key] || drug.stdFrequency || 'qd'
        form.med_now_freq[drug.key] = saved.med_now_freq?.[drug.key] || drug.stdFrequency || 'qd'
      }
    }
    if (!Array.isArray(form.adherence) || !form.adherence.length) form.adherence = [{ id: nextEntryId++, drug: '', days: null }]
    form.other_intolerance_names = Array.isArray(saved.other_intolerance_names) && saved.other_intolerance_names.length ? saved.other_intolerance_names : ['']
    currentStep.value = Math.min(4, Number(draft.step) || 0)
    restoring = false
    ElMessage.info(draft.version === 3 ? '已恢复旧版草稿，并补齐新版字段' : '已为您恢复上次填写内容')
  } catch {
    restoring = false
  }
}

function clearDraft(): void {
  localStorage.removeItem(DRAFT_KEY)
  localStorage.removeItem(LEGACY_DRAFT_KEY)
}

async function saveAndExit(): Promise<void> {
  saveDraft()
  await ElMessageBox.alert('已保存到本机；下次打开会自动恢复。可以直接关闭页面。', '已保存', {
    confirmButtonText: '知道了',
  })
}

async function reset(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定清空所有填写内容？此操作不可撤销。', '重新填写', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  if (saveTimer !== null) {
    window.clearTimeout(saveTimer)
    saveTimer = null
  }
  restoring = true
  resetForm()
  clearDraft()
  currentStep.value = 0
  screen.value = 'form'
  result.value = null
  errors.value = []
  errorMsg.value = ''
  await nextTick()
  restoring = false
}

function printResult(): void {
  window.print()
}

function exportPdf(): void {
  ElMessage.info('在打印对话框中选择「另存为 PDF」即可导出。')
  window.print()
}

watch(form, () => {
  if (restoring) return
  if (saveTimer !== null) window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(saveDraft, 500)
}, { deep: true })

onMounted(() => {
  loadDraft()
  const step = Number(new URLSearchParams(window.location.search).get('step'))
  if (Number.isInteger(step) && step >= 1 && step <= 5) currentStep.value = step - 1
})
</script>

<template>
  <div class="page">
    <header class="brand">
      <div class="brand-icon"><el-icon :size="30"><FirstAidKit /></el-icon></div>
      <div class="brand-text">
        <h1>PCI 术后用药管理助手</h1>
        <p>基于分级诊疗指南的规则引擎 · 零自由发挥 · 每一条建议可溯源</p>
      </div>
      <span class="brand-tag">基层辅助决策</span>
    </header>

    <div class="view-tabs">
      <button :class="['view-tab', { on: view === 'form' }]" @click="view = 'form'">智能用药方案</button>
      <button :class="['view-tab', { on: view === 'chat' }]" @click="view = 'chat'">AI 用药问答</button>
    </div>

    <ChatView v-if="view === 'chat'" />

    <template v-else>
      <template v-if="screen === 'form'">
        <el-card class="panel" shadow="never">
          <el-steps :active="currentStep" finish-status="success" align-center class="steps">
            <el-step v-for="(s, i) in STEPS" :key="i" :title="s.title" />
          </el-steps>
        </el-card>

        <el-card class="panel form-panel" shadow="never">
          <div class="form-head">
            <span class="form-badge">{{ currentStep + 1 }}</span>
            <div><h2>{{ STEPS[currentStep].title }}</h2></div>
            <el-button class="save-exit" size="small" text @click="saveAndExit">保存并退出</el-button>
          </div>

          <el-alert v-if="errors.length" type="error" :closable="false" show-icon class="form-alert">
            <template #title>还有 {{ errors.length }} 项需要处理</template>
            <ul class="error-list"><li v-for="(e, i) in errors" :key="i">{{ e }}</li></ul>
          </el-alert>

          <!-- ================= 第 1 步：基本信息 ================= -->
          <template v-if="currentStep === 0">
            <el-form label-width="190px" label-position="left" class="form">
              <el-form-item>
                <template #label><span class="field-label"><span class="req">*</span>年龄</span></template>
                <div class="field-wrap">
                  <el-input-number v-model="form.age" :min="18" controls-position="right" class="ctrl" />
                  <p class="field-note">核心必填；仅用于成年患者</p>
                </div>
              </el-form-item>

              <el-form-item>
                <template #label><span class="field-label"><span class="req">*</span>性别</span></template>
                <div class="option-group">
                  <label v-for="op in ['男', '女']" :key="op" class="opt">
                    <input v-model="form.sex" type="radio" :value="op" /><span>{{ op }}</span>
                  </label>
                </div>
              </el-form-item>

              <el-form-item>
                <template #label><span class="field-label"><span class="req">*</span>PCI 手术日期</span></template>
                <div class="field-wrap">
                  <el-date-picker v-model="form.surgery_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" class="ctrl" />
                  <p class="field-note">填日期后自动计算术后时长</p>
                </div>
              </el-form-item>

              <el-form-item>
                <template #label><span class="field-label">术后时长</span></template>
                <div class="field-wrap">
                  <el-input-number v-model="form.post_pci_months" :min="0" :max="240" controls-position="right" class="ctrl" />
                  <span class="inline-unit">月</span>
                  <p class="field-note">已自动计算，可手动修正</p>
                </div>
              </el-form-item>

              <el-form-item>
                <template #label><span class="field-label"><span class="req">*</span>出院诊断</span></template>
                <div class="option-group option-block">
                  <label v-for="d in DIAGNOSES" :key="d.label" class="opt">
                    <input v-model="form.diagnosis" type="radio" :value="d.label" /><span>{{ d.label }}</span>
                  </label>
                </div>

              </el-form-item>

              <el-form-item>
                <template #label><span class="field-label"><span class="req">*</span>病变支数</span></template>
                <div class="option-group">
                  <label v-for="op in ['单支', '双支', '三支']" :key="op" class="opt">
                    <input v-model="form.vessels" type="radio" :value="op" /><span>{{ op }}</span>
                  </label>
                </div>
                <p class="field-note">双支及以上记为多支病变</p>
              </el-form-item>

              <el-form-item>
                <template #label><span class="field-label"><span class="req">*</span>干预血管与干预方式</span></template>
                <div class="vessel-block">
                  <p class="field-note">勾选干预血管后，填写每条血管的球囊 / 支架数量；填 0 表示未使用。至少一条血管需要填写干预方式。</p>
                  <div v-for="v in VESSELS" :key="v.key" class="vessel-row">
                    <el-checkbox v-model="form['vessel_' + v.key]" class="vessel-check">{{ v.label }}</el-checkbox>
                    <div v-if="form['vessel_' + v.key]" class="vessel-inputs">
                      <span class="vessel-input-label">药物洗脱支架（枚）</span>
                      <el-input-number v-model="form['iv_' + v.key].des" :min="0" :max="20" controls-position="right" class="ctrl-xs" />
                      <span class="vessel-input-label">药物球囊（个）</span>
                      <el-input-number v-model="form['iv_' + v.key].dcb" :min="0" :max="20" controls-position="right" class="ctrl-xs" />
                      <span class="vessel-input-label">可吸收支架（枚）</span>
                      <el-input-number v-model="form['iv_' + v.key].brs" :min="0" :max="20" controls-position="right" class="ctrl-xs" />
                    </div>
                    <p v-if="v.key === 'left_main' && form.vessel_left_main" class="field-note danger-note">左主干病变纳入高缺血风险</p>
                  </div>
                </div>
              </el-form-item>
            </el-form>

            <el-collapse class="optional-collapse">
              <el-collapse-item title="补充信息（选填）" name="optional">
                <el-form label-width="190px" label-position="left" class="form">
                  <el-form-item label="是否急诊 PCI">
                    <el-switch v-model="form.emergency_pci" active-text="是" inactive-text="否" />
                  </el-form-item>
                  <el-form-item label="出院抗栓方案">
                    <el-input v-model="form.discharge_plan" placeholder="填写出院抗栓方案" class="ctrl-text" />
                  </el-form-item>
                </el-form>
              </el-collapse-item>
            </el-collapse>
          </template>

          <!-- ================= 第 2 步：合并症与既往史 ================= -->
          <template v-else-if="currentStep === 1">
            <p class="section-hint">默认均为“无”；勾选后才展开子项，避免满屏空表单。</p>
            <div class="comorb-list">
              <div v-for="item in COMORB" :key="item.key" class="comorb-item">
                <div class="comorb-head">
                  <el-switch v-model="form['c_' + item.key]" />
                  <span class="comorb-label" :title="termTip(item.label)">{{ item.label }}</span>
                  <span v-if="item.hint" class="comorb-hint">{{ item.hint }}</span>
                </div>
                <div v-if="form['c_' + item.key] && item.sub" class="comorb-sub">
                  <div v-for="sub in item.sub" :key="sub.key" class="comorb-sub-row">
                    <span class="comorb-sub-label">{{ sub.label }}</span>
                    <el-select v-if="sub.kind === 'select'" v-model="form['c_' + sub.key]" placeholder="请选择" class="ctrl-sm">
                      <el-option v-for="op in sub.options" :key="op" :label="op" :value="op" />
                    </el-select>
                    <template v-else-if="sub.kind === 'number'">
                      <el-input-number v-if="sub.shared" v-model="form[sub.key]" controls-position="right" class="ctrl-sm" />
                      <el-input-number v-else v-model="form['c_' + sub.key]" controls-position="right" class="ctrl-sm" />
                      <span v-if="sub.unit" class="inline-unit">{{ sub.unit }}</span>
                    </template>
                    <template v-else-if="sub.kind === 'date'">
                      <el-date-picker v-model="form['c_' + sub.key]" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" class="ctrl" />
                      <span class="date-elapsed">{{ elapsedDate(form['c_' + sub.key]) }}</span>
                    </template>
                    <el-input v-else v-model="form['c_' + sub.key]" :placeholder="sub.placeholder || '选填'" class="ctrl-text" />
                  </div>
                </div>
              </div>
            </div>
            <el-form label-width="190px" label-position="left" class="form" style="margin-top: 16px">
              <el-form-item label="其他合并症和既往史">
                <el-input v-model="form.other_pmh" placeholder="如心脏瓣膜病、心律失常、痛风、甲状腺功能异常、肿瘤等" class="ctrl-text" />
              </el-form-item>
            </el-form>
          </template>

          <!-- ================= 第 3 步：辅助检查 ================= -->
          <template v-else-if="currentStep === 2">
            <div class="section-tip">
              <el-icon :size="15"><Camera /></el-icon>
              <span>支持 JPG / PNG，一次最多 5 张，逐张识别后合并；识别失败可直接手动填写，不影响生成建议。</span>
              <el-button size="small" type="primary" plain class="ocr-any" @click="openOcr('')">拍照或上传化验单（可多张）</el-button>
            </div>
            <el-alert
              type="warning"
              :closable="false"
              show-icon
              class="multi-patient-alert"
              title="多张照片仅限同一位患者；不同患者请分开识别。"
            />
            <div class="exam-grid">
              <div
                v-for="card in EXAM_CARDS"
                :key="card.key"
                :class="['exam-card', { 'exam-card-wide': card.key === 'critical' }]"
              >
                <div class="exam-head">
                  <div class="exam-title">
                    {{ card.name }}
                    <span v-if="card.hint" class="exam-items">{{ card.hint }}</span>
                  </div>
                  <el-button size="small" text type="primary" @click="openOcr(card.name)">
                    <el-icon :size="14"><Camera /></el-icon>拍照识别
                  </el-button>
                </div>
                <div class="exam-body">
                  <div v-for="f in card.fields" :key="f.key" class="exam-field">
                    <span class="exam-label" :title="termTip(f.label)">
                      {{ labelMain(f.label) }}<span v-if="labelAbbr(f.label)" class="abbr">{{ labelAbbr(f.label) }}</span>
                    </span>
                    <div v-if="f.kind === 'pair'" class="exam-pair">
                      <el-input-number v-model="form[f.key]" :min="0" controls-position="right" class="ctrl-xs" placeholder="ALT" />
                      <span>/</span>
                      <el-input-number v-model="form[f.secondKey!]" :min="0" controls-position="right" class="ctrl-xs" placeholder="AST" />
                    </div>
                    <el-input-number
                      v-else-if="f.kind === 'number'"
                      v-model="form[f.key]"
                      :min="0"
                      controls-position="right"
                      class="ctrl-sm"
                      :placeholder="f.placeholder || '数值'"
                    />
                    <div v-else-if="f.kind === 'status'" class="option-group">
                      <label v-for="op in f.options" :key="op" class="opt opt-sm">
                        <input v-model="form[f.key]" type="radio" :value="op" /><span>{{ op }}</span>
                      </label>
                    </div>
                    <el-switch v-else-if="f.kind === 'bool'" v-model="form[f.key]" />
                    <el-input v-else v-model="form[f.key]" :placeholder="f.placeholder || '选填'" class="ctrl-sm" />
                    <span v-if="f.unit" class="inline-unit">{{ f.unit }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- ================= 第 4 步：用药 ================= -->
          <template v-else-if="currentStep === 3">
            <div class="med-summary" v-if="selectedDrugs.length">
              <span class="med-summary-title">当前已选 {{ selectedDrugs.length }} 种药</span>
              <span v-for="d in selectedDrugs" :key="d.key" class="src-chip">{{ d.name }}</span>
            </div>
            <el-alert v-if="medChanges.length" type="warning" :closable="false" show-icon class="med-change-alert" title="出院时 vs 现在：发现以下差异，请核对是否擅自停药 / 减量">
              <ul class="med-change-list"><li v-for="c in medChanges" :key="c.name"><b>{{ c.name }}</b>：{{ c.text }}</li></ul>
            </el-alert>

            <div v-for="cat in MED_CATEGORIES" :key="cat.key" class="med-cat">
              <div class="med-cat-head">
                <el-switch v-model="form.med_used[cat.key]" @change="onCategoryToggle(cat)" />
                <span class="med-name" :title="termTip(cat.label)">{{ labelMain(cat.label) }}<span v-if="labelAbbr(cat.label)" class="abbr">{{ labelAbbr(cat.label) }}</span></span>
              </div>
              <div v-if="form.med_used[cat.key]" class="med-body">
                <div v-for="drug in cat.drugs" :key="drug.key" class="drug-row">
                  <el-checkbox v-model="form.med_sel[drug.key]" class="drug-check">{{ drug.name }}</el-checkbox>
                  <div v-if="form.med_sel[drug.key]" class="dose-pair">
                    <div class="dose-group">
                      <span class="dose-label">出院</span>
                      <el-input-number v-model="form.med_discharge[drug.key]" :min="0" controls-position="right" class="ctrl-xs" placeholder="剂量" />
                      <span class="inline-unit">mg</span>
                      <el-select v-model="form.med_discharge_freq[drug.key]" class="freq-select" aria-label="出院频次"><el-option v-for="f in FREQUENCIES" :key="f" :label="f" :value="f" /></el-select>
                    </div>
                    <div class="dose-group">
                      <span class="dose-label">现在</span>
                      <el-input-number v-model="form.med_now[drug.key]" :min="0" controls-position="right" class="ctrl-xs" placeholder="剂量" />
                      <span class="inline-unit">mg</span>
                      <el-select v-model="form.med_now_freq[drug.key]" class="freq-select" aria-label="当前频次"><el-option v-for="f in FREQUENCIES" :key="f" :label="f" :value="f" /></el-select>
                      <el-button v-if="drug.stdValue" size="small" text type="primary" @click="fillStd(drug)">填标准量</el-button>
                    </div>
                  </div>
                </div>
                <div v-if="cat.custom" class="custom-med-list">
                  <div v-for="(med, index) in form.med_custom[cat.key]" :key="med.id" class="custom-med-row">
                    <div class="custom-med-head"><strong>其他药物 {{ index + 1 }}</strong><el-button text type="danger" size="small" @click="removeCustomMed(cat, med.id)">删除</el-button></div>
                    <el-input v-model="med.name" placeholder="输入药品名称" class="ctrl-text" />
                    <div class="dose-pair">
                      <div class="dose-group"><span class="dose-label">出院</span><el-input-number v-model="med.discharge" :min="0" controls-position="right" class="ctrl-xs" /><span class="inline-unit">mg</span><el-select v-model="med.dischargeFrequency" class="freq-select"><el-option v-for="f in FREQUENCIES" :key="f" :label="f" :value="f" /></el-select></div>
                      <div class="dose-group"><span class="dose-label">现在</span><el-input-number v-model="med.now" :min="0" controls-position="right" class="ctrl-xs" /><span class="inline-unit">mg</span><el-select v-model="med.nowFrequency" class="freq-select"><el-option v-for="f in FREQUENCIES" :key="f" :label="f" :value="f" /></el-select></div>
                    </div>
                  </div>
                  <el-button size="small" plain @click="addCustomMed(cat)">＋ 添加其他药物</el-button>
                </div>
              </div>
            </div>

            <el-collapse class="optional-collapse" style="margin-top: 16px">
              <el-collapse-item title="用药特殊情况（不耐受 / 禁忌，选填）" name="special">
                <el-form label-width="280px" label-position="left" class="form">
                  <el-form-item v-for="s in SPECIAL" :key="s.key" :label="s.label"><el-switch v-model="form.med_special[s.key]" /></el-form-item>
                  <el-form-item label="其他药物不耐受 / 禁忌"><el-switch v-model="form.other_intolerance" /></el-form-item>
                  <div v-if="form.other_intolerance" class="dynamic-list">
                    <div v-for="(_, index) in form.other_intolerance_names" :key="index" class="inline-row">
                      <el-input v-model="form.other_intolerance_names[index]" placeholder="输入具体药品名称" class="ctrl-text" />
                      <el-button text type="danger" @click="removeIntoleranceName(index)">删除</el-button>
                    </div>
                    <el-button size="small" plain @click="addIntoleranceName">＋ 添加药品名称</el-button>
                  </div>
                </el-form>
              </el-collapse-item>
            </el-collapse>
          </template>

          <!-- ================= 第 5 步：症状与用药行为 ================= -->
          <template v-else>
            <div v-for="group in SYMPTOM_GROUPS" :key="group.severity" :class="['symptom-block', `symptom-${group.severity}`]">
              <h3 class="symptom-title">{{ group.title }}</h3>
              <div class="switch-grid">
                <label v-for="s in group.items" :key="s.key" :class="['switch-chip', { danger: group.severity === 'red' && form[s.key] }]">
                  <el-switch v-model="form[s.key]" /><span>{{ s.label }}</span>
                </label>
              </div>
            </div>

            <el-form label-width="190px" label-position="left" class="form">
              <el-form-item label="临时用药">
                <el-input
                  v-model="form.temp_meds"
                  type="textarea"
                  :rows="2"
                  placeholder="对乙酰氨基酚、镇痛药、活血中成药等"
                  class="ctrl-text"
                />
              </el-form-item>

              <el-form-item label="用药依从性">
                <div class="dynamic-list">
                  <div v-for="entry in form.adherence" :key="entry.id" class="adherence-row">
                    <el-input v-model="entry.drug" placeholder="输入停药 / 漏服药品名称" class="ctrl-text" />
                    <span class="inline-unit">已停 / 漏服</span>
                    <el-input-number v-model="entry.days" :min="0" controls-position="right" class="ctrl-xs" />
                    <span class="inline-unit">天</span>
                    <el-button text type="danger" :disabled="form.adherence.length === 1" @click="removeAdherence(entry.id)">删除</el-button>
                  </div>
                  <el-button size="small" plain @click="addAdherence">＋ 添加一种药物</el-button>
                </div>
              </el-form-item>

              <el-form-item label="拟行其他手术">
                <div class="inline-row">
                  <el-input v-model="form.surgery_name" placeholder="手术名称" class="ctrl-text" />
                  <el-date-picker v-model="form.surgery_date_planned" type="date" value-format="YYYY-MM-DD" placeholder="预计日期" class="ctrl" />
                </div>
                <p class="field-note">影响抗栓药围手术期管理</p>
              </el-form-item>
            </el-form>

            <el-collapse class="optional-collapse">
              <el-collapse-item title="其他（药物相关表现 / 下转信息，选填）" name="other">
                <div class="switch-grid">
                  <label v-for="a in ADR" :key="a.key" class="switch-chip">
                    <el-switch v-model="form[a.key]" /><span>{{ a.label }}</span>
                  </label>
                </div>
                <el-form label-width="240px" label-position="left" class="form" style="margin-top: 12px">
                  <el-form-item label="上级方案下转已确认">
                    <el-switch v-model="form.referral_confirmed" />
                  </el-form-item>
                  <el-form-item label="下转后 1 个月内再发症状">
                    <el-switch v-model="form.recent_symptom" />
                  </el-form-item>
                </el-form>
              </el-collapse-item>
            </el-collapse>
          </template>

          <div class="nav">
            <el-button v-if="currentStep > 0" size="large" @click="prev">上一步</el-button>
            <el-button v-if="currentStep < STEPS.length - 1" type="primary" size="large" @click="next">下一步</el-button>
            <el-button v-else type="primary" size="large" @click="goReview">
              <el-icon class="btn-icon"><Document /></el-icon>进入核对页
            </el-button>
          </div>
          <p class="hint"><span class="req">*</span> 为核心字段；条件必填仅在对应开关打开后要求，其余按实际可获取情况补充</p>
        </el-card>
      </template>

      <!-- ================= 提交核对页 ================= -->
      <template v-else-if="screen === 'review'">
        <el-card class="panel review-panel" shadow="never">
          <div class="result-head">
            <h2>提交核对</h2>
            <span class="review-note">确认后系统将依据分级诊疗指南生成用药分析与建议</span>
          </div>
          <div class="review-grid">
            <div v-for="g in summaryGroups" :key="g.step" class="review-item">
              <div class="review-item-head">
                <span class="review-step">{{ g.step + 1 }}</span>
                <span class="review-title">{{ g.title }}</span>
                <el-button size="small" text type="primary" @click="editStep(g.step)">修改</el-button>
              </div>
              <p class="review-count">已填 {{ g.count }} 项</p>
              <p class="review-desc">{{ g.desc }}</p>
            </div>
          </div>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="review-tip"
            title="请核对以上信息，确认无误后开始分析；如有错误请点对应分组的「修改」。"
          />
          <div class="nav">
            <el-button size="large" @click="editStep(4)">返回修改</el-button>
            <el-button type="primary" size="large" :loading="loading" @click="submit">
              <el-icon class="btn-icon"><Document /></el-icon>确认无误，开始分析
            </el-button>
          </div>
        </el-card>
      </template>

      <!-- ================= 分析结果页 ================= -->
      <template v-else>
        <el-card v-if="errorMsg" class="panel" shadow="never">
          <el-alert :title="errorMsg" type="error" show-icon :closable="false" />
          <div class="nav"><el-button type="primary" size="large" @click="screen = 'review'">返回核对页</el-button></div>
        </el-card>

        <el-card v-else-if="result" class="panel result-panel" shadow="never">
          <AnalysisReport v-if="result.report" :report="result.report" />
          <el-alert v-else title="后端未返回结构化报告，请重启后端后重新分析。" type="error" show-icon :closable="false" />

          <div class="result-actions">
            <el-button @click="printResult"><el-icon class="btn-icon"><Printer /></el-icon>打印</el-button>
            <el-button @click="exportPdf"><el-icon class="btn-icon"><Download /></el-icon>导出 PDF</el-button>
            <el-button @click="screen = 'review'">返回核对页</el-button>
            <el-button type="primary" @click="reset"><el-icon class="btn-icon"><RefreshLeft /></el-icon>重新填写</el-button>
          </div>
        </el-card>
      </template>
    </template>

    <OcrDialog v-model="ocrVisible" :card-hint="ocrHint" :current="ocrCurrent" @apply="applyOcr" />
  </div>
</template>

<style></style>


