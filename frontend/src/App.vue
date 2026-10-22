<template>
  <div class="doctor-workbench">
    <!-- 顶部导航栏 -->
    <header class="header">
      <h2>PCI 术后用药 AI 辅助决策工作台</h2>
      <div class="user-info">当前医生：王医生</div>
    </header>

    <!-- 三分屏 -->
    <main class="main-content">
      <!-- 左侧：患者档案 --> 
      <aside class="left-panel">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>患者档案</span>
            </div>
          </template>
           <el-form label-width="80px">
            <el-form-item label="姓名">
              <el-input v-model="patientName"></el-input>
            </el-form-item>
            <el-form-item label="术后时长">
              <el-input-number v-model="postPciMonths"></el-input-number>
            </el-form-item>
            <el-form-item label="当前用药">
              <el-input v-model="currentMeds" type="textarea"></el-input>
            </el-form-item>
            <el-form-item label="近期症状">
              <el-input v-model="symptoms" type="textarea"></el-input>
            </el-form-item>
          </el-form>
        </el-card>
      </aside>

      <!-- 中间：AI 交互区 -->
      <section class="center-panel">
        <el-card class="box-card">
          <template #header>
            <span>AI 智能助手建议</span>
          </template>
          <!-- 这放聊天框或建议列表 -->
          <div class="chat-area">
            <div v-for="(msg, index) in chatMessages" :key="index" :class="['message', msg.role]">
              <strong>{{ msg.role === 'ai' ? 'AI 助手' : '医生' }}：</strong>
              <span>{{ msg.text }}</span>
            </div>
          </div>
          <!-- 底部输入框 -->
          <div class="input-area">
            <el-input v-model="inputText" placeholder="请输入患者主诉或问题..." />
            <el-button type="primary" style="margin-left: 10px;"@click="handleSend">发送</el-button>
          </div>
        </el-card>
      </section>

      <!-- 右侧：证据溯源与审核区 -->
      <aside class="right-panel">
        <el-card class="box-card">
          <template #header>
            <span>证据溯源 & 审核</span>
          </template>
          <div class="evidence-content">
            <p><strong>引用指南：</strong>《经皮冠状动脉介入治疗指南（2025）》</p>
            <p><strong>原文片段：</strong>对于高出血风险患者，DAPT 疗程可缩短至 1~3 个月...</p>
            <el-divider />
            <el-button type="success">采纳建议</el-button>
            <el-button type="danger">驳回修改</el-button>
          </div>
        </el-card>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// 顶部医生名字
const doctorName = ref('王医生')

// 中间
const inputText = ref('')

// 左侧患者档案
const patientName = ref('李某某')
const postPciMonths = ref(7)
const currentMeds = ref('阿司匹林 + 氯吡格雷')
const symptoms = ref('牙龈出血')
const handleSend = () => {
  if (inputText.value.trim() === '') {
    alert('请先输入问题！')
    return
  }
  
  // 医生的话存进列表
  chatMessages.value.push({ role: 'user', text: inputText.value })
  
  // 模拟 AI 的回复（以后这里换成发给后端）
  setTimeout(() => {
    chatMessages.value.push({ role: 'ai', text: '收到您的提问：' + inputText.value + '。AI 正在思考中...' })
  }, 500) // 延迟0.5秒，假装 AI 在想
  
  // 清空输入框
  inputText.value = ''
}

// 定义聊天记录列表，初始有一个 AI 的欢迎语
const chatMessages = ref([
  { role: 'ai', text: '您好，我是 PCI 术后用药助手，请问有什么可以帮您？' }
])
</script>

<style scoped>
.doctor-workbench {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

.header {
  height: 60px;
  background-color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.main-content {
  flex: 1;
  display: flex;
  padding: 20px;
  gap: 20px;
  overflow: hidden;
}

.left-panel {
  width: 25%;
}

.center-panel {
  width: 45%;
}

.right-panel {
  width: 30%;
}

.box-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.chat-area {
  flex: 1;
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
}

.input-area {
  margin-top: 15px;
  display: flex;
}
</style>

.message {
  margin-bottom: 10px;
  padding: 10px;
  border-radius: 6px;
}
.user { background-color: #e3f2fd; text-align: right; }
.ai { background-color: #fff; }