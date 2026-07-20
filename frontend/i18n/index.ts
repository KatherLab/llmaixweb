// vue-i18n setup — the single i18n instance used across the app.
//
// Phase 1 uses the full ("esm-bundler") vue-i18n build (aliased in
// vite.config.js / vitest.config.ts) so message strings can be compiled at
// runtime without a separate precompile plugin. If bundle size becomes a
// concern, `@intlify/unplugin-vue-i18n` can precompile the catalogs and the
// alias can be dropped — no call-site changes required.
//
// `en` is bundled eagerly as the fallback/source-of-truth catalog; the other
// locales are lazy-loaded on demand (see composables/useLocale.ts).
import { createI18n } from 'vue-i18n'
import en from '@/locales/en.json'

export const SUPPORTED_LOCALES = ['en', 'de', 'fr', 'es'] as const
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

export const DEFAULT_LOCALE: SupportedLocale = 'en'

/** BCP-47 tags used for Intl date/number formatting per app locale. */
export const INTL_LOCALES: Record<SupportedLocale, string> = {
  en: 'en-US',
  de: 'de-DE',
  fr: 'fr-FR',
  es: 'es-ES',
}

const STORAGE_KEY = 'locale'

/** The message-catalog shape; every locale must mirror `en.json`. */
export type MessageSchema = typeof en

function isSupported(value: string | null | undefined): value is SupportedLocale {
  return !!value && (SUPPORTED_LOCALES as readonly string[]).includes(value)
}

/**
 * Resolve the initial locale: an explicit saved choice wins, then the browser
 * language (matched on its primary subtag), then the default.
 */
export function detectInitialLocale(): SupportedLocale {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (isSupported(saved)) return saved

  const navLang = (navigator.language || '').slice(0, 2).toLowerCase()
  if (isSupported(navLang)) return navLang

  return DEFAULT_LOCALE
}

export function persistLocale(locale: SupportedLocale): void {
  localStorage.setItem(STORAGE_KEY, locale)
}

// Shared Intl format presets, applied to every supported locale so `$d`/`$n`
// render consistently. The separators/ordering adapt to the active locale.
const datetimeFormats = {
  short: { year: 'numeric', month: 'short', day: 'numeric' },
  long: {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  },
} as const

const numberFormats = {
  decimal: { style: 'decimal', maximumFractionDigits: 1 },
  percent: { style: 'percent', maximumFractionDigits: 1 },
} as const

const perLocale = <T>(value: T): Record<SupportedLocale, T> =>
  Object.fromEntries(SUPPORTED_LOCALES.map((l) => [l, value])) as Record<SupportedLocale, T>

export const i18n = createI18n({
  legacy: false,
  // Expose $t/$d/$n in every template without a per-component import.
  globalInjection: true,
  locale: detectInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: { en },
  datetimeFormats: perLocale(datetimeFormats),
  numberFormats: perLocale(numberFormats),
})
