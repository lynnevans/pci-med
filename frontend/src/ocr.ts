/**
 * 化验单 OCR 前端接线层
 * - prepareImage：按「400 万像素 / 高 5000px」压缩，长条化验单不会被压成一条细线
 * - requestOcr：POST /api/ocr，返回后端「已映射」的 fields
 * 这里不做任何字段映射（映射在 backend/ocr_map.py，确定性字典，零 LLM）。
 */

export type OcrFieldKind = 'number' | 'status' | 'bool'

export interface OcrSourceItem {
  item: string
  value: string
  unit: string
  ref_range: string
  flag: string
  reason?: string
}

export interface OcrMappedField {
  field: string
  label: string
  kind: OcrFieldKind
  card: string
  value: number | string | boolean
  unit: string
  sources: OcrSourceItem[]
  note: string
}

export interface OcrApiResult {
  items?: OcrSourceItem[]
  remark?: string
  fields?: OcrMappedField[]
  unmatched?: OcrSourceItem[]
  warnings?: string[]
  error?: string
  disclaimer?: string
}

/** 多图批量识别：每张图单独调用 /api/ocr，前端只负责合并「已映射」的字段 */
export interface OcrBatchImageResult {
  /** 图片在原批次里的下标（0 开始），用于显示「图1、图2」 */
  index: number
  name: string
  result: OcrApiResult
}

export interface MergedOcrField extends OcrMappedField {
  imageIndexes: number[]
  imageNames: string[]
  /** 同一字段在多张单子上出现不同值时置 true，必须让医生只勾一条 */
  conflict: boolean
}

export interface MergedOcrUnmatched extends OcrSourceItem {
  imageIndexes: number[]
}

export interface MergedOcrResult {
  fields: MergedOcrField[]
  unmatched: MergedOcrUnmatched[]
  warnings: string[]
  itemCount: number
  disclaimer: string
}

function sameValue(a: unknown, b: unknown): boolean {
  if (typeof a === 'boolean' || typeof b === 'boolean') return Boolean(a) === Boolean(b)
  return String(a) === String(b)
}

function sameSource(a: OcrSourceItem, b: OcrSourceItem): boolean {
  return (
    a.item === b.item &&
    a.value === b.value &&
    a.unit === b.unit &&
    a.ref_range === b.ref_range &&
    (a.flag || '') === (b.flag || '')
  )
}

function appendNote(base: string | undefined, extra: string | undefined): string {
  const parts: string[] = []
  for (const raw of `${base || ''}；${extra || ''}`.split('；')) {
    const text = raw.trim()
    if (text && !parts.includes(text)) parts.push(text)
  }
  return parts.join('；')
}

/**
 * 合并多张图的映射结果：
 * - 同字段同值：合并来源、图片编号、备注；
 * - 同字段不同值：**不自动选**，两条都保留并标 conflict，默认只勾第一条；
 * - warnings / unmatched 按文本去重，并合并图片编号。
 */
export function mergeOcrResults(results: OcrBatchImageResult[]): MergedOcrResult {
  const rows: MergedOcrField[] = []
  const byField = new Map<string, MergedOcrField[]>()
  const unmatchedMap = new Map<string, MergedOcrUnmatched>()
  const warningMap = new Map<string, number[]>()
  let itemCount = 0
  let disclaimer = ''

  for (const { index, name, result } of results) {
    itemCount += result.items?.length ?? 0
    if (!disclaimer && result.disclaimer) disclaimer = result.disclaimer

    if (result.remark) {
      const text = `模型备注：${result.remark}`
      const indexes = warningMap.get(text) ?? []
      if (!indexes.includes(index)) indexes.push(index)
      warningMap.set(text, indexes)
    }

    for (const warning of result.warnings ?? []) {
      const indexes = warningMap.get(warning) ?? []
      if (!indexes.includes(index)) indexes.push(index)
      warningMap.set(warning, indexes)
    }

    for (const item of result.unmatched ?? []) {
      const key = `${item.item}|${item.value}|${item.unit}|${item.reason || ''}`
      const found = unmatchedMap.get(key)
      if (found) {
        if (!found.imageIndexes.includes(index)) found.imageIndexes.push(index)
      } else {
        unmatchedMap.set(key, { ...item, imageIndexes: [index] })
      }
    }

    for (const field of result.fields ?? []) {
      const existing = byField.get(field.field) ?? []
      let row = existing.find((candidate) => sameValue(candidate.value, field.value))

      if (!row) {
        row = {
          ...field,
          imageIndexes: [],
          imageNames: [],
          conflict: existing.length > 0,
          note: field.note,
        }
        if (existing.length > 0) {
          const message = `与其他图片的「${field.label}」结果不一致，请只勾选一条`
          row.note = appendNote(row.note, message)
          for (const other of existing) {
            other.conflict = true
            other.note = appendNote(other.note, message)
          }
        }
        rows.push(row)
        byField.set(field.field, [...existing, row])
      }

      if (!row.imageIndexes.includes(index)) row.imageIndexes.push(index)
      if (!row.imageNames.includes(name)) row.imageNames.push(name)
      for (const source of field.sources ?? []) {
        if (!row.sources.some((candidate) => sameSource(candidate, source))) {
          row.sources.push(source)
        }
      }
      if (field.note) row.note = appendNote(row.note, field.note)
    }
  }

  // 把同一字段的多行放在一起（冲突行相邻），其余按首次出现顺序
  const firstSeen = new Map<string, number>()
  rows.forEach((row, i) => {
    if (!firstSeen.has(row.field)) firstSeen.set(row.field, i)
  })
  rows.sort(
    (a, b) =>
      (firstSeen.get(a.field) ?? 0) - (firstSeen.get(b.field) ?? 0) ||
      (a.imageIndexes[0] ?? 0) - (b.imageIndexes[0] ?? 0),
  )

  return {
    fields: rows,
    unmatched: [...unmatchedMap.values()],
    warnings: [...warningMap.entries()].map(
      ([text, indexes]) => `${indexes.map((i) => `图${i + 1}`).join('、')}：${text}`,
    ),
    itemCount,
    disclaimer,
  }
}

