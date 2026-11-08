import './index.css'

import { createApp } from 'vue'
import { FrappeUI, setConfig, frappeRequest } from 'frappe-ui'
import App from './App.vue'
import router from './router'

setConfig('resourceFetcher', frappeRequest)

createApp(App).use(FrappeUI).use(router).mount('#app')
