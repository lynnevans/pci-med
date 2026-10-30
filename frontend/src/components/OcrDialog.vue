<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Camera, Loading, UploadFilled } from '@element-plus/icons-vue'
import {
  mergeOcrResults,
  prepareImage,
  requestOcr,
  type MergedOcrField,
  type OcrApiResult,
  type PreparedImage,
} from '../ocr'

type BatchStatus = 'pending' | 'running' | 'done' | 'error'

interface BatchItem {
  id: number
  name: string
  prepared: PreparedImage
  status: BatchStatus
  result?: OcrApiResult
  error?: string
}

const props = defineProps<{
  modelValue: boolean
  cardHint?: string
  current?: Record<string, any>
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'apply', payload: { patch: Record<string, any>; labels: string[] }): void
}>()

const MAX_IMAGES = 5
const MAX_FILE_MB = 25
const STATUS_TEXT: Record<BatchStatus, string> = {
  pending: '等待',
  running: '识别中',
  done: '完成',
  error: '失败',
}

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const cameraInput = ref<HTMLInputElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const tableRef = ref<any>(null)

const items = ref<BatchItem[]>([])
const selected = ref<MergedOcrField[]>([])
const keepCurrent = ref<Record<string, boolean>>({})
const busy = ref(false)
const preparing = ref(false)
const elapsed = ref(0)
const activeIndex = ref(-1)
const errorMsg = ref('')

let controller: AbortController | null = null
let timer: number | null = null
let nextId = 1

const doneItems = computed(() => items.value.filter((it) => it.status === 'done' && it.result))
const doneCount = computed(() => doneItems.value.length)
const failedItems = computed(() => items.value.filter((it) => it.status === 'error'))
const failedCount = computed(() => failedItems.value.length)
const pendingCount = computed(() => items.value.filter((it) => it.status === 'pending').length)
const finishedCount = computed(() => doneCount.value + failedCount.value)
const hasUnfinished = computed(() => items.value.some((it) => it.status !== 'done'))
const progressPct = computed(() =>
  items.value.length ? Math.round((finishedCount.value / items.value.length) * 100) : 0,
)
const alertType = computed<'error' | 'warning'>(() => (failedCount.value ? 'error' : 'warning'))

const merged = computed(() =>
  mergeOcrResults(
    doneItems.value.map((it) => ({
      index: items.value.indexOf(it),
      name: it.name,
      result: it.result!,
    })),
  ),
)
const fields = computed(() => merged.value.fields)
const unmatched = computed(() => merged.value.unmatched)
const warnings = computed(() => merged.value.warnings)
const itemCount = computed(() => merged.value.itemCount)
const disclaimer = computed(() => merged.value.disclaimer)
const conflictCount = computed(() => fields.value.filter((row) => row.conflict).length)
const formConflictCount = computed(() => fields.value.filter((row) => hasFormConflict(row)).length)

const resumeLabel = computed(() => {
  if (pendingCount.value) return `继续识别剩余（${pendingCount.value}）`
  if (failedCount.value) return `重试失败（${failedCount.value}）`
  return ''
})

const title = computed(() =>
  props.cardHint ? `化验单识别 · ${props.cardHint}` : '化验单识别（可多张）',
)

