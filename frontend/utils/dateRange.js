/**
 * Shared date-range preset logic for filter bars.
 * Used by TrialsManagement, FilesAndProcessing, DocumentsManagement.
 *
 * Presets: 'today' | 'yesterday' | 'week' (last 7 days) | 'month' (last 30 days) | 'custom'
 */

const DATE_RANGE_LABELS = {
  today: 'Today',
  yesterday: 'Yesterday',
  week: 'Last 7 Days',
  month: 'Last 30 Days',
  custom: 'Custom Range',
}

export function getDateRangeLabel(range) {
  return DATE_RANGE_LABELS[range] || range
}

/**
 * Compute { date_from, date_to } ISO bounds for a preset range.
 * For 'custom', pass customFrom/customTo (ISO date strings or Date objects).
 * @returns {{ date_from?: string, date_to?: string }}
 */
export function getDateRangeBounds(range, customFrom = null, customTo = null) {
  const now = new Date()
  const start = new Date(now)

  if (range === 'today') {
    start.setHours(0, 0, 0, 0)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  }
  if (range === 'yesterday') {
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    yesterday.setHours(0, 0, 0, 0)
    start.setHours(23, 59, 59, 999)
    return { date_from: yesterday.toISOString(), date_to: start.toISOString() }
  }
  if (range === 'week') {
    start.setDate(now.getDate() - 7)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  }
  if (range === 'month') {
    start.setDate(now.getDate() - 30)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  }
  if (range === 'custom' && customFrom) {
    const from = new Date(customFrom)
    from.setHours(0, 0, 0, 0)
    const to = customTo ? new Date(customTo) : now
    to.setHours(23, 59, 59, 999)
    return { date_from: from.toISOString(), date_to: to.toISOString() }
  }
  return {}
}

export { DATE_RANGE_LABELS }
