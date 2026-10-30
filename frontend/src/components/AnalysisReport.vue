<script setup lang="ts">
import { computed } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'
import ReportItemCard from './ReportItemCard.vue'

interface ReportItem {
  id: string
  ref?: string
  conclusion: string
  evidence: string
  impact: string
  action: string
  timeframe: string
  source: string
  severity?: string
  level?: string
  priority?: number
  [key: string]: any
}

interface ReportData {
  summary: {
    basic: string
    surgery: string
    diagnosis: string
    comorbidity_count: number
    core_completed: number
    core_total: number
    exam_completed: number
    exam_total: number
    portrait: string
    risk_level: string
    risk_label: string
    counts: { critical: number; attention: number; medication: number; behavior: number }
    tags: string[]
  }
  comorbidity: { name: string; status: string; association: string; source: string }[]
  exam_critical: ReportItem[]
  exam_attention: ReportItem[]
  exam_normal: { count: number; text: string; items: { name: string; value: string }[] }
  exam_gap: { missing: string; impact: string; action: string; timeframe: string }[]
  medication_gap: { summary: string; items: ReportItem[] }
  drug_disease: { items: ReportItem[]; synergy: ReportItem[] }
  adjust_plan: ReportItem[]
  symptom_behavior: { symptoms: ReportItem[]; behavior: ReportItem[]; confirmation: string }
  action_plan: {
    summary: string
    levels: { key: string; title: string; items: { number: string; conclusion: string; action: string; timeframe: string; ref: string }[] }[]
  }
  followup: {
    schedule: { item: string; timing: string; purpose: string; source: string }[]
    referral: string[]
    referral_note: string
  }
  references: {
    sources: { code: string; name: string; rules: string[] }[]
    terms: { abbr: string; full: string }[]
    disclaimer: string
  }
}

const props = defineProps<{ report: ReportData }>()
const tagText: Record<string, string> = { tag_br: '高出血风险', tag_ir: '高缺血风险', tag_el: '老年（≥75）' }
const activeTags = computed(() => props.report.summary.tags.map((tag) => tagText[tag] ?? tag))
</script>

