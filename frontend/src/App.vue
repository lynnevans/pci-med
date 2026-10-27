<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Document, RefreshLeft, FirstAidKit, WarningFilled, InfoFilled } from '@element-plus/icons-vue'

// ===== 极简数据结构定义 =====
const basicFields = [
  { key: 'age', label: '年龄 (岁)' },
  { key: 'sex', label: '性别' },
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

const historyFields = [
  { key: 'hypertension_grade', label: '高血压分级' },
  { key: 'comorbidities', label: '其他合并症' },
  { key: 'cha2ds2_vasc', label: 'CHA2DS2-VASc 评分' },
  { key: 'has_bled', label: 'HAS-BLED 评分' },
  { key: 'precis_dapt', label: 'PRECISE-DAPT 评分' },
  { key: 'cv_history', label: '心脑血管既往史' },
  { key: 'other_history', label: '其他相关既往史' },
]

const examFields = [
  { key: 'hb_low', label: '血红蛋白是否降低 (填 是/否)' },
  { key: 'plt_status', label: '血小板状态' },
  { key: 'alt_ast_status', label: 'ALT/AST 状态' },
  { key: 'scr', label: '血肌酐 Scr' },
  { key: 'egfr', label: 'eGFR' },
  { key: 'lvef', label: 'LVEF (%)' },
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

const symptomFields = [
  { key: 'symptoms', label: '症状表现' },
  { key: 'bleeding', label: '出血征象' },
  { key: 'self_stop_days', label: '自行停药天数' },
  { key: 'blood_activating', label: '是否自服活血药 (填 是/否)' },
]

const steps = [
  { title: '基本信息', fields: basicFields },
  { title: '病史与合并症', fields: historyFields },
  { title: '辅助检查', fields: examFields },
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
  for (const f of step.fields) {
    form[f.key] = ''
  }
}

// ===== 提交逻辑 =====
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

        <el-form label-width="200px" label-position="left">
          <el-form-item v-for="f in steps[currentStep].fields" :key="f.key" :label="f.label">
            <el-input v-model="form[f.key]" placeholder="请输入..." clearable />
          </el-form-item>
        </el-form>

        <div class="nav">
          <el-button v-if="currentStep > 0" size="large" @click="currentStep--">上一步</el-button>
          <el-button v-if="currentStep < steps.length - 1" type="primary" size="large" @click="currentStep++">下一步</el-button>
          <el-button v-else type="primary" size="large" :loading="loading" @click="submit">
            <el-icon class="btn-icon"><Document /></el-icon>提交分析
          </el-button>
        </div>
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
</style>