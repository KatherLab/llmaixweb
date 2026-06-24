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
  running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400',
  completed: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
  success: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
  failed: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
  error: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
  cancelled: 'bg-gray-200 dark:bg-slate-700 text-gray-500 dark:text-gray-400',
  canceled: 'bg-gray-200 dark:bg-slate-700 text-gray-500 dark:text-gray-400',
  partial: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400',
}

const DEFAULT_STATUS_STYLE = 'bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-gray-400'

export function getStatusBadgeClass(status) {
  if (!status) return DEFAULT_STATUS_STYLE
  return STATUS_STYLES[status] || DEFAULT_STATUS_STYLE
}

/**
 * Generic dark-mode-aware color map for semantic pills (counts, "active",
 * match/mismatch, extraction method, filter chips, …). Shared by FilterChip,
 * StatusBadge, ExtractionMethodBadge and any hand-rolled pill so colors and
 * dark-mode variants stay consistent.
 *
 * @param {string} color - One of: blue|green|yellow|red|purple|indigo|teal|cyan|orange|gray
 * @returns {string} Tailwind class string
 */
const PILL_COLORS = {
  blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  green: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
  yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
  red: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
  purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  indigo: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
  teal: 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300',
  cyan: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300',
  orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
  gray: 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300',
}

const DEFAULT_PILL_COLOR = PILL_COLORS.gray

export function getPillClass(color) {
  return PILL_COLORS[color] || DEFAULT_PILL_COLOR
}

export { STATUS_STYLES, DEFAULT_STATUS_STYLE, PILL_COLORS, DEFAULT_PILL_COLOR }
