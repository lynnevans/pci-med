import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './app.css'
import AppV2 from './AppV2.vue'

createApp(AppV2).use(ElementPlus).mount('#app')