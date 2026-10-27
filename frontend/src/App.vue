<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { Document, RefreshLeft, FirstAidKit, WarningFilled, InfoFilled } from '@element-plus/icons-vue'

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
  { name: '血常规', items: 'Hb / WBC / PLT', fields: [
    { key: 'hb_low', label: '血红蛋白降低', type: 'bool' }, // 这个用开关
    { key: 'plt_status', label: '血小板', type: 'status', options: ['正常', '降低'] }, // 小胶囊
  ]},
  { name: '肝功能', items: 'ALT / AST', fields: [
    { key: 'alt_ast_status', label: 'ALT/AST', type: 'status', options: ['正常', '轻度升高', '重度升高'] },
  ]},
  { name: '肾功能', items: '肌酐 / eGFR', fields: [
    { key: 'scr', label: '血肌酐 Scr', type: 'number', unit: 'μmol/L' }, // 数字框
    { key: 'egfr', label: 'eGFR', type: 'number', unit: 'ml/min' },
  ]},
  { name: '超声心动图', items: 'EF / 室壁运动', fields: [
    { key: 'lvef', label: 'LVEF', type: 'number', unit: '%' },
  ]},
]

const medFields = [
  { key: 'aspirin', label: '阿司匹林当前剂量' },
  { key: 'clopidogrel', label: '氯吡格雷当前剂量' },
  { key: 'ticagrelor', label: '替格瑞洛当前剂量' },
  { key: 'noac', label: '口服抗凝药' },
  { key: 'beta_blocker', label: 'β受体阻滞剂' },
  { key: 'arni', label: 'ARNI/ACEI/ARB' },
  { key: 'ppi', label: 'PPI类药物' },
  { key: 'lipid', label: '降脂类药物' },
  { key: 'glucose', label: '降糖类药物' },
]

// 【修改 symptomFields】
const symptomFields = [
  { key: 'symptoms', label: '症状表现', multi: true, options: ['胸痛', '胸闷气短', '晕厥', '活动耐量下降'] },
  // 把出血征象里危险的选项加上 dangerOptions
  { key: 'bleeding', label: '出血征象', multi: true, 
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
    else form[f.key] = ''
  }
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
    let val = form[key].trim()
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
      <div class="brand-icon"><el-icon :size="30"><FirstAidKit /></el-icon></div>
      <div class="brand-text">
        <h1>PCI 术后用药管理助手 (2.0版)</h1>
        <p>初版测试，所有字段文本输入</p>
      </div>
    </header>

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

            <div class="field-wrap">
              <!-- 有 options 渲染胶囊按钮 -->
              <div v-if="f.options" class="option-group">
                <label v-for="op in f.options" :key="op" class="opt" 
                :class="{ danger: f.dangerOptions && f.dangerOptions.includes(op) }">
                  <input :type="f.multi ? 'checkbox' : 'radio'" 
                  :name="f.key" :value="op" 
                  v-model="form[f.key]" />
                  <span>{{ op }}</span>
                </label>
              </div>

              <!-- 没有 options 渲染输入框 -->
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

        <!-- ================= 3. 底部悬浮按钮 ================= -->
        <div class="floating-nav">
          <el-button v-if="currentStep > 0" size="large" @click="currentStep--">上一步</el-button>
          <el-button v-if="currentStep < steps.length - 1" type="primary" size="large" @click="nextStep">下一步</el-button>
          <el-button v-else type="primary" size="large" :loading="loading" @click="submit">
            <el-icon class="btn-icon"><Document /></el-icon>提交分析
          </el-button>
        </div>
        <div class="spacer"></div>
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
            <strong><el-icon><WarningFilled /></el-icon> 【红线】{{ r.name }}</strong>
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

        <p class="disclaimer"><el-icon><InfoFilled /></el-icon> {{ result.disclaimer }}</p>
        
        <div class="nav">
          <el-button type="primary" @click="reset">
            <el-icon class="btn-icon"><RefreshLeft /></el-icon>重新填写
          </el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style>
:root {
  --primary: #0369a1;
  --danger: #dc2626;
  --bg: #f6f8fa;
  --card: #fff;
}
body { margin: 0; background: var(--bg); font-family: sans-serif; }
* { box-sizing: border-box; }
.page { max-width: 800px; margin: 0 auto; padding: 28px 18px; }

.brand { display: flex; align-items: center; gap: 16px; margin-bottom: 22px; }
.brand-icon { width: 50px; height: 50px; background: var(--primary); color: #fff; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.brand-text h1 { margin: 0 0 4px; font-size: 20px; color: #333; }
.brand-text p { margin: 0; color: #666; font-size: 13px; }

.panel { border-radius: 12px; margin-bottom: 18px; }
.panel :deep(.el-card__body) { padding: 24px; }
.form-head { border-bottom: 1px solid #eee; padding-bottom: 12px; margin-bottom: 20px; }
.form-head h2 { margin: 0; font-size: 18px; color: #333; }
.nav { display: flex; justify-content: center; gap: 12px; margin-top: 24px; }
.btn-icon { margin-right: 4px; }

.result-head { border-bottom: 1px solid #eee; padding-bottom: 12px; margin-bottom: 16px; }
.result-head h2 { margin: 0; font-size: 18px; }
.redline-item { background: #fef2f2; border-left: 4px solid var(--danger); padding: 12px; margin-bottom: 12px; border-radius: 6px; }
.advice-item { border-left: 4px solid var(--primary); padding: 12px; margin-bottom: 12px; background: #f8fafc; border-radius: 6px; }
.disclaimer { font-size: 12px; color: #999; text-align: center; margin-top: 20px; }

/* 必填项红星 */
.req { color: var(--danger); margin-right: 4px; font-weight: bold; }

/* 底部悬浮按钮的样式 */
.floating-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  padding: 15px;
  display: flex;
  justify-content: center;
  gap: 12px;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
  z-index: 100;
}


/* ===== 胶囊按钮样式 ===== */
.option-group { display: flex; flex-wrap: wrap; gap: 9px; }
.opt { position: relative; }
.opt input { position: absolute; opacity: 0; pointer-events: none; }
.opt span {
  display: inline-block; padding: 8px 17px; border: 1px solid #e2e8f0;
  border-radius: 9px; font-size: 13.5px; color: #475569; cursor: pointer;
  background: #fff; transition: all 0.15s; user-select: none;
}
.opt:hover span { border-color: var(--primary); }
.opt input:checked + span { 
  background: #f0f7fb; border-color: var(--primary); 
  color: var(--primary); font-weight: 600; 
}
.opt input:checked + span::after { content: ' ✓'; }
.opt.danger span { color: var(--danger); border-color: #fecaca; }
.opt.danger input:checked + span { background: #fef2f2; border-color: var(--danger); color: var(--danger); }
.opt-sm span { padding: 5px 12px; font-size: 12.5px; }

/* ===== 辅助检查卡片网格样式 ===== */
.exam-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.exam-card { border: 1px solid #e2e8f0; border-radius: 11px; padding: 14px 15px; background: #fff; }
.exam-head { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px dashed #e2e8f0; padding-bottom: 10px; margin-bottom: 10px; }
.exam-title { font-size: 15px; font-weight: 600; color: #333; }
.exam-items { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.exam-body { display: flex; flex-direction: column; gap: 10px; }
.exam-field { display: flex; align-items: center; justify-content: space-between; }
.exam-label { font-size: 13px; color: #475569; }
.ctrl-sm { width: 130px; }

/* 防止最后面几个输入框被悬浮按钮遮挡 */
.spacer { height: 80px; }
</style>