<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  report: any
  patient: Record<string, any>
}>()

const r = computed(() => props.report || {})
const p = computed(() => props.patient || {})
const levels = computed(() => r.value.action_plan?.levels || [])
const primary = computed(() => levels.value.find((x: any) => x.key === 'primary')?.items || [])
const secondary = computed(() => levels.value.find((x: any) => x.key === 'secondary')?.items || [])
const tertiary = computed(() => levels.value.find((x: any) => x.key === 'tertiary')?.items || [])

function text(value: unknown): string {
  return String(value ?? '—').trim() || '—'
}

function short(text: unknown, max = 40): string {
  const value = String(text || '').replace(/\s+/g, '').replace(/[。；;]+$/g, '')
  return value.length > max ? value.slice(0, max - 1) + '…' : value
}

function oneSentence(): string {
  const first = primary.value[0] || secondary.value[0] || tertiary.value[0]
  if (!first) return '维持现有方案，按计划完成随访'
  return short(`${first.action} ${first.timeframe || '本次随访'}`, 40)
}

function redRows() {
  return primary.value.map((item: any) => ({
    problem: text(item.conclusion),
    action: text(item.action),
    timeframe: text(item.timeframe || '今日'),
  }))
}

function yellowRows() {
  const rows: any[] = []
  const seen = new Set<string>()
  for (const item of [...secondary.value, ...tertiary.value]) {
    const key = String(item.conclusion || '')
    if (seen.has(key)) continue
    seen.add(key)
    rows.push({
      item: text(item.conclusion),
      current: text(item.current || item.conclusion),
      target: text(item.recommendation || item.target),
      action: text(item.action),
      timeframe: text(item.timeframe || '本次随访'),
    })
  }
  return rows
}

function medicationRows() {
  const gaps = (r.value.medication_gap?.items || []).filter((row: any) =>
    `${row.decision || ''}`.includes('缺口') || `${row.decision || ''}`.includes('未达标') || `${row.decision || ''}`.includes('建议评估'),
  )
  if (gaps.length) {
    return gaps.map((row: any) => ({
      drug: text(row.item),
      current: text(row.current || '未使用/未录入'),
      suggested: text(row.action || row.recommendation),
      tag: `${row.decision || ''}`.includes('加用') ? '加用' : '调整',
      reason: short(row.decision || row.impact || '—', 10),
    }))
  }
  return (r.value.adjust_plan || []).map((row: any) => {
    const action = String(row.action || '')
    const tag = /停/.test(action) ? '停用' : /加|启动|联合/.test(action) ? '加用' : '调整'
    return {
      drug: text(row.conclusion || row.current_medication),
      current: text(row.current_medication),
      suggested: text(row.action || row.recommendation),
      tag,
      reason: short(row.reason || row.evidence || '—', 10),
    }
  })
}

function chip(label: string, value: unknown, unit: string, direction: string, level: 'red' | 'amber' = 'amber') {
  if (value === null || value === undefined || value === '') return null
  return { label, value: String(value), unit, direction, level }
}

