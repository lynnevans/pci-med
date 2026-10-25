<script setup>
import { reactive, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

// ============ 分步问诊字段配置（注意：key 与后端 rule_engine.py 字段完全一致） ============
const steps = [
  {
    title: '基本信息',
    desc: '年龄、性别、化验值、危险分层',
    fields: [
      { key: 'age', label: '年龄', type: 'number', unit: '岁', min: 0, max: 120 },
      { key: 'sex', label: '性别', type: 'select', options: ['男', '女'] },
      { key: 'weight', label: '体重', type: 'number', unit: 'kg', min: 0, max: 300 },
      { key: 'scr', label: '血肌酐', type: 'number', unit: 'μmol/L', min: 0 },
      { key: 'egfr', label: 'eGFR', type: 'number', unit: 'ml/min/1.73m²', min: 0 },
      { key: 'hb', label: '血红蛋白', type: 'number', unit: 'g/L', min: 0 },
      { key: 'plt', label: '血小板', type: 'number', unit: '×10⁹/L', min: 0 },
      { key: 'ascvd_risk', label: 'ASCVD 危险分层', type: 'select', options: ['极高危', '超高危'] },
    ],
  },
  {
    title: '手术与场景',
    desc: 'PCI 手术史、术后时长、支架情况',
    fields: [
      { key: 'scenario', label: '就诊场景', type: 'select', options: ['ACS', 'CCS'] },
      { key: 'post_pci', label: '是否 PCI 术后', type: 'boolean' },
      { key: 'post_pci_months', label: '术后时长', type: 'number', unit: '月', min: 0, max: 240 },
      { key: 'surgery_date', label: '手术日期', type: 'date' },
      { key: 'stent_type', label: '支架类型与数量', type: 'text', placeholder: '如：药物洗脱支架×1' },
      { key: 'discharge_plan', label: '出院方案', type: 'text', placeholder: '如：DAPT 12个月' },
      { key: 'dcb', label: '药物涂层球囊（DCB）', type: 'boolean' },
      { key: 'emergency_pci', label: '急诊 PCI', type: 'boolean' },
      { key: 'precis_dapt', label: 'PRECISE-DAPT 评分', type: 'number', min: 0, max: 60 },
    ],
  },
  {
    title: '风险评分',
    desc: '出血/缺血/降脂相关评分',
    fields: [
      { key: 'has_bled', label: 'HAS-BLED 评分', type: 'number', min: 0, max: 9 },
      { key: 'cha2ds2_vasc', label: 'CHA₂DS₂-VASc 评分', type: 'number', min: 0, max: 9 },
      { key: 'baseline_ldl', label: '基线 LDL-C', type: 'number', unit: 'mmol/L', min: 0 },
    ],
  },
  {
    title: '合并症',
    desc: '既往病史与共病情况',
    fields: [
      { key: 'diabetes', label: '2 型糖尿病', type: 'boolean' },
      { key: 'ckd', label: 'CKD 慢性肾脏病', type: 'boolean' },
      { key: 'af', label: '房颤', type: 'boolean' },
      { key: 'hf', label: '心衰', type: 'boolean' },
      { key: 'lvef_reduced', label: 'LVEF 降低', type: 'boolean' },
      { key: 'asthma_copd', label: '哮喘 / COPD', type: 'boolean' },
      { key: 'gout_history', label: '痛风史', type: 'boolean' },
      { key: 'stroke_tia_history', label: '缺血性卒中 / TIA 史', type: 'boolean' },
      { key: 'prior_mi_stroke', label: '既往心梗 / 卒中史', type: 'boolean' },
      { key: 'multivessel', label: '多支病变', type: 'boolean' },
      { key: 'bp_high', label: '规范服药下血压 ≥140/90', type: 'boolean' },
    ],
  },
  {
    title: '当前用药',
    desc: '正在服用 / 不耐受 / 禁忌的药物',
    fields: [
      { key: 'on_clopidogrel', label: '正在用氯吡格雷', type: 'boolean' },
      { key: 'on_ticagrelor', label: '正在用替格瑞洛', type: 'boolean' },
      { key: 'on_noac', label: '正在用 NOAC 抗凝', type: 'boolean' },
      { key: 'noac_type', label: 'NOAC 品种', type: 'select', options: ['利伐沙班', '达比加群', '阿哌沙班'] },
      { key: 'aspirin_intolerant', label: '阿司匹林过敏 / 不耐受', type: 'boolean' },
      { key: 'ticagrelor_intolerant', label: '替格瑞洛不耐受 / 禁忌', type: 'boolean' },
      { key: 'cyp2c19_loss', label: '氯吡格雷抵抗（CYP2C19 缺失）', type: 'boolean' },
      { key: 'on_metformin', label: '正在用二甲双胍', type: 'boolean' },
      { key: 'on_amiodarone', label: '长期用胺碘酮', type: 'boolean' },
      { key: 'on_nitrate', label: '正在用硝酸酯', type: 'boolean' },
      { key: 'on_pde5i', label: '正在用 PDE5 抑制剂', type: 'boolean' },
      { key: 'on_nsaid_steroid', label: '同用 NSAIDs / 激素', type: 'boolean' },
      { key: 'ppi', label: 'PPI 品种', type: 'select', options: ['奥美拉唑', '艾司奥美拉唑', '泮托拉唑', '雷贝拉唑', '其他'] },
      { key: 'beta_blocker_contra', label: 'β 阻滞剂禁忌', type: 'boolean' },
      { key: 'acei_contra', label: 'ACEI 禁忌', type: 'boolean' },
    ],
  },
  {
    title: '症状与用药行为',
    desc: '红旗症状、出血征象、漏服停药等',
    fields: [
      { key: 'red_flag', label: '红旗症状（再发胸痛/黑便呕血/晕厥/活动耐量明显下降）', type: 'boolean' },
      { key: 'mild_bleed', label: '轻微出血（牙龈/瘀斑，无 Hb 下降）', type: 'boolean' },
      { key: 'recent_fatal_bleed', label: '近期致命性出血', type: 'boolean' },
      { key: 'ich_history', label: '颅内出血史', type: 'boolean' },
      { key: 'ulcer_bleed_history', label: '消化道溃疡 / 出血史', type: 'boolean' },
      { key: 'want_stop_antiplatelet', label: '患者拟停抗血小板药', type: 'boolean' },
      { key: 'miss_single_dose', label: '单次漏服抗血小板/他汀', type: 'boolean' },
      { key: 'self_stop_days', label: '自行停药天数', type: 'number', unit: '天', min: 0 },
      { key: 'blood_activating', label: '自服活血中成药/鱼油/纳豆激酶', type: 'boolean' },
      { key: 'need_analgesic', label: '需用镇痛药', type: 'boolean' },
      { key: 'enhance_ct', label: '拟行增强 CT / 造影', type: 'boolean' },
      { key: 'alt_ast_ratio', label: 'ALT/AST（正常上限倍数）', type: 'number', min: 0 },
      { key: 'ck_ratio', label: 'CK（正常上限倍数）', type: 'number', min: 0 },
      { key: 'referral_plan_confirmed', label: '上级方案下转已确认', type: 'boolean' },
      { key: 'recent_symptom_after_referral', label: '下转后 1 个月内再发症状', type: 'boolean' },
    ],
  },
]

// ============ 表单状态 ============
const form = reactive({})
for (const s of steps) {
  for (const f of s.fields) {
    form[f.key] = f.type === 'boolean' ? false : null
  }
}

const currentStep = ref(0)
const loading = ref(false)
const result = ref(null)
const errorMsg = ref('')

// ============ 提交流程 ============
function buildPayload() {
  const payload = {}
  for (const s of steps) {
    for (const f of s.fields) {
      const v = form[f.key]
      if (f.type === 'number') {
        if (v === null || v === undefined || v === '') continue
        payload[f.key] = Number(v)
      } else if (f.type === 'boolean') {
        if (v === true) payload[f.key] = true
      } else if (f.type === 'date') {
        if (v) payload[f.key] = v
      } else {
        if (v) payload[f.key] = v
      }
    }
  }
  return payload
}

async function submit() {
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
    result.value = await resp.json()
  } catch (e) {
    errorMsg.value = '调用后端失败：' + e.message + '。请确认 uvicorn 已在 backend 目录启动。'
  } finally {
    loading.value = false
  }
}