function stopTimer(): void {
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

function stateText(status: BatchStatus): string {
  return STATUS_TEXT[status]
}

function imageTag(indexes: number[]): string {
  return indexes.length ? `图${indexes.map((i) => i + 1).join('、图')}` : ''
}

function resetAll(): void {
  controller?.abort()
  controller = null
  stopTimer()
  items.value = []
  selected.value = []
  keepCurrent.value = {}
  busy.value = false
  preparing.value = false
  elapsed.value = 0
  activeIndex.value = -1
  errorMsg.value = ''
  if (cameraInput.value) cameraInput.value.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

watch(
  () => props.modelValue,
  (v) => {
    if (!v) resetAll()
  },
)

onBeforeUnmount(() => {
  controller?.abort()
  stopTimer()
})

function pick(fromCamera = false): void {
  const el = fromCamera ? cameraInput.value : fileInput.value
  el?.click()
}

async function onInputChange(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  if (files.length) await start(files)
}

async function onDrop(e: DragEvent): Promise<void> {
  const files = Array.from(e.dataTransfer?.files ?? [])
  if (files.length) await start(files)
}

async function start(files: File[]): Promise<void> {
  const images = files.filter((file) => file.type.startsWith('image/'))
  const skipped: string[] = files
    .filter((file) => !file.type.startsWith('image/'))
    .map((file) => `${file.name}（非图片）`)

  if (!images.length) {
    ElMessage.error('请选择图片文件（JPG / PNG / WebP）')
    return
  }
  if (images.length > MAX_IMAGES) {
    ElMessage.warning(`一次最多 ${MAX_IMAGES} 张，已取前 ${MAX_IMAGES} 张`)
  }
  const batch = images.slice(0, MAX_IMAGES)

  resetAll()
  preparing.value = true
  for (const file of batch) {
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      skipped.push(`${file.name}（超过 ${MAX_FILE_MB}MB）`)
      continue
    }
    try {
      const prepared = await prepareImage(file)
      items.value.push({ id: nextId++, name: file.name, prepared, status: 'pending' })
    } catch (err) {
      skipped.push(`${file.name}（${err instanceof Error ? err.message : String(err)}）`)
    }
  }
  preparing.value = false

  if (skipped.length) {
    ElMessage.warning(`已跳过 ${skipped.length} 张：${skipped[0]}${skipped.length > 1 ? ' 等' : ''}`)
  }
  if (!items.value.length) {
    errorMsg.value = '没有可识别的图片'
    return
  }
  await runAll()
}

async function runAll(): Promise<void> {
  if (busy.value || preparing.value) return
  const queue = items.value.filter((it) => it.status !== 'done')
  if (!queue.length) {
    if (fields.value.length) await selectDefaults()
    return
  }

  busy.value = true
  errorMsg.value = ''
  keepCurrent.value = {}
  const currentController = new AbortController()
  controller = currentController
  let aborted = false

  for (const item of queue) {
    if (!props.modelValue) {
      aborted = true
      break
    }
    item.status = 'running'
    item.error = ''
    activeIndex.value = items.value.indexOf(item)
    elapsed.value = 0
    const startedAt = Date.now()
    stopTimer()
    timer = window.setInterval(() => {
      elapsed.value = Math.floor((Date.now() - startedAt) / 1000)
    }, 250)

    try {
      const data = await requestOcr(item.prepared, props.cardHint ?? '', currentController.signal)
      if (data.error) {
        item.status = 'error'
        item.error = data.error
      } else {
        item.result = data
        item.status = 'done'
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        item.status = 'pending'
        aborted = true
        break
      }
      item.status = 'error'
      item.error = err instanceof Error ? err.message : String(err)
    } finally {
      stopTimer()
    }
  }

  busy.value = false
  if (controller === currentController) controller = null
  stopTimer()
  activeIndex.value = -1
  if (!props.modelValue) return

  if (aborted) {
    errorMsg.value = '已停止识别，可点「继续识别」处理剩余图片'
  } else if (failedCount.value) {
    errorMsg.value = `${failedCount.value} 张图片识别失败，可重试`
  }
  if (doneCount.value) await selectDefaults()
}

function cancel(): void {
  controller?.abort()
}

function reprocessAll(): void {
  for (const item of items.value) {
    item.status = 'pending'
    item.result = undefined
    item.error = ''
  }
  selected.value = []
  errorMsg.value = ''
  void runAll()
}

async function selectDefaults(): Promise<void> {
  await nextTick()
  const choices: Record<string, boolean> = {}
  for (const row of fields.value) if (hasFormConflict(row)) choices[row.field] = false
  keepCurrent.value = choices
  const table = tableRef.value
  if (!table) return
  table.clearSelection()
  const seen = new Set<string>()
  for (const row of fields.value) {
    if (seen.has(row.field)) continue
    seen.add(row.field)
    table.toggleRowSelection(row, true)
  }
}

function onSelect(rows: MergedOcrField[]): void {
  selected.value = rows
}

function formatValue(row: MergedOcrField): string {
  if (row.kind === 'bool') return row.value ? '是' : '否'
  if (row.kind === 'number') return `${row.value}${row.unit ? ' ' + row.unit : ''}`
  return String(row.value)
}

function sourceLine(row: MergedOcrField): string {
  const tag = imageTag(row.imageIndexes)
  const body = row.sources
    .map((s) => `${s.item}：${s.value}${s.unit ? ' ' + s.unit : ''}`)
    .join('；')
  return tag ? `${tag} · ${body}` : body
}

function sourceRange(row: MergedOcrField): string {
  const first = row.sources[0]
  if (!first) return ''
  const parts: string[] = []
  if (first.ref_range) parts.push('参考 ' + first.ref_range)
  if (first.flag === 'high') parts.push('↑ 高于参考范围')
  else if (first.flag === 'low') parts.push('↓ 低于参考范围')
  return parts.join(' · ')
}

function isAbnormal(row: MergedOcrField): boolean {
  return row.sources.some((s) => s.flag === 'high' || s.flag === 'low')
}

function currentText(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'boolean') return value ? '是' : '否'
  return String(value)
}