export interface PreparedImage {
  dataUrl: string
  base64: string
  width: number
  height: number
  bytes: number
}

const MAX_PIXELS = 4_000_000
const MAX_HEIGHT = 5000
/** base64 字符数上限（约 2MB 原图），超过则降质量重编码 */
const MAX_BASE64_CHARS = 2_600_000

type Drawable = ImageBitmap | HTMLImageElement

async function decodeImage(file: File): Promise<Drawable> {
  if (typeof createImageBitmap === 'function') {
    try {
      // from-image：按 EXIF 方向摆正，避免手机竖拍照片横过来
      return await createImageBitmap(file, { imageOrientation: 'from-image' })
    } catch {
      /* 部分浏览器不支持该参数，回落到 <img> 解码 */
    }
  }
  const url = URL.createObjectURL(file)
  try {
    const img = new Image()
    img.decoding = 'async'
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('图片解码失败，请换成 JPG / PNG 再试'))
      img.src = url
    })
    return img
  } finally {
    URL.revokeObjectURL(url)
  }
}

export async function prepareImage(file: File): Promise<PreparedImage> {
  if (!file.type.startsWith('image/')) {
    throw new Error('请选择图片文件（JPG / PNG / WebP）')
  }
  const img = await decodeImage(file)
  const width = img.width
  const height = img.height
  if (!width || !height) throw new Error('图片尺寸异常，请重新拍照')

  // 长条化验单（例如 1224×6502）按长边压到 2000px 会只剩 376px 宽，文字直接糊掉。
  // 改成「4MP 总像素 + 5000px 高」双上限，优先保住宽度。
  const scale = Math.min(1, Math.sqrt(MAX_PIXELS / (width * height)), MAX_HEIGHT / height)
  const cw = Math.max(1, Math.round(width * scale))
  const ch = Math.max(1, Math.round(height * scale))

  const canvas = document.createElement('canvas')
  canvas.width = cw
  canvas.height = ch
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('当前浏览器无法处理图片（canvas 不可用）')
  ctx.drawImage(img as CanvasImageSource, 0, 0, cw, ch)
  if (img instanceof ImageBitmap) img.close()

  let quality = 0.9
  let dataUrl = canvas.toDataURL('image/jpeg', quality)
  while (dataUrl.length > MAX_BASE64_CHARS && quality > 0.55) {
    quality -= 0.1
    dataUrl = canvas.toDataURL('image/jpeg', quality)
  }

  const base64 = dataUrl.slice(dataUrl.indexOf(',') + 1)
  return {
    dataUrl,
    base64,
    width: cw,
    height: ch,
    bytes: Math.round(base64.length * 0.75),
  }
}

export async function requestOcr(
  prepared: PreparedImage,
  cardHint: string,
  signal?: AbortSignal,
): Promise<OcrApiResult> {
  const resp = await fetch('/api/ocr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: prepared.base64, card_hint: cardHint }),
    signal,
  })
  if (resp.status === 413) throw new Error('图片过大被服务器拒绝，请压缩后重试')
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`接口返回 ${resp.status}${text ? '：' + text.slice(0, 120) : ''}`)
  }
  return (await resp.json()) as OcrApiResult
}