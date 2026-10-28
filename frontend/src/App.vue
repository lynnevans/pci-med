<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { Document, RefreshLeft, FirstAidKit, WarningFilled, InfoFilled } from '@element-plus/icons-vue'
const view = ref<'form' | 'chat'>('form')

// ===== 数据结构定义 =====
const basicFields = [
  { key: 'age', label: '年龄 (岁)' },
  { key: 'sex', label: '性别', type: 'select', options: ['男', '女'], required: true },   //性别换成下拉
  { key: 'weight', label: '体重 (kg)' },
  { key: 'surgery_date', label: '手术日期 (如 2023-01-01)' },
  { key: 'post_pci_months', label: '术后时长 (月)' },
  { key: 'diagnosis', label: '出院诊断' },
  { key: 'vessels', label: '病变支数' },
  { key: 'target_vessel', label: '干预血管' },
  { key: 'dcb_count', label: 'DCB 数量 (个)' },
  { key: 'brs_count', label: 'BRS 数量 (枚)' },
  { key: 'des_count', label: 'DES 数量 (枚)' },
  { key: 'ascvd_risk', label: 'ASCVD 危险分层' },
  { key: 'discharge_plan', label: '出院抗栓方案' },
]

// 【修改 historyFields】
const historyFields = [
  // 高血压换成 options
  { key: 'hypertension_grade', label: '高血压分级', options: ['1级', '2级', '3级'] },
  // multi: true 代表可以多选
  { key: 'comorbidities', label: '其他合并症', multi: true, options: ['无', '糖尿病', '高脂血症', '房颤', '心衰', 'COPD', '哮喘', 'CKD'] },
  { key: 'cha2ds2_vasc', label: 'CHA2DS2-VASc 评分', placeholder: '例如：3' },
  { key: 'has_bled', label: 'HAS-BLED 评分', placeholder: '例如：2' },
  { key: 'precis_dapt', label: 'PRECISE-DAPT 评分', placeholder: '例如：15' },
  // 原来是输入框，改成选项
  { key: 'cv_history', label: '心脑血管既往史', multi: true, options: ['既往心梗史', '既往卒中/TIA史'] },
  { key: 'other_history', label: '其他相关既往史（选填）', placeholder: '选填' },
]


// 【新增 examCards 替换原来的 examFields】
const examCards = [
  {
    name: '血常规', items: 'Hb / WBC / PLT', fields: [
      { key: 'hb_low', label: '血红蛋白降低', type: 'bool' }, // 这个用开关
      { key: 'plt_status', label: '血小板', type: 'status', options: ['正常', '降低'] }, // 小胶囊
    ]
  },
  {
    name: '肝功能', items: 'ALT / AST', fields: [
      { key: 'alt_ast_status', label: 'ALT/AST', type: 'status', options: ['正常', '轻度升高', '重度升高'] },
    ]
  },
  {
    name: '肾功能', items: '肌酐 / eGFR', fields: [
      { key: 'scr', label: '血肌酐 Scr', type: 'number', unit: 'μmol/L' }, // 数字框
      { key: 'egfr', label: 'eGFR', type: 'number', unit: 'ml/min' },
    ]
  },
  {
    name: '超声心动图', items: 'EF / 室壁运动', fields: [
      { key: 'lvef', label: 'LVEF', type: 'number', unit: '%' },
    ]
  },
]

// 用药加上剂量
const medFields = [
  { key: 'aspirin', label: '阿司匹林', unit: 'mg' },
  { key: 'clopidogrel', label: '氯吡格雷', unit: 'mg' },
  { key: 'ticagrelor', label: '替格瑞洛', unit: 'mg' },
  { key: 'noac', label: '口服抗凝药', unit: 'mg' },
  { key: 'beta_blocker', label: 'β受体阻滞剂', unit: 'mg' },
  { key: 'arni', label: 'ARNI/ACEI/ARB', unit: 'mg' },
  { key: 'ppi', label: 'PPI类药物', unit: 'mg' },
  { key: 'lipid', label: '降脂类药物', unit: 'mg' },
  { key: 'glucose', label: '降糖类药物', unit: 'mg' },
]


// 【修改 symptomFields】
const symptomFields = [
  { key: 'symptoms', label: '症状表现', multi: true, options: ['胸痛', '胸闷气短', '晕厥', '活动耐量下降'] },
  // 把出血征象里危险的选项加上 dangerOptions
  {
    key: 'bleeding', label: '出血征象', multi: true,
    options: ['淤青', '牙龈出血', '呕血', '尿血', '黑便'],
    dangerOptions: ['呕血', '尿血', '黑便'] // 这一项是为了变红
  },
  { key: 'self_stop_days', label: '自行停药天数', unit: '天', placeholder: '未停药请填 0' },
  { key: 'blood_activating', label: '是否自服活血药', options: ['否', '是'] }, // 改成选项
]

