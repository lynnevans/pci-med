<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, UserFilled } from '@element-plus/icons-vue'

const emit = defineEmits<{ (e: 'authenticated', user: any): void }>()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const displayName = ref('')
const loading = ref(false)
const error = ref('')

function switchMode(next: 'login' | 'register'): void {
  mode.value = next
  error.value = ''
}

async function submit(): Promise<void> {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请填写用户名和密码'
    return
  }
  if (mode.value === 'register' && password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    const resp = await fetch(`/api/auth/${mode.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value,
        display_name: displayName.value.trim(),
      }),
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) {
      error.value = data.error || `请求失败（${resp.status}）`
      return
    }
    ElMessage.success(mode.value === 'login' ? '登录成功' : '注册成功')
    emit('authenticated', data.user)
  } catch (e) {
    error.value = `无法连接服务器：${e instanceof Error ? e.message : String(e)}`
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <el-card class="auth-card" shadow="never">
      <div class="auth-brand">
        <div class="auth-icon"><el-icon :size="26"><UserFilled /></el-icon></div>
        <div>
          <h2>{{ mode === 'login' ? '医生登录' : '注册医生账号' }}</h2>
          <p>专为基层医生使用 · 每位使用者需先注册并登录</p>
        </div>
      </div>

      <div class="auth-tabs">
        <button :class="['auth-tab', { on: mode === 'login' }]" @click="switchMode('login')">登录</button>
        <button :class="['auth-tab', { on: mode === 'register' }]" @click="switchMode('register')">注册</button>
      </div>

      <el-form label-position="top" class="auth-form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="username" size="large" placeholder="3–32 位中英文、数字或下划线" autocomplete="username">
            <template #prefix><el-icon><UserFilled /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="姓名 / 科室（选填）">
          <el-input v-model="displayName" size="large" placeholder="用于报告复核医生抬头，可留空" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" size="large" type="password" show-password placeholder="至少 6 位" autocomplete="current-password">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="确认密码">
          <el-input v-model="confirmPassword" size="large" type="password" show-password placeholder="再次输入密码" autocomplete="new-password" />
        </el-form-item>

        <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="auth-error" />
        <el-button type="primary" size="large" class="auth-submit" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登录' : '注册并登录' }}
        </el-button>
      </el-form>

      <p class="auth-foot">
        {{ mode === 'login' ? '还没有账号？' : '已经有账号？' }}
        <button class="auth-link" @click="switchMode(mode === 'login' ? 'register' : 'login')">
          {{ mode === 'login' ? '注册医生账号' : '返回登录' }}
        </button>
      </p>
    </el-card>
  </div>
</template>

<style scoped>
.auth-wrap { max-width: 460px; margin: 38px auto 0; }
.auth-card { border: 1px solid var(--border); border-radius: 14px; }
.auth-brand { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.auth-icon { width: 46px; height: 46px; border-radius: 12px; background: var(--primary-50); color: var(--primary); display: flex; align-items: center; justify-content: center; }
.auth-brand h2 { margin: 0; font-size: 20px; color: var(--text); }
.auth-brand p { margin: 4px 0 0; font-size: 12.5px; color: var(--text-3); }
.auth-tabs { display: flex; gap: 6px; padding: 4px; background: #f1f5f9; border-radius: 9px; margin-bottom: 18px; }
.auth-tab { flex: 1; border: 0; background: transparent; padding: 8px; border-radius: 7px; color: var(--text-2); font-size: 14px; cursor: pointer; }
.auth-tab.on { background: #fff; color: var(--primary); font-weight: 700; box-shadow: 0 1px 4px rgba(15, 23, 42, .08); }
.auth-submit { width: 100%; margin-top: 4px; }
.auth-error { margin-bottom: 12px; }
.auth-foot { margin: 16px 0 0; text-align: center; font-size: 13px; color: var(--text-3); }
.auth-link { border: 0; background: none; color: var(--primary); cursor: pointer; font-size: 13px; padding: 0 2px; }
</style>
