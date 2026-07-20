// Locale management — mirrors the darkMode pattern in AppLayout: the active
// locale is persisted to localStorage and reflected on <html lang>. Non-default
// catalogs are lazy-loaded (dynamic import) so the initial bundle only ships the
// active language plus the eager `en` fallback.
import { computed } from 'vue'
import {
  i18n,
  persistLocale,
  SUPPORTED_LOCALES,
  type MessageSchema,
  type SupportedLocale,
} from '@/i18n'

const messageLoaders: Record<SupportedLocale, () => Promise<{ default: MessageSchema }>> = {
  en: () => import('@/locales/en.json'),
  de: () => import('@/locales/de.json'),
  fr: () => import('@/locales/fr.json'),
  es: () => import('@/locales/es.json'),
}

// `en` is bundled eagerly by i18n/index.ts, so it starts out loaded.
const loaded = new Set<SupportedLocale>(['en'])

async function loadLocaleMessages(locale: SupportedLocale): Promise<void> {
  if (loaded.has(locale)) return
  const mod = await messageLoaders[locale]()
  i18n.global.setLocaleMessage(locale, mod.default)
  loaded.add(locale)
}

/**
 * Load (if needed) and activate a locale.
 * @param persist  whether to remember the choice (true for explicit user
 *                 selection, false for boot-time auto-detection).
 */
export async function applyLocale(locale: SupportedLocale, persist = true): Promise<void> {
  await loadLocaleMessages(locale)
  i18n.global.locale.value = locale
  document.documentElement.setAttribute('lang', locale)
  if (persist) persistLocale(locale)
}

export function useLocale() {
  const locale = computed<SupportedLocale>(() => i18n.global.locale.value as SupportedLocale)

  return {
    locale,
    supportedLocales: SUPPORTED_LOCALES,
    setLocale: (next: SupportedLocale) => applyLocale(next, true),
  }
}
