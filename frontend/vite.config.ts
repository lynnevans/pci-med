import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 局域网开发模式：其他电脑访问 http://<本机IP>:5173
    // 生产/演示更推荐 npm run build + 后端 8000 单端口托管（见 docs/局域网访问.md）
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      // 前端里 fetch('/api/...') 会走这里，转发到后端 8000，避免跨域
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})