/**
 * Shared status -> Tailwind class maps for task/trial/preprocessing statuses.
 * Use with StatusBadge.vue (pill) or directly via getStatusBadgeClass(status).
 *
 * All variants include dark-mode styles so badges render correctly in both themes.
 */

const STATUS_STYLES = {
  // Trial / task statuses
  pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400',
  processing: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400',
  in_progress: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400',
  running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400',
  completed: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
  success: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
  failed: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
  error: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
  cancelled: 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400',
  canceled: 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400',
  partial: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400',
}

const DEFAULT_STATUS_STYLE = 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-400'

/**
 * Normalize a raw task status string to the canonical key used in STATUS_STYLES.
 * Handles common variants (in_progress, canceled) so callers can pass the raw
 * backend value directly.
 * @param {string} status
 * @returns {string}
 */
export function normalizeTaskStatus(status) {
  if (!status) return ''
  return String(status).toLowerCase()
}

export function getStatusBadgeClass(status) {
  const key = normalizeTaskStatus(status)
  if (!key) return DEFAULT_STATUS_STYLE
  return STATUS_STYLES[key] || DEFAULT_STATUS_STYLE
}

/**
 * Solid background color (bg-*-500) for a status indicator dot.
 * Mirrors the STATUS_STYLES color assignment (cancelled=gray, the app-wide
 * standard) so dots and badges stay in sync.
 */
const STATUS_DOT_COLORS = {
  pending: 'bg-yellow-500',
  processing: 'bg-blue-500',
  in_progress: 'bg-blue-500',
  running: 'bg-blue-500',
  completed: 'bg-green-500',
  success: 'bg-green-500',
  failed: 'bg-red-500',
  error: 'bg-red-500',
  cancelled: 'bg-slate-400',
  canceled: 'bg-slate-400',
  partial: 'bg-yellow-500',
}

const DEFAULT_DOT_COLOR = 'bg-slate-400'

export function getStatusDotClass(status) {
  const key = normalizeTaskStatus(status)
  if (!key) return DEFAULT_DOT_COLOR
  return STATUS_DOT_COLORS[key] || DEFAULT_DOT_COLOR
}

/**
 * Soft banner/box class (bg-*-50 border-*-200, dark-mode-aware) for a status.
 * Used by per-file task rows in PreprocessingHistoryPanel, etc.
 */
const STATUS_BANNER_COLORS = {
  pending: 'yellow',
  processing: 'blue',
  in_progress: 'blue',
  running: 'blue',
  completed: 'green',
  success: 'green',
  failed: 'red',
  error: 'red',
  cancelled: 'gray',
  canceled: 'gray',
  partial: 'yellow',
}

export function getStatusBannerClass(status) {
  const key = normalizeTaskStatus(status)
  if (!key) return getBannerClass('gray')
  return getBannerClass(STATUS_BANNER_COLORS[key] || 'gray')
}

/**
 * Generic dark-mode-aware color map for semantic pills (counts, "active",
 * match/mismatch, extraction method, filter chips, …). Shared by FilterChip,
 * StatusBadge, ExtractionMethodBadge and any hand-rolled pill so colors and
 * dark-mode variants stay consistent.
 *
 * @param {string} color - One of: blue|green|yellow|amber|red|pink|purple|teal|cyan|orange|gray
 * @returns {string} Tailwind class string
 */
const PILL_COLORS = {
  blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  green: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
  yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
  amber: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  red: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
  pink: 'bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-300',
  purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  teal: 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300',
  cyan: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300',
  orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
  gray: 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300',
}

const DEFAULT_PILL_COLOR = PILL_COLORS.gray

export function getPillClass(color) {
  return PILL_COLORS[color] || DEFAULT_PILL_COLOR
}

/**
 * Soft banner/box variant (bg-*-50 + border-*-200) for status callouts that
 * need more presence than a pill but less than ErrorBanner. Used by
 * ModelTestCard, PreprocessingHistoryPanel, etc.
 *
 * @param {string} color - Any key from BANNER_COLORS
 * @returns {string} Tailwind class string
 */
const BANNER_COLORS = {
  blue: 'bg-blue-50 border border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-300',
  green:
    'bg-green-50 border border-green-200 text-green-700 dark:bg-green-900/20 dark:border-green-800 dark:text-green-300',
  yellow:
    'bg-yellow-50 border border-yellow-200 text-yellow-700 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-300',
  amber:
    'bg-amber-50 border border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-300',
  red: 'bg-red-50 border border-red-200 text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300',
  pink: 'bg-pink-50 border border-pink-200 text-pink-700 dark:bg-pink-900/20 dark:border-pink-800 dark:text-pink-300',
  purple:
    'bg-purple-50 border border-purple-200 text-purple-700 dark:bg-purple-900/20 dark:border-purple-800 dark:text-purple-300',
  teal: 'bg-teal-50 border border-teal-200 text-teal-700 dark:bg-teal-900/20 dark:border-teal-800 dark:text-teal-300',
  cyan: 'bg-cyan-50 border border-cyan-200 text-cyan-700 dark:bg-cyan-900/20 dark:border-cyan-800 dark:text-cyan-300',
  orange:
    'bg-orange-50 border border-orange-200 text-orange-700 dark:bg-orange-900/20 dark:border-orange-800 dark:text-orange-300',
  gray: 'bg-slate-50 border border-slate-200 text-slate-700 dark:bg-slate-700/40 dark:border-slate-600 dark:text-slate-300',
}

const DEFAULT_BANNER_COLOR = BANNER_COLORS.gray

export function getBannerClass(color) {
  return BANNER_COLORS[color] || DEFAULT_BANNER_COLOR
}

export {
  STATUS_STYLES,
  DEFAULT_STATUS_STYLE,
  STATUS_DOT_COLORS,
  DEFAULT_DOT_COLOR,
  STATUS_BANNER_COLORS,
  PILL_COLORS,
  DEFAULT_PILL_COLOR,
  BANNER_COLORS,
}