function reset() {
  for (const s of steps) {
    for (const f of s.fields) {
      form[f.key] = f.type === 'boolean' ? false : null
    }
  }
  currentStep.value = 0
  result.value = null
  errorMsg.value = ''
}

const tagText = { tag_br: '高出血风险', tag_ir: '高缺血风险', tag_el: '老年(≥75)' }
const activeTags = computed(() => {
  if (!result.value || !result.value.tags) return []
  return Object.entries(result.value.tags).filter(([, v]) => v).map(([k]) => tagText[k])
})
</script>

<template>
  <div class="wrap">
    <header class="head">
      <h1>PCI 术后用药管理助手</h1>
      <p>基于分级诊疗指南的规则引擎 · 零自由发挥 · 每一条建议可溯源</p>
    </header>

    <template v-if="!result && !errorMsg">
      <el-steps :active="currentStep" finish-status="success" align-center class="steps">
        <el-step v-for="(s, i) in steps" :key="i" :title="s.title" :description="s.desc" />
      </el-steps>

      <el-card class="card" shadow="never">
        <h2 class="step-title">{{ steps[currentStep].title }}</h2>
        <el-form label-width="220px" label-position="left" class="form">
          <el-form-item v-for="f in steps[currentStep].fields" :key="f.key" :label="f.label">
            <el-switch v-if="f.type === 'boolean'" v-model="form[f.key]" active-text="是" inactive-text="否" />
            <el-input-number v-else-if="f.type === 'number'" v-model="form[f.key]" :min="f.min" :max="f.max" controls-position="right" style="width: 200px">
              <template #suffix v-if="f.unit">{{ f.unit }}</template>
            </el-input-number>
            <el-date-picker v-else-if="f.type === 'date'" v-model="form[f.key]" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 200px" />
            <el-select v-else-if="f.type === 'select'" v-model="form[f.key]" placeholder="请选择" clearable style="width: 200px">
              <el-option v-for="op in f.options" :key="op" :label="op" :value="op" />
            </el-select>
            <el-input v-else v-model="form[f.key]" :placeholder="f.placeholder || '选填'" style="width: 320px" />
          </el-form-item>
        </el-form>

        <div class="nav">
          <el-button v-if="currentStep > 0" @click="currentStep--">上一步</el-button>
          <el-button v-if="currentStep < steps.length - 1" type="primary" @click="currentStep++">下一步</el-button>
          <el-button v-else type="success" :loading="loading" @click="submit">提交分析</el-button>
        </div>
      </el-card>
    </template>

    <template v-else-if="errorMsg">
      <el-alert :title="errorMsg" type="error" show-icon :closable="false" class="alert" />
      <div class="nav"><el-button type="primary" @click="reset">返回重填</el-button></div>
    </template>

    <template v-else>
      <div class="result">
        <div class="tags" v-if="activeTags.length">
          <el-tag v-for="t in activeTags" :key="t" type="warning" effect="plain" class="tag">{{ t }}</el-tag>
        </div>

        <div v-if="result.redlines && result.redlines.length">
          <el-alert v-for="r in result.redlines" :key="r.id" type="error" :closable="false" class="alert">
            <template #title>
              【红线 {{ r.id }}】{{ r.name }}
            </template>
            {{ r.action }}
          </el-alert>
        </div>

        <div v-else class="advice">
          <template v-if="result.advices && result.advices.length">
            <div class="advice-item" v-for="a in result.advices" :key="a.id">
              <div class="advice-head">
                <span class="advice-id">{{ a.id }}</span>
                <el-tag :type="a.level === '审核级' ? 'warning' : 'success'" size="small">{{ a.level }}</el-tag>
              </div>
              <p class="advice-text">{{ a.action }}</p>
              <p class="advice-src">出处：{{ a.source }}</p>
            </div>
          </template>
          <el-empty v-else description="未命中任何规则，请核对录入信息" />
        </div>

        <p class="disclaimer">{{ result.disclaimer }}</p>
        <div class="nav"><el-button type="primary" @click="reset">重新填写</el-button></div>
      </div>
    </template>
  </div>
</template>

<style>
body { margin: 0; background: #f5f7fa; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
.wrap { max-width: 860px; margin: 0 auto; padding: 24px 16px 60px; }
.head { text-align: center; margin-bottom: 20px; }
.head h1 { margin: 0 0 8px; color: #1f2f3d; }
.head p { margin: 0; color: #8492a6; font-size: 14px; }
.steps { margin-bottom: 20px; }
.card { border-radius: 8px; }
.step-title { margin: 0 0 16px; font-size: 18px; color: #1f2f3d; }
.form { margin-top: 4px; }
.nav { display: flex; justify-content: center; gap: 12px; margin-top: 20px; }
.alert { margin-bottom: 12px; }
.tags { margin-bottom: 14px; }
.tag { margin-right: 8px; }
.advice-item { background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }
.advice-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.advice-id { font-weight: 700; color: #409eff; }
.advice-text { margin: 0 0 6px; color: #303133; line-height: 1.6; }
.advice-src { margin: 0; color: #909399; font-size: 12px; }
.disclaimer { color: #c0c4cc; font-size: 12px; text-align: center; margin: 20px 0 8px; }
</style>