// 更新 steps 数组，把第三步指向新的 examCards
const steps = [
  { title: '基本信息', fields: basicFields },
  { title: '病史与合并症', fields: historyFields },
  { title: '辅助检查', isExamGrid: true }, // 这里加个标记，告诉 template 特殊渲染
  { title: '当前用药', fields: medFields },
  { title: '症状与行为', fields: symptomFields },
]

// ===== 状态 =====
const currentStep = ref(0)
const loading = ref(false)
const form = reactive<Record<string, string>>({})
const result = ref<any>(null)
const errorMsg = ref('')


// 初始化空表单
for (const step of steps) {
  if (step.fields) {
    for (const f of step.fields) {
      // 如果是多选，初始给个空数组，其他给空字符串
      form[f.key] = f.multi ? [] : ''
    }
  }
}
// 给卡片里的字段赋初值
for (const c of examCards) {
  for (const f of c.fields) {
    if (f.type === 'bool') form[f.key] = false
    else if (f.type === 'status') form[f.key] = '正常'
    else form[f.key] = null
  }
}

// 初始化表单时，给每个药加一个“未使用”的状态
for (const f of medFields) {
  form[f.key] = '' // 剂量
  form[`${f.key}_unused`] = false // 是否未使用
}


// ===== 提交逻辑 =====
//必填项
// 修改为：
const currentStepFields = computed(() => steps[currentStep.value].fields || [])

function nextStep() {
  const emptyRequired = currentStepFields.value.find(f => f.required && !form[f.key])
  if (emptyRequired) {
    alert(`请填写必填项：${emptyRequired.label}`) // 这里先用原生弹窗
    return
  }
  currentStep.value++
}

// 将输入框的字符串转为后端需要的格式（处理数字、布尔、多选）
function buildPayload() {
  const p: Record<string, any> = {}

  for (const key in form) {
    let val = form[key]
    // 如果是多选数组，直接赋值给后端，跳过 trim 处理
    if (Array.isArray(val)) {
      if (val.length > 0) p[key] = val
      continue
    }

    if (!val) continue
    val = val.trim()
    if (!val) continue

    // 处理布尔值 (是/否)
    if (val === '是') p[key] = true
    else if (val === '否') p[key] = false
    // 处理纯数字
    else if (!isNaN(Number(val))) p[key] = Number(val)
    // 处理带逗号的字符串（如多选）
    else if (val.includes(',')) p[key] = val.split(',').map(s => s.trim())
    // 直接赋值
    else p[key] = val
  }

  // 兼容后端的特殊字段映射（简单转换几个关键的）
  if (p['diagnosis']) {
    const d = p['diagnosis']
    if (d.includes('心梗') || d.includes('心绞痛')) {
      p['scenario'] = d.includes('ST段') || d.includes('不稳定') ? 'ACS' : 'CCS'
    }
  }

  return p
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
  } catch (e: any) {
    errorMsg.value = '调用失败：' + e.message
  } finally {
    loading.value = false
  }
}

function reset() {
  currentStep.value = 0
  result.value = null
  errorMsg.value = ''
  for (const key in form) form[key] = ''
}
</script>

