<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { Promotion, InfoFilled } from '@element-plus/icons-vue'

interface Source {
  index: number
  tier: number
  source: string
}

interface ChatMsg {
  role: 'user' | 'ai'
  content: string
  sources?: Source[]
  pending?: boolean
}

const messages = ref<ChatMsg[]>([
  {
    role: 'ai',
    content:
      '你好，我是 PCI 术后用药问答助手。我的每条回答都只摘录指南原文并标注来源，绝不自由发挥。直接输入用药问题即可，例如：“替格瑞洛维持剂量是多少？”',
  },
])
const input = ref('')
const sending = ref(false)
const listRef = ref<HTMLElement | null>(null)

function scrollBottom(): void {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

async function send(): Promise<void> {
  const q = input.value.trim()
  if (!q || sending.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: q })
  const ai: ChatMsg = { role: 'ai', content: '', sources: [], pending: true }
  messages.value.push(ai)
  sending.value = true
  scrollBottom()

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    })
    if (!resp.ok || !resp.body) throw new Error('接口返回 ' + resp.status)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        const data = line.slice(5).trim()
        if (data === '[DONE]') continue
        try {
          const obj = JSON.parse(data)
          if (obj.type === 'sources') ai.sources = obj.data
          else if (obj.type === 'delta') { ai.content += obj.data; scrollBottom() }
          else if (obj.type === 'error') ai.content += '\n\n[提示] ' + obj.data
        } catch { /* 跳过不完整行 */ }
      }
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    ai.content += '\n\n[调用失败] ' + msg + '。请确认 uvicorn 已启动；首次问答需加载 bge-m3 向量模型，约几十秒，请稍候重试。'
  } finally {
    ai.pending = false
    sending.value = false
    scrollBottom()
  }
}
</script>

<template>
  <div class="chat">
    <div class="chat-tip">
      <el-icon :size="14"><InfoFilled /></el-icon>
      摘录式问答：AI 只引用指南原文并标注来源，绝不编造。首次提问需加载向量模型，约几十秒。
    </div>

    <div class="msg-list" ref="listRef">
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        <div class="bubble">
          <div class="content">{{ m.content }}<span v-if="m.pending" class="cursor">▍</span></div>
          <div v-if="m.sources && m.sources.length" class="sources">
            <div class="sources-title">指南溯源</div>
            <span v-for="s in m.sources" :key="s.index" class="src-chip">[{{ s.index }}] {{ s.source }}（Tier {{ s.tier }}）</span>
          </div>
        </div>
      </div>
    </div>

    <div class="input-bar">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        placeholder="输入用药问题，回车发送（Shift+回车换行）"
        @keydown.enter.exact.prevent="send"
      />
      <el-button type="primary" :loading="sending" class="send-btn" @click="send">
        <el-icon class="send-icon"><Promotion /></el-icon>发送
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; height: calc(100vh - 210px); min-height: 480px; background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden; }
.chat-tip { display: flex; align-items: center; gap: 6px; padding: 10px 18px; background: rgba(3,105,161,0.06); color: #0369a1; font-size: 12.5px; border-bottom: 1px solid #e2e8f0; }
.msg-list { flex: 1; overflow-y: auto; padding: 20px 18px; }
.msg { display: flex; margin-bottom: 18px; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 84%; padding: 12px 15px; border-radius: 12px; }
.msg.ai .bubble { background: #f1f5f9; border: 1px solid #e2e8f0; border-top-left-radius: 4px; }
.msg.user .bubble { background: #0369a1; color: #fff; border-top-right-radius: 4px; }
.content { white-space: pre-wrap; line-height: 1.7; font-size: 14.5px; word-break: break-word; }
.cursor { display: inline-block; color: #0369a1; animation: blink 1s infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
.sources { margin-top: 10px; padding-top: 10px; border-top: 1px dashed #cbd5e1; }
.sources-title { font-size: 12px; color: #64748b; margin-bottom: 6px; font-weight: 600; }
.src-chip { display: inline-block; font-size: 12px; color: #0369a1; background: rgba(3,105,161,0.08); border: 1px solid rgba(3,105,161,0.18); border-radius: 6px; padding: 3px 8px; margin: 0 6px 6px 0; }
.input-bar { display: flex; gap: 10px; padding: 14px 16px; border-top: 1px solid #e2e8f0; background: #f8fafc; align-items: flex-end; }
.input-bar :deep(.el-textarea__inner) { border-radius: 10px; }
.send-btn { height: 54px; padding: 0 22px; border-radius: 10px; flex-shrink: 0; }
.send-icon { margin-right: 4px; vertical-align: -2px; }
</style>