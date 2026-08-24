import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { toast } from 'vue-sonner'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

/**
 * Last-resort error handling: anything that escapes component/store
 * boundaries gets logged for diagnosis and surfaced once as a toast,
 * throttled so an error loop cannot flood the UI.
 */
let lastErrorToastAt = 0
function reportUnexpected(err: unknown, source: string) {
  console.error(`[genesis:${source}]`, err)
  const now = Date.now()
  if (now - lastErrorToastAt < 5000) return
  lastErrorToastAt = now
  toast.error('Something went wrong. Completed work is saved; try the action again.')
}

app.config.errorHandler = (err) => reportUnexpected(err, 'vue')
window.addEventListener('unhandledrejection', (event) => {
  event.preventDefault()
  reportUnexpected(event.reason, 'promise')
})

app.mount('#app')
