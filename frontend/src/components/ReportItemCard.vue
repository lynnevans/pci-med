<script setup lang="ts">
import { Document, WarningFilled } from '@element-plus/icons-vue'

interface ReportItem {
  ref?: string
  conclusion: string
  evidence: string
  impact: string
  action: string
  timeframe: string
  source: string
  severity?: string
  level?: string
}

defineProps<{ item: ReportItem }>()
</script>

<template>
  <article :class="['report-item', `report-item-${item.severity || 'attention'}`]">
    <div class="report-item-head">
      <el-icon v-if="item.severity === 'critical'" :size="19"><WarningFilled /></el-icon>
      <span v-if="item.ref" class="report-item-ref">{{ item.ref }}</span>
      <h4>{{ item.conclusion }}</h4>
      <span v-if="item.severity && item.severity !== 'critical'" class="report-severity">{{ item.severity }}</span>
      <el-tag v-if="item.level" size="small" effect="plain">{{ item.level }}</el-tag>
    </div>
    <dl class="report-facts">
      <div><dt>证据</dt><dd>{{ item.evidence }}</dd></div>
      <div><dt>影响</dt><dd>{{ item.impact }}</dd></div>
      <div><dt>建议</dt><dd>{{ item.action }}</dd></div>
      <div><dt>时限</dt><dd>{{ item.timeframe }}</dd></div>
    </dl>
    <p class="report-source"><el-icon :size="13"><Document /></el-icon>{{ item.source }}</p>
  </article>
</template>