function abnormalChips() {
  const out: any[] = []
  const q = p.value
  const add = (x: any) => { if (x) out.push(x) }
  const hb = Number(q.hb)
  if (q.hb_low || (Number.isFinite(hb) && hb > 0 && hb < 110)) add(chip('血红蛋白', q.hb, 'g/L', '↓', hb < 70 ? 'red' : 'amber'))
  const plt = Number(q.plt)
  if (q.plt_status === '降低' || (Number.isFinite(plt) && plt > 0 && plt < 100)) add(chip('血小板', q.plt, '×10⁹/L', '↓', plt < 50 ? 'red' : 'amber'))
  const alt = Number(q.alt)
  const ast = Number(q.ast)
  const liver = Math.max(Number.isFinite(alt) ? alt : 0, Number.isFinite(ast) ? ast : 0)
  if (liver > 40) add(chip('ALT/AST', `${q.alt ?? '—'}/${q.ast ?? '—'}`, 'U/L', '↑', liver > 120 ? 'red' : 'amber'))
  const egfr = Number(q.egfr)
  if (Number.isFinite(egfr) && egfr > 0 && egfr < 90) add(chip('eGFR', q.egfr, 'ml/min/1.73m²', '↓', egfr < 30 ? 'red' : 'amber'))
  const ldl = Number(q.current_ldl)
  const target = q.ascvd_risk === '超高危' ? 1.4 : q.ascvd_risk === '极高危' ? 1.8 : null
  if (Number.isFinite(ldl) && ldl > 0 && target && ldl > target) add(chip('LDL-C', q.current_ldl, 'mmol/L', '↑', ldl > target * 2 ? 'red' : 'amber'))
  const k = Number(q.potassium)
  if (Number.isFinite(k) && k > 0 && (k < 3.5 || k > 5.5)) add(chip('血钾', q.potassium, 'mmol/L', k < 3.5 ? '↓' : '↑', k < 3 || k > 6 ? 'red' : 'amber'))
  const na = Number(q.sodium)
  if (Number.isFinite(na) && na > 0 && (na < 135 || na > 145)) add(chip('血钠', q.sodium, 'mmol/L', na < 135 ? '↓' : '↑', na < 125 || na > 155 ? 'red' : 'amber'))
  const fpg = Number(q.fpg)
  if (Number.isFinite(fpg) && fpg > 0 && (fpg < 3.9 || fpg >= 6.1)) add(chip('空腹血糖', q.fpg, 'mmol/L', fpg < 3.9 ? '↓' : '↑', fpg <= 2.8 || fpg >= 22.2 ? 'red' : 'amber'))
  const a1c = Number(q.hba1c)
  if (Number.isFinite(a1c) && a1c > 0 && a1c >= 6.5) add(chip('HbA1c', q.hba1c, '%', '↑'))
  const hr = Number(q.heart_rate)
  if (Number.isFinite(hr) && hr > 0 && (hr < 60 || hr >= 100)) add(chip('心率', q.heart_rate, '次/分', hr < 60 ? '↓' : '↑', hr < 40 || hr > 130 ? 'red' : 'amber'))
  const qtc = Number(q.qtc)
  if (Number.isFinite(qtc) && qtc > 0 && qtc >= 460) add(chip('QTc', q.qtc, 'ms', '↑', qtc > 500 ? 'red' : 'amber'))
  const inr = Number(q.inr)
  if (Number.isFinite(inr) && inr > 0 && inr > 3) add(chip('INR', q.inr, '', '↑', inr > 4.5 ? 'red' : 'amber'))
  const dd = Number(q.d_dimer)
  if (Number.isFinite(dd) && dd > 0 && dd > 0.5) add(chip('D-二聚体', q.d_dimer, 'mg/L', '↑', dd > 2 ? 'red' : 'amber'))
  const lvef = Number(q.lvef)
  if (Number.isFinite(lvef) && lvef > 0 && lvef < 50) add(chip('LVEF', q.lvef, '%', '↓', lvef < 40 ? 'red' : 'amber'))
  if (q.troponin_elevated) add(chip('肌钙蛋白', q.troponin_value ?? '升高', 'ng/mL', '↑', 'red'))
  const bnp = Number(q.bnp)
  if (Number.isFinite(bnp) && bnp > 0 && bnp > 100) add(chip('BNP/NT-proBNP', q.bnp, 'pg/mL', '↑'))
  return out
}

function greenRows() {
  const rows = (r.value.followup?.schedule || [])
    .filter((row: any) => String(row.timing || '').includes('术后'))
    .slice(0, 4)
  return rows.map((row: any) => ({
    timing: text(row.timing),
    items: text(row.item),
    target: text(row.purpose),
    where: '基层；异常转上级',
  }))
}

function reportId(): string {
  const seed = `${p.value.patient_name || ''}|${p.value.sex || ''}|${p.value.age || ''}|${p.value.surgery_date || ''}`
  let hash = 0
  for (const ch of seed) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return `PCI-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${String(hash % 10000).padStart(4, '0')}`
}