// 表单已有非默认值时提示「将被覆盖」，避免 OCR 静默改掉医生刚填的值
function conflictText(row: MergedOcrField): string {
  const cur = props.current?.[row.field]
  const text = currentText(cur)
  if (!text) return ''
  if (row.kind === 'bool' && cur === false) return ''
  if (row.kind === 'status' && cur === '正常') return ''
  if (String(cur) === String(row.value)) return ''
  return `表单已有「${text}」，请选择保留哪一项`
}

function hasFormConflict(row: MergedOcrField): boolean {
  return !!conflictText(row)
}

function formValue(row: MergedOcrField): string {
  return currentText(props.current?.[row.field]) || '—'
}

function rowClass({ row }: { row: any }): string {
  const item = row as MergedOcrField
  return [item.conflict ? 'ocr-conflict' : '', hasFormConflict(item) ? 'ocr-form-conflict' : '', isAbnormal(item) ? 'ocr-abnormal' : '']
    .filter(Boolean)
    .join(' ')
}

function confirmApply(): void {
  if (!selected.value.length) return
  const applied = selected.value.filter((row) => !(hasFormConflict(row) && keepCurrent.value[row.field]))
  if (!applied.length) {
    ElMessage.warning('所有选中项都选择了保留已填值，没有需要回填的内容')
    return
  }
  const seen = new Set<string>()
  for (const row of applied) {
    if (seen.has(row.field)) {
      ElMessage.error(`「${row.label}」勾选了多条，请只保留一条（多图冲突）`)
      return
    }
    seen.add(row.field)
  }

  const patch: Record<string, any> = {}
  const labels: string[] = []
  for (const row of applied) {
    patch[row.field] = row.value
    labels.push(row.label)
  }
  emit('apply', { patch, labels })
  visible.value = false
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="min(880px, 94vw)"
    top="5vh"
    append-to-body
    :close-on-click-modal="false"
    class="ocr-dialog"
    @closed="resetAll"
  >
    <!-- 未选图：拖拽 / 拍照 / 多选文件 -->
    <div v-if="!items.length && !preparing" class="drop" @dragover.prevent @drop.prevent="onDrop" @click="pick(false)">
      <el-icon :size="42" color="#0369a1"><UploadFilled /></el-icon>
      <p class="drop-title">拍照或上传化验单（可多张）</p>
      <p class="drop-sub">
        支持 JPG / PNG / WebP；一次最多 {{ MAX_IMAGES }} 张，逐张识别后合并。按 400 万像素 / 5000px 高压缩，图片只用于本次识别。
        <strong>多图会合并成同一份患者表单，仅限同一位患者；不同患者请分开识别。</strong>
      </p>
      <div class="drop-btns" @click.stop>
        <el-button type="primary" @click="pick(true)">
          <el-icon class="btn-ico"><Camera /></el-icon>拍照
        </el-button>
        <el-button @click="pick(false)">选择图片（可多选）</el-button>
      </div>
      <p class="drop-tip">手机「拍照」为单张；需要多张时用「选择图片」，可按住 Ctrl / Shift 多选。</p>
    </div>

    <input ref="cameraInput" type="file" accept="image/*" capture="environment" class="hidden-input" @change="onInputChange" />
    <input ref="fileInput" type="file" accept="image/*" multiple class="hidden-input" @change="onInputChange" />

    <div v-if="preparing" class="busy">
      <el-icon class="is-loading" :size="18"><Loading /></el-icon>
      <span>正在读取 / 压缩图片…</span>
    </div>

    <!-- 已选图：单张预览，多张缩略图 -->
    <div v-if="items.length" class="batch">
      <div v-if="items.length === 1" class="shot">
        <img :src="items[0].prepared.dataUrl" class="shot-img" alt="化验单预览" />
        <div class="shot-meta">
          <p class="shot-name">{{ items[0].name }}</p>
          <p class="shot-size">
            {{ items[0].prepared.width }}×{{ items[0].prepared.height }} ·
            {{ Math.round(items[0].prepared.bytes / 1024) }} KB ·
            <span :class="['state', items[0].status]">{{ stateText(items[0].status) }}</span>
          </p>
          <div class="shot-btns">
            <el-button size="small" :disabled="busy" @click="pick(false)">重新选择</el-button>
            <el-button v-if="!busy && items[0].status === 'done'" size="small" @click="reprocessAll">重新识别</el-button>
            <el-button v-else-if="!busy" size="small" type="primary" @click="runAll">
              {{ items[0].status === 'error' ? '重试' : '继续识别' }}
            </el-button>
          </div>
        </div>
      </div>

      <template v-else>
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          class="same-patient"
          title="这多张图会合并成同一份患者表单。请确认它们属于同一位患者；不同患者请分开识别。"
        />
        <div class="batch-head">
          <span class="batch-count">共 {{ items.length }} 张</span>
          <span class="batch-hint">按顺序逐张识别；失败的可单独重试</span>
        </div>
        <div class="thumbs">
          <div v-for="(it, i) in items" :key="it.id" :class="['thumb', it.status]">
            <img :src="it.prepared.dataUrl" :alt="it.name" />
            <div class="thumb-name" :title="it.name">{{ i + 1 }}. {{ it.name }}</div>
            <div class="thumb-state">
              {{ stateText(it.status) }}<span v-if="it.status === 'error'" class="thumb-err" :title="it.error">（可重试）</span>
            </div>
          </div>
        </div>
        <div class="batch-actions">
          <el-button size="small" :disabled="busy" @click="pick(false)">重新选择</el-button>
          <el-button v-if="!busy" size="small" @click="reprocessAll">全部重识别</el-button>
          <el-button v-if="!busy && hasUnfinished" size="small" type="primary" @click="runAll">{{ resumeLabel }}</el-button>
        </div>
      </template>
    </div>

    <div v-if="busy" class="busy">
      <el-icon class="is-loading" :size="18"><Loading /></el-icon>
      <span v-if="activeIndex >= 0">正在识别第 {{ activeIndex + 1 }} / {{ items.length }} 张 · {{ elapsed }}s</span>
      <span v-else>正在准备…</span>
      <div class="busy-bar"><i :style="{ width: progressPct + '%' }"></i></div>
      <el-button size="small" text type="primary" @click="cancel">停止</el-button>
    </div>

    <el-alert v-if="errorMsg" :title="errorMsg" :type="alertType" show-icon :closable="false" class="ocr-alert">
      <template #default>
        <p class="err-tip">可以先检查：后端是否在 8000 端口、.env 里 DASHSCOPE_API_KEY 是否有效、图片是否清晰且方向正确。识别失败可以直接手动填写，不影响生成建议。</p>
        <ul v-if="failedItems.length" class="fail-list">
          <li v-for="it in failedItems" :key="it.id">{{ it.name }}：{{ it.error }}</li>
        </ul>
      </template>
    </el-alert>

    <!-- 识别结果：逐项核对后回填 -->
    <template v-if="doneCount > 0">
      <div v-if="fields.length" class="summary">
        <span>共 {{ items.length }} 张图 · 识别 {{ itemCount }} 项 · 可回填 <b>{{ fields.length }}</b> 项</span>
        <span v-if="conflictCount" class="summary-conflict">{{ conflictCount }} 项多图冲突，请只勾选一条</span>
        <span v-if="formConflictCount" class="summary-conflict">{{ formConflictCount }} 项表单已有值，请在「冲突处理」选择</span>
        <span class="summary-hint">逐项核对；同一字段出现多条时只保留一条。</span>
      </div>

      <el-table
        v-if="fields.length"
        ref="tableRef"
        :data="fields"
        size="small"
        class="ocr-table"
        max-height="380"
        :row-class-name="rowClass"
        @selection-change="onSelect"
      >
        <el-table-column type="selection" width="46" />
        <el-table-column label="回填字段" min-width="190">
          <template #default="{ row }">
            <div class="f-label">
              {{ row.label }}
              <span class="f-card">{{ row.card }}</span>
              <span v-if="row.conflict" class="f-badge">多图冲突</span>
            </div>
            <div v-if="row.note" class="f-note">{{ row.note }}</div>
          </template>
        </el-table-column>
        <el-table-column label="化验单原值" min-width="200">
          <template #default="{ row }">
            <div class="f-src">{{ sourceLine(row) }}</div>
            <div class="f-range">{{ sourceRange(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="已填值" width="110">
          <template #default="{ row }">
            <span class="f-current">{{ formValue(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="将回填" width="120">
          <template #default="{ row }">
            <span :class="['f-value', { danger: isAbnormal(row) }]">{{ formatValue(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="冲突处理" width="156">
          <template #default="{ row }">
            <el-radio-group v-if="hasFormConflict(row)" v-model="keepCurrent[row.field]" size="small">
              <el-radio-button :value="false">识别值</el-radio-button>
              <el-radio-button :value="true">已填值</el-radio-button>
            </el-radio-group>
            <span v-else class="f-no-conflict">—</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="empty">未匹配到可回填字段，请查看下方识别项后手动录入。</div>

      <el-collapse v-if="warnings.length || unmatched.length" class="ocr-extra">
        <el-collapse-item v-if="warnings.length" :title="`注意事项（${warnings.length}）`" name="warn">
          <ul class="warn-list">
            <li v-for="(w, i) in warnings" :key="i">{{ w }}</li>
          </ul>
        </el-collapse-item>
        <el-collapse-item v-if="unmatched.length" :title="`未回填的识别项（${unmatched.length}）`" name="unmatched">
          <ul class="warn-list">
            <li v-for="(u, i) in unmatched" :key="i">
              <span class="u-img">{{ imageTag(u.imageIndexes) }}</span>
              {{ u.item }}：{{ u.value }}{{ u.unit ? ' ' + u.unit : '' }}
              <span v-if="u.reason" class="u-reason">（{{ u.reason }}）</span>
            </li>
          </ul>
        </el-collapse-item>
      </el-collapse>

      <p v-if="disclaimer" class="ocr-disclaimer">{{ disclaimer }}</p>
    </template>

    <template #footer>
      <div class="ocr-footer">
        <span v-if="fields.length" class="ocr-count">已选 {{ selected.length }} / {{ fields.length }} 项</span>
        <div class="ocr-actions">
          <el-button @click="visible = false">取消</el-button>
          <el-button
            v-if="fields.length"
            type="primary"
            :disabled="!selected.length || busy"
            @click="confirmApply"
          >
            确认回填（{{ selected.length }} 项）
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.hidden-input { display: none; }

.drop {
  border: 2px dashed #cbd5e1;
  border-radius: 14px;
  padding: 34px 20px 26px;
  text-align: center;
  cursor: pointer;
  background: #f8fafc;
  transition: border-color 0.2s, background 0.2s;
}
.drop:hover { border-color: #0369a1; background: #f0f7fb; }
.drop-title { margin: 10px 0 6px; font-size: 17px; font-weight: 600; color: #0f172a; }
.drop-sub { margin: 0 auto; max-width: 560px; font-size: 13px; color: #64748b; line-height: 1.6; }
.drop-btns { display: flex; justify-content: center; gap: 12px; margin: 18px 0 12px; }
.drop-tip { margin: 0; font-size: 12px; color: #94a3b8; }
.btn-ico { margin-right: 4px; vertical-align: -2px; }

.batch { margin-top: 4px; }
.same-patient { margin-bottom: 10px; }
.batch-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px; }
.batch-count { font-size: 13.5px; font-weight: 600; color: #0f172a; }
.batch-hint { font-size: 12px; color: #94a3b8; }
.batch-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }

.thumbs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(108px, 1fr));
  gap: 10px;
}
.thumb {
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  padding: 6px;
  background: #fff;
  min-width: 0;
}
.thumb img {
  width: 100%;
  height: 64px;
  object-fit: contain;
  background: #f8fafc;
  border-radius: 6px;
}
.thumb-name {
  margin-top: 4px;
  font-size: 11.5px;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.thumb-state { font-size: 11px; color: #94a3b8; }
.thumb.running { border-color: #0369a1; box-shadow: 0 0 0 2px rgba(3, 105, 161, 0.12); }
.thumb.done .thumb-state { color: #16a34a; }
.thumb.error { border-color: #fecaca; }
.thumb.error .thumb-state { color: #dc2626; }
.thumb-err { color: #dc2626; }

.shot { display: flex; gap: 14px; align-items: flex-start; }
.shot-img {
  width: 44%;
  max-height: 190px;
  object-fit: contain;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}
.shot-meta { flex: 1; min-width: 0; }
.shot-name { margin: 2px 0 4px; font-size: 14px; font-weight: 600; color: #0f172a; word-break: break-all; }
.shot-size { margin: 0 0 12px; font-size: 12.5px; color: #94a3b8; }
.shot-btns { display: flex; gap: 8px; flex-wrap: wrap; }
.state.pending { color: #94a3b8; }
.state.running { color: #0369a1; }
.state.done { color: #16a34a; }
.state.error { color: #dc2626; }

.busy {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid rgba(3, 105, 161, 0.18);
  background: rgba(3, 105, 161, 0.06);
  border-radius: 10px;
  color: #0369a1;
  font-size: 13.5px;
}
.busy .el-button { margin-left: auto; }
.busy-bar { flex: 1; min-width: 80px; height: 6px; border-radius: 3px; background: #dbeafe; overflow: hidden; }
.busy-bar i { display: block; height: 100%; background: #0369a1; transition: width 0.25s; }

.ocr-alert { margin-top: 14px; }
.err-tip { margin: 6px 0 0; font-size: 12.5px; line-height: 1.6; color: #7f1d1d; }
.fail-list {
  margin: 6px 0 0;
  padding-left: 18px;
  max-height: 90px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.6;
  color: #7f1d1d;
  word-break: break-all;
}

.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  align-items: baseline;
  margin: 16px 0 10px;
  font-size: 13.5px;
  color: #334155;
}
.summary b { color: #0369a1; }
.summary-conflict { font-size: 12.5px; font-weight: 600; color: #b91c1c; }
.summary-hint { font-size: 12px; color: #94a3b8; }

.ocr-table { border: 1px solid #e2e8f0; border-radius: 10px; }
.ocr-table :deep(th.el-table__cell) { background: #f8fafc; color: #475569; font-weight: 600; }
.ocr-table :deep(.ocr-abnormal td.el-table__cell) { background: #fff7ed; }
.ocr-table :deep(.ocr-form-conflict td.el-table__cell) { background: #eff6ff; }
.ocr-table :deep(.ocr-conflict td.el-table__cell) { background: #fef2f2; }
.f-label { font-weight: 600; color: #0f172a; font-size: 13.5px; }
.f-card {
  margin-left: 6px;
  font-size: 11px;
  font-weight: 400;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  padding: 1px 6px;
}
.f-badge {
  margin-left: 6px;
  font-size: 10.5px;
  font-weight: 400;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 5px;
  padding: 1px 5px;
}
.f-note { margin-top: 3px; font-size: 11.5px; color: #94a3b8; line-height: 1.5; }
.f-src { font-size: 13px; color: #334155; }
.f-range { margin-top: 2px; font-size: 11.5px; color: #94a3b8; }
.f-value { font-weight: 700; color: #0369a1; }
.f-value.danger { color: #b45309; }
.f-current { font-size: 12.5px; color: #475569; }
.f-no-conflict { color: #cbd5e1; }
.f-conflict { margin-top: 3px; font-size: 11px; color: #b45309; line-height: 1.4; }

.empty { padding: 24px 0; text-align: center; color: #94a3b8; font-size: 13.5px; }

.ocr-extra { margin-top: 12px; }
.warn-list { margin: 0; padding-left: 18px; font-size: 12.5px; color: #475569; line-height: 1.8; }
.u-img { display: inline-block; margin-right: 4px; color: #0369a1; font-weight: 600; }
.u-reason { color: #94a3b8; }

.ocr-disclaimer { margin: 14px 0 0; font-size: 12px; color: #94a3b8; text-align: center; }

.ocr-footer { display: flex; align-items: center; gap: 12px; }
.ocr-count { font-size: 12.5px; color: #64748b; }
.ocr-actions { margin-left: auto; display: flex; gap: 8px; }

@media (max-width: 640px) {
  .shot { flex-direction: column; }
  .shot-img { width: 100%; max-height: 150px; }
  .summary-hint { display: none; }
  .thumbs { grid-template-columns: repeat(auto-fill, minmax(92px, 1fr)); }
  .thumb img { height: 52px; }
  .busy { flex-wrap: wrap; }
  .busy-bar { order: 3; flex-basis: 100%; }
}
</style>