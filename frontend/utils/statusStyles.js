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

export { STATUS_STYLES, DEFAULT_STATUS_STYLE }