const today = new Date().toLocaleDateString('zh-CN')
const generatedAt = new Date().toLocaleString('zh-CN', { hour12: false })
const riskLabel = computed(() => String(r.value.summary?.risk_label || '风险待评估').replace('-', ' · '))
const riskBasis = computed(() => {
  const c = r.value.summary?.counts || {}
  return `危急值 ${c.critical || 0} 项 / 关注异常 ${c.attention || 0} 项 / 用药调整 ${c.medication || 0} 条`
})
const red = computed(redRows)
const yellow = computed(yellowRows)
const meds = computed(medicationRows)
const chips = computed(abnormalChips)
const green = computed(greenRows)
const references = computed(() => {
  const names = (r.value.references?.sources || []).map((x: any) => x.name).filter(Boolean)
  return [...new Set(names.filter((name: string) => !name.includes('原始来源') && !name.includes('模板') && !name.includes('规则库')))]
})
const emergency = computed(() => {
  const items = (r.value.symptoms || []).filter((x: any) => x.priority === 1).map((x: any) => short(x.conclusion, 12))
  return items.length ? items.slice(0, 4) : ['持续胸痛', '黑矇 / 晕厥', '呕血 / 黑便']
})
const revisit = computed(() => {
  const items = (r.value.symptoms || []).filter((x: any) => x.priority === 2).map((x: any) => short(x.conclusion, 12))
  return items.length ? items.slice(0, 4) : ['胸闷气短加重', '下肢水肿', '心悸']
})
</script>

<template>
  <div class="concise-report">
    <div class="concise-sheet">
      <header class="rpt-head">
        <div>
          <div class="rpt-title">PCI 术后随访用药评估单</div>
          <div class="rpt-sub">基层医疗机构使用 · 依据现行指南与专家共识生成，须由临床医生复核后执行</div>
        </div>
        <div class="rpt-badge">
          {{ riskLabel }}
          <span>主要依据：{{ riskBasis }}</span>
        </div>
      </header>

      <div class="idbar">
        <div><i>姓名</i><span class="ph">{{ p.patient_name || '未填写' }}</span></div>
        <div><i>性别 / 年龄</i><span class="ph">{{ p.sex || '—' }}</span> / <span class="ph">{{ p.age ?? '—' }}</span> 岁</div>
        <div><i>术后</i><span class="ph">{{ p.post_pci_months ?? '—' }}</span> 个月（<span class="ph">{{ p.surgery_date || '手术日期未录' }}</span>）</div>
        <div><i>复查日期</i><span class="ph">{{ today }}</span></div>
        <div><i>报告编号</i><span class="ph">{{ reportId() }}</span></div>
      </div>

      <div class="verdict">
        <div class="lb">本次最重要的一件事</div>
        <div class="tx">{{ oneSentence() }}</div>
      </div>

      <section class="sec">
        <div class="sec-h"><span class="dot d-red"></span>红灯 · 今天必须处理<span class="cap">按紧急度降序；无则整块显示“无”</span></div>
        <div v-if="red.length">
          <div v-for="row in red" :key="row.problem" class="red-item">
            <span class="q">{{ row.problem }}</span>
            <span class="a">{{ row.action }}</span>
            <span class="t">{{ row.timeframe }}</span>
          </div>
        </div>
        <div v-else class="red-item empty"><span class="q">无</span><span class="a">本次未触发需要今日处理的条目</span><span class="t">—</span></div>
      </section>

      <section class="sec">
        <div class="sec-h"><span class="dot d-amber"></span>黄灯 · 本次复诊办完<span class="cap">按影响预后的权重降序；同一原因只出现一次</span></div>
        <table>
          <thead><tr><th style="width:20%">待办事项</th><th style="width:22%">当前情况</th><th style="width:18%">目标</th><th style="width:28%">具体动作（药名 + 剂量 + 频次）</th><th style="width:12%">复查时限</th></tr></thead>
          <tbody>
            <tr v-for="row in yellow" :key="row.item + row.action">
              <td class="k">{{ row.item }}</td><td>{{ row.current }}</td><td>{{ row.target }}</td><td>{{ row.action }}</td><td>{{ row.timeframe }}</td>
            </tr>
            <tr v-if="!yellow.length"><td class="k">无</td><td colspan="4">本次未识别需要本次复诊处理的待办事项。</td></tr>
          </tbody>
        </table>
      </section>

      <section class="sec">
        <div class="sec-h"><span class="dot d-blue"></span>用药调整一览<span class="cap">只列需要变动的药；无变动者合并为一行</span></div>
        <table>
          <thead><tr><th style="width:18%">药物</th><th style="width:26%">现方案</th><th style="width:28%">建议方案</th><th style="width:12%">处理</th><th style="width:16%">理由（≤10 字）</th></tr></thead>
          <tbody>
            <tr v-for="row in meds" :key="row.drug + row.suggested">
              <td class="k">{{ row.drug }}</td><td>{{ row.current }}</td><td>{{ row.suggested }}</td>
              <td><span :class="['tag', row.tag === '停用' ? 't-stop' : row.tag === '加用' ? 't-add' : 't-up']">{{ row.tag }}</span></td>
              <td>{{ row.reason }}</td>
            </tr>
            <tr v-if="!meds.length"><td class="k">其余用药</td><td colspan="3">维持现有方案，按计划复查</td><td><span class="tag t-keep">维持</span></td></tr>
          </tbody>
        </table>
      </section>

      <section class="sec">
        <div class="sec-h"><span class="dot d-red" style="background:#8e44ad"></span>异常指标速览<span class="cap">只列超出参考范围的，正常项不出现</span></div>
        <div class="chips">
          <span v-for="c in chips" :key="c.label + c.value" :class="['chip', c.level === 'red' ? 'red' : 'amber']">
            {{ c.label }} <b>{{ c.value }}</b> {{ c.unit }} {{ c.direction }}
          </span>
          <span v-if="!chips.length" class="chip">本次未录入超出参考范围的指标</span>
        </div>
      </section>

      <section class="sec">
        <div class="sec-h"><span class="dot d-green"></span>绿灯 · 接下来的随访安排<span class="cap">只排本次之后的节点；已过去的时间点不再出现</span></div>
        <table>
          <thead><tr><th style="width:26%">时间点（术后月数 / 预计日期）</th><th style="width:30%">要查什么</th><th style="width:26%">达标要求</th><th style="width:18%">去哪查</th></tr></thead>
          <tbody>
            <tr v-for="row in green" :key="row.timing + row.items"><td class="k">{{ row.timing }}</td><td>{{ row.items }}</td><td>{{ row.target }}</td><td>{{ row.where }}</td></tr>
            <tr v-if="!green.length"><td class="k">按计划</td><td colspan="3">术后随访节点待手术日期补全后生成。</td></tr>
          </tbody>
        </table>
      </section>

      <section class="patient-card">
        <div class="pc-title">患者提醒卡（请随身携带）</div>
        <div class="pc-grid">
          <div><h5>出现以下情况，立即去急诊</h5><ul><li v-for="x in emergency" :key="x">{{ x }}</li></ul></div>
          <div><h5>出现以下情况，尽快来复诊</h5><ul><li v-for="x in revisit" :key="x">{{ x }}</li></ul></div>
          <div><h5>不要自行做的事</h5><ul><li>不要自行停用抗血小板药</li><li>加用任何止痛药前先咨询</li></ul></div>
        </div>
      </section>

      <footer class="foot">
        <div>依据：{{ references.join('、') || '现行指南与专家共识' }}</div>
        <div>生成时间：{{ generatedAt }}　复核医生：__________</div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.concise-report { width: 100%; overflow-x: auto; padding: 4px 0 12px; }
