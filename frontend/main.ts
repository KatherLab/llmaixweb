import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { i18n, type SupportedLocale } from './i18n'
import { applyLocale } from './composables/useLocale'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(router)

// Load the detected locale's catalog (and set <html lang>) before mount so the
// first paint is already localized. The locale defaults to the system/browser
// language (see detectInitialLocale in i18n/index.ts) unless the user has saved
// an explicit choice — we don't persist the auto-detected value here, only an
// explicit switch persists. `en` is bundled eagerly so this resolves
// synchronously for English; other locales resolve after a small dynamic import.
applyLocale(i18n.global.locale.value as SupportedLocale, false).finally(() => {
  app.mount('#app')
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled Promise Rejection:', event.reason)
})