<template>
  <div class="analysis-report">
    <div class="result-head">
      <div>
        <p class="report-kicker">PCI 术后复诊 · 结构化分析报告</p>
        <h2>分析结果报告</h2>
      </div>
      <div class="report-head-tags">
        <span :class="['report-risk', `report-risk-${report.summary.risk_level}`]">{{ report.summary.risk_label }}</span>
        <span v-for="tag in activeTags" :key="tag" class="tag-chip">{{ tag }}</span>
      </div>
    </div>

    <section class="report-section">
      <div class="report-section-head"><span>01</span><h3>患者概要</h3></div>
      <div class="summary-grid">
        <div><span>基本情况</span><strong>{{ report.summary.basic }}</strong></div>
        <div><span>出院诊断</span><strong>{{ report.summary.diagnosis }}</strong></div>
        <div class="summary-wide"><span>手术信息</span><strong>{{ report.summary.surgery }}</strong></div>
        <div><span>合并症数量</span><strong>{{ report.summary.comorbidity_count }} 项（详见第二部分）</strong></div>
        <div><span>数据完整度</span><strong>核心字段 {{ report.summary.core_completed }}/{{ report.summary.core_total }}；辅助检查已录 {{ report.summary.exam_completed }}/{{ report.summary.exam_total }} 项</strong></div>
      </div>
      <div :class="['clinical-portrait', `portrait-${report.summary.risk_level}`]">
        <strong>临床画像</strong><p>{{ report.summary.portrait }}</p>
      </div>
    </section>

    <section class="report-section">
      <div class="report-section-head"><span>02</span><h3>合并症与既往史</h3></div>
      <div v-if="report.comorbidity.length" class="report-table-wrap">
        <table class="report-table">
          <thead><tr><th>合并症/既往史</th><th>现状与控制情况</th><th>与本次用药的关联提示</th><th>依据</th></tr></thead>
          <tbody><tr v-for="row in report.comorbidity" :key="row.name"><td><strong>{{ row.name }}</strong></td><td>{{ row.status }}</td><td>{{ row.association }}</td><td class="table-source">{{ row.source }}</td></tr></tbody>
        </table>
      </div>
      <p v-else class="report-empty success">未报告合并症或既往史；本部分不作额外疾病推定。</p>
    </section>

    <section class="report-section">
      <div class="report-section-head"><span>03</span><h3>检查指标评估</h3></div>
      <h4 class="report-subtitle danger">5.1 危急值</h4>
      <ReportItemCard v-for="item in report.exam_critical" :key="item.ref" :item="item" />
      <p v-if="!report.exam_critical.length" class="report-empty success">已录入指标未触发危急值阈值。</p>

      <h4 class="report-subtitle warning">5.2 需关注异常</h4>
      <ReportItemCard v-for="item in report.exam_attention" :key="item.ref" :item="item" />
      <p v-if="!report.exam_attention.length" class="report-empty">未识别需关注异常；未录入项目见信息缺口。</p>

      <el-collapse class="report-normal-collapse">
        <el-collapse-item name="normal">
          <template #title><span class="normal-title">5.3 正常指标确认（{{ report.exam_normal.count }} 项）</span></template>
          <p class="normal-confirmation">{{ report.exam_normal.text }}</p>
          <div v-if="report.exam_normal.items.length" class="normal-grid">
            <span v-for="item in report.exam_normal.items" :key="item.name">{{ item.name }}：<strong>{{ item.value }}</strong></span>
          </div>
        </el-collapse-item>
      </el-collapse>

      <h4 class="report-subtitle muted">5.4 信息缺口</h4>
      <div v-if="report.exam_gap.length" class="gap-list">
        <div v-for="gap in report.exam_gap" :key="gap.missing" class="gap-item">
          <strong>缺少{{ gap.missing }}</strong>
          <p>{{ gap.impact }}</p>
          <p>{{ gap.action }} <span>时限：{{ gap.timeframe }}</span></p>
        </div>
      </div>
      <p v-else class="report-empty">本次评估所需关键信息已录入。</p>
    </section>

    <section class="report-section">
      <div class="report-section-head"><span>04</span><h3>当前用药评估</h3></div>
      <h4 class="report-subtitle">6.1 冠心病二级预防方案完整性</h4>
      <div v-if="report.medication_gap.items.length" class="report-table-wrap">
        <table class="report-table">
          <thead><tr><th>评估项</th><th>患者现状</th><th>指南推荐</th><th>判定</th><th>动作与时限</th><th>依据</th></tr></thead>
          <tbody><tr v-for="row in report.medication_gap.items" :key="row.ref"><td><strong>{{ row.item }}</strong><small>{{ row.ref }}</small></td><td>{{ row.current }}</td><td>{{ row.recommendation }}</td><td><span :class="row.decision.includes('缺口') || row.decision.includes('未达标') ? 'text-warning' : 'text-success'">{{ row.decision }}</span></td><td>{{ row.action }}<small>{{ row.timeframe }}</small></td><td class="table-source">{{ row.source }}</td></tr></tbody>
        </table>
      </div>
      <p class="report-inline-summary">{{ report.medication_gap.summary }}</p>

      <h4 class="report-subtitle">6.2 药物与合并症的相互影响</h4>
      <ReportItemCard v-for="item in report.drug_disease.items" :key="item.ref" :item="item" />
      <p v-if="!report.drug_disease.items.length" class="report-empty">未识别需调整的药病冲突；未录入信息不作安全推定。</p>
      <el-collapse v-if="report.drug_disease.synergy.length" class="report-normal-collapse">
        <el-collapse-item :title="`协同与常规管理（${report.drug_disease.synergy.length} 项）`" name="synergy">
          <ReportItemCard v-for="item in report.drug_disease.synergy" :key="item.id" :item="item" />
        </el-collapse-item>
      </el-collapse>

      <h4 class="report-subtitle">6.3 用药调整建议清单</h4>
      <div v-if="report.adjust_plan.length" class="report-table-wrap">
        <table class="report-table adjust-table">
          <thead><tr><th>优先级</th><th>当前用药</th><th>建议调整</th><th>理由</th><th>时限</th><th>依据</th></tr></thead>
          <tbody><tr v-for="row in report.adjust_plan" :key="row.ref"><td><span class="priority-number">{{ row.priority_rank }}</span><small>{{ row.ref }}</small></td><td>{{ row.current_medication }}</td><td>{{ row.action }}</td><td>{{ row.reason }}<small>证据：{{ row.evidence }}</small></td><td>{{ row.timeframe }}</td><td class="table-source">{{ row.source }}</td></tr></tbody>
        </table>
      </div>
      <p v-else class="report-empty">本次无需新增加药、换药、停药或调量建议。</p>
    </section>

    <section class="report-section">
      <div class="report-section-head"><span>05</span><h3>症状与用药行为影响评估</h3></div>
      <h4 class="report-subtitle danger">7.1 症状评估</h4>
      <ReportItemCard v-for="item in report.symptom_behavior.symptoms" :key="item.ref" :item="item" />
      <p v-if="report.symptom_behavior.confirmation" class="report-empty success">{{ report.symptom_behavior.confirmation }}</p>
      <h4 class="report-subtitle">7.2 用药行为评估</h4>
      <ReportItemCard v-for="item in report.symptom_behavior.behavior" :key="item.ref" :item="item" />
      <p v-if="!report.symptom_behavior.behavior.length" class="report-empty success">未报告停药、漏服或其他高危用药行为。</p>
    </section>

    <section class="report-section action-section">
      <div class="report-section-head"><span>06</span><h3>综合结论与处理优先级</h3></div>
      <p class="action-summary">{{ report.action_plan.summary }}</p>
      <div v-for="level in report.action_plan.levels" :key="level.key" :class="['action-level', `action-${level.key}`]">
        <h4>{{ level.title }}<span>{{ level.items.length }} 条</span></h4>
        <div v-if="level.items.length" class="action-list">
          <div v-for="item in level.items" :key="item.number" class="action-row">
            <strong>{{ item.number }}</strong>
            <div><p>{{ item.conclusion }} <span>（见 {{ item.ref }}）</span></p><p>{{ item.action }}</p><small>{{ item.timeframe }}</small></div>
          </div>
        </div>
        <p v-else class="report-empty">本级别无待办事项。</p>
      </div>
    </section>

    <section class="report-section">
      <div class="report-section-head"><span>07</span><h3>随访与转诊建议</h3></div>
      <div v-if="report.followup.schedule.length" class="report-table-wrap">
        <table class="report-table">
          <thead><tr><th>复查项目</th><th>时间节点</th><th>目的</th><th>依据</th></tr></thead>
          <tbody><tr v-for="row in report.followup.schedule" :key="row.item + row.timing"><td><strong>{{ row.item }}</strong></td><td>{{ row.timing }}</td><td>{{ row.purpose }}</td><td class="table-source">{{ row.source }}</td></tr></tbody>
        </table>
      </div>
      <h4 class="report-subtitle danger">转诊指征</h4>
      <ul v-if="report.followup.referral.length" class="referral-list"><li v-for="item in report.followup.referral" :key="item">{{ item }}</li></ul>
      <p v-else class="report-empty">{{ report.followup.referral_note }}</p>
    </section>

    <section class="report-section">
      <div class="report-section-head"><span>08</span><h3>依据与说明</h3></div>
      <h4 class="report-subtitle">指南与出处清单</h4>
      <ol class="reference-list">
        <li v-for="source in report.references.sources" :key="source.code"><strong>{{ source.name }}</strong><span>来源编号：{{ source.code }}<template v-if="source.rules.length">；相关规则：{{ source.rules.join('、') }}</template></span></li>
      </ol>
      <h4 class="report-subtitle">术语对照</h4>
      <div class="term-list"><span v-for="term in report.references.terms" :key="term.abbr" :title="term.full"><strong>{{ term.abbr }}</strong>{{ term.full }}</span></div>
      <p class="disclaimer report-disclaimer"><el-icon :size="16"><InfoFilled /></el-icon><span>{{ report.references.disclaimer }}</span></p>
    </section>
  </div>
</template>