.concise-sheet { width: 210mm; min-height: 297mm; margin: 0 auto; background: #fff; padding: 13mm 14mm 10mm; box-shadow: 0 4px 20px rgba(20, 40, 70, .14); font-size: 10.5pt; line-height: 1.5; color: #1f2430; }
.rpt-head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1f4e79; padding-bottom: 6px; gap: 12px; }
.rpt-title { font-size: 17pt; font-weight: 700; color: #1f4e79; letter-spacing: .5px; }
.rpt-sub { font-size: 8.5pt; color: #7a8496; margin-top: 3px; }
.rpt-badge { border: 1.5px solid #c62828; color: #c62828; border-radius: 4px; padding: 4px 10px; font-size: 9.5pt; font-weight: 700; text-align: center; line-height: 1.3; min-width: 150px; }
.rpt-badge span { display: block; font-size: 7.5pt; font-weight: 400; color: #8a4b4b; margin-top: 2px; }
.idbar { display: flex; flex-wrap: wrap; gap: 4px 18px; font-size: 9pt; color: #3b4453; padding: 7px 0 8px; border-bottom: 1px dashed #d3dae5; }
.idbar i { font-style: normal; color: #8a93a5; margin-right: 3px; }
.ph { color: #8a93a5; border-bottom: 1px dashed #b9c2d0; padding: 0 3px; font-style: normal; }
.verdict { margin: 10px 0 12px; border-left: 5px solid #c62828; background: #fdf0f0; padding: 8px 12px; }
.verdict .lb { font-size: 8.5pt; color: #a33; font-weight: 700; letter-spacing: .5px; }
.verdict .tx { font-size: 12pt; font-weight: 700; color: #8d1f1f; line-height: 1.45; margin-top: 2px; }
.sec { margin: 12px 0 0; }
.sec-h { display: flex; align-items: center; gap: 7px; font-size: 10.5pt; font-weight: 700; padding-bottom: 4px; border-bottom: 1px solid #e3e8f0; margin-bottom: 6px; }
.dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
.d-red { background: #c62828; } .d-amber { background: #d68910; } .d-green { background: #2e7d32; } .d-blue { background: #1f4e79; }
.sec-h .cap { color: #7a8496; font-weight: 400; font-size: 8.5pt; margin-left: auto; }
.red-item { border: 1px solid #f0c8c8; border-left: 4px solid #c62828; background: #fffafa; padding: 6px 10px; margin-bottom: 5px; display: flex; gap: 10px; align-items: baseline; }
.red-item .q { font-weight: 700; color: #8d1f1f; flex: none; }
.red-item .a { color: #2b3038; }
.red-item .t { margin-left: auto; flex: none; font-size: 8.5pt; font-weight: 700; color: #fff; background: #c62828; border-radius: 3px; padding: 1px 7px; }
.red-item.empty { border-style: dashed; background: #fff; color: #8a93a5; } .red-item.empty .q { color: #8a93a5; }
table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
th { background: #f1f5fa; color: #1f4e79; font-weight: 700; text-align: left; padding: 4px 7px; border: 1px solid #dbe3ee; font-size: 9pt; }
td { padding: 4px 7px; border: 1px solid #e3e8f0; vertical-align: top; }
td.k { font-weight: 700; color: #2b3038; }
.tag { display: inline-block; font-size: 8pt; padding: 0 6px; border-radius: 3px; line-height: 1.7; white-space: nowrap; }
.t-keep { background: #eef7ef; color: #2e7d32; border: 1px solid #cbe3cd; } .t-up { background: #fff4e5; color: #a86500; border: 1px solid #f0d9b5; } .t-stop { background: #fdeaea; color: #b32b2b; border: 1px solid #f2c6c6; } .t-add { background: #e8f1fb; color: #1f4e79; border: 1px solid #c6d9ef; }
.chips { display: flex; flex-wrap: wrap; gap: 5px; }
.chip { font-size: 9pt; border: 1px solid #e0e6ef; border-radius: 14px; padding: 2px 10px; background: #fafbfd; color: #3b4453; }
.chip b { font-weight: 700; } .chip.red { border-color: #f0c8c8; background: #fff6f6; color: #8d1f1f; } .chip.amber { border-color: #f0d9b5; background: #fffaf0; color: #8a5600; }
.patient-card { margin-top: 12px; border: 2px dashed #9ab0c9; border-radius: 4px; padding: 8px 12px 9px; position: relative; }
.patient-card::after { content: "沿虚线剪下交给患者"; position: absolute; right: 10px; top: -10px; background: #fff; padding: 0 6px; font-size: 8pt; color: #8a93a5; }
.pc-title { font-size: 10pt; font-weight: 700; color: #1f4e79; margin-bottom: 4px; }
.pc-grid { display: flex; gap: 16px; font-size: 9.5pt; } .pc-grid > div { flex: 1; }
.pc-grid h5 { margin: 0 0 2px; font-size: 9pt; color: #b32b2b; } .pc-grid ul { margin: 0; padding-left: 16px; } .pc-grid li { margin: 1px 0; }
.foot { margin-top: 12px; border-top: 1px solid #e3e8f0; padding-top: 6px; font-size: 8pt; color: #8a93a5; display: flex; justify-content: space-between; gap: 20px; }
@media (max-width: 900px) { .concise-sheet { width: 100%; min-height: auto; padding: 14px; } }
@media print {
  .concise-report { overflow: visible; padding: 0; }
  .concise-sheet { width: auto; min-height: auto; box-shadow: none; margin: 0; padding: 8mm; }
  .red-item, tr, .patient-card { break-inside: avoid; }
  @page { size: A4; margin: 8mm; }
}
</style>