<template>
  <div class="page">
    <header class="brand">
      <div class="brand-icon"><el-icon :size="30">
          <FirstAidKit />
        </el-icon></div>
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


    <!-- 填表区 -->
    <template v-if="!result && !errorMsg">
      <el-card class="panel" shadow="never">
        <el-steps :active="currentStep" finish-status="success" align-center class="steps">
          <el-step v-for="(s, i) in steps" :key="i" :title="s.title" />
        </el-steps>
      </el-card>

      <el-card class="panel" shadow="never">
        <div class="form-head">
          <h2>{{ steps[currentStep].title }}</h2>
        </div>

        <!-- ================= 1. 普通表单页 (非第三步) ================= -->
        <el-form v-if="currentStep !== 2" label-width="170px" label-position="left">
          <el-form-item v-for="f in steps[currentStep].fields" :key="f.key">
            <template #label>
              <span v-if="f.required" class="req">*</span> {{ f.label }}
            </template>
            <!-- ======= 新增：第4步（用药剂量单位） ======= -->
            <div v-if="currentStep === 3" class="med-row-wrap">
              <el-checkbox v-model="form[`${f.key}_unused`]" @change="form[f.key] = ''"
                style="margin-right: 15px;">未使用此药</el-checkbox>
              <el-input v-model="form[f.key]" :disabled="form[`${f.key}_unused`]"
                :placeholder="form[`${f.key}_unused`] ? '已停用' : '请输入剂量'" style="width: 200px;">
                <template v-if="f.unit" #append>{{ f.unit }}</template>
              </el-input>
            </div>

            <!-- ======= 其他步骤保持原样（胶囊或输入框） ======= -->
            <div v-else class="field-wrap">
              <div v-if="f.options" class="option-group">
                <label v-for="op in f.options" :key="op" class="opt"
                  :class="{ danger: f.dangerOptions && f.dangerOptions.includes(op) }">
                  <input :type="f.multi ? 'checkbox' : 'radio'" :name="f.key" :value="op" v-model="form[f.key]" />
                  <span>{{ op }}</span>
                </label>
              </div>
              <el-input v-else v-model="form[f.key]" :placeholder="f.placeholder || '请输入'" clearable>
                <template v-if="f.unit" #append>{{ f.unit }}</template>
              </el-input>
            </div>
          </el-form-item>
        </el-form>

        <!-- ================= 2. 第三步：辅助检查卡片 ================= -->
        <div v-if="currentStep === 2" class="exam-grid">
          <div v-for="c in examCards" :key="c.name" class="exam-card">
            <div class="exam-head">
              <div>
                <div class="exam-title">{{ c.name }}</div>
                <div class="exam-items">{{ c.items }}</div>
              </div>
            </div>
            <div class="exam-body">
              <div v-for="f in c.fields" :key="f.key" class="exam-field">
                <span class="exam-label">{{ f.label }}</span>

                <!-- 开关 -->
                <el-switch v-if="f.type === 'bool'" v-model="form[f.key]" />

                <!-- 小胶囊 -->
                <div v-else-if="f.type === 'status'" class="option-group">
                  <label v-for="op in f.options" :key="op" class="opt opt-sm">
                    <input type="radio" :name="f.key" :value="op" v-model="form[f.key]" />
                    <span>{{ op }}</span>
                  </label>
                </div>

                <!-- 数字框 -->
                <el-input-number v-else v-model="form[f.key]" :min="0" controls-position="right" class="ctrl-sm">
                  <template #suffix v-if="f.unit">{{ f.unit }}</template>
                </el-input-number>
              </div>
            </div>
          </div>
        </div>

        <!-- ================= 3. 底部按钮 ================= -->
        <div class="nav">
          <el-button v-if="currentStep > 0" size="large" @click="currentStep--">上一步</el-button>
          <el-button v-if="currentStep < steps.length - 1" type="primary" size="large" @click="nextStep">下一步</el-button>
          <el-button v-else type="primary" size="large" :loading="loading" @click="submit">提交分析</el-button>
        </div>
        <p class="hint"><span class="req">*</span> 为核心字段，其余按实际可获取情况选填</p>
      </el-card>
    </template>

    <!-- 错误区 -->
    <template v-else-if="errorMsg">
      <el-card class="panel" shadow="never">
        <el-alert :title="errorMsg" type="error" show-icon :closable="false" />
        <div class="nav"><el-button type="primary" @click="reset">返回重填</el-button></div>
      </el-card>
    </template>

    <!-- 结果区 -->
    <template v-else>
      <el-card class="panel" shadow="never">
        <div class="result-head">
          <h2>分析结果</h2>
        </div>

        <div v-if="result.redlines?.length">
          <div v-for="r in result.redlines" :key="r.id" class="redline-item">
            <strong><el-icon>
                <WarningFilled />
              </el-icon> 【红线】{{ r.name }}</strong>
            <p>{{ r.action }}</p>
          </div>
        </div>
        <div v-else>
          <div v-for="a in result.advices" :key="a.id" class="advice-item">
            <strong>[{{ a.level }}] {{ a.id }}</strong>
            <p>{{ a.action }}</p>
          </div>
          <el-empty v-if="!result.advices?.length" description="未命中规则" />
        </div>

        <p class="disclaimer"><el-icon>
            <InfoFilled />
          </el-icon> {{ result.disclaimer }}</p>

        <div class="nav">
          <el-button type="primary" @click="reset">
            <el-icon class="btn-icon">
              <RefreshLeft />
            </el-icon>重新填写
          </el-button>
        </div>
      </el-card>
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

body {
  margin: 0;
  background: var(--bg);
  font-family: -apple-system,
  "PingFang SC", 
  "Microsoft YaHei", 
  "Helvetica Neue", 
  sans-serif;
}

* {
  box-sizing: border-box;
}



.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 28px 18px 70px;
}

/* ===== 品牌区 ===== */

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
}

.brand-icon {
  width: 50px;
  height: 50px;
  border-radius: 14px; 
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(3, 105, 161, 0.25);
}

.brand-text h1 {
  margin: 0 0 6px;
  font-size: 24px;
  color: var(--text); 
  letter-spacing: 0.5px;
}

.brand-text p {
  margin: 0;
  color: var(--text-2); 
  font-size: 13.5px;
}

.brand-tag {
  margin-left: auto; 
  flex-shrink: 0; 
  font-size: 12px; 
  padding: 5px 12px;
  border-radius: 20px;
  background: rgba(3, 105, 161, 0.08); 
  color: var(--primary); 
  border: 1px solid rgba(3, 105, 161, 0.2);
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