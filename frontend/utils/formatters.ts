/**
 * Format a date string to a readable format
 * @param {string} dateString - ISO date string
 * @param {boolean} includeTime - Whether to include time in the output
 * @returns {string} Formatted date string
 */
export function formatDate(dateString: string | null | undefined, includeTime = false): string {
  if (!dateString) return ''

  const date = new Date(dateString)

  if (isNaN(date.getTime())) {
    return 'Invalid date'
  }

  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }

  if (includeTime) {
    options.hour = '2-digit'
    options.minute = '2-digit'
  }

  return date.toLocaleDateString('en-US', options)
}

/**
 * Format file size to a human-readable string
 * @param {number} bytes - Size in bytes
 * @param {string} [fallback='0 B'] - Value returned when bytes is missing/invalid
 * @returns {string} Formatted size
 */
export function formatFileSize(bytes: number | null | undefined, fallback = '0 B'): string {
  if (!bytes || isNaN(bytes)) return fallback

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes

  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }

  return `${size.toFixed(1)} ${units[i]}`
}

/**
 * Truncates text to a specified length and adds ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length before truncating
 * @returns {string} Truncated text
 */
export function truncateText(text: string | null | undefined, maxLength = 100): string {
  if (!text) return ''

  if (text.length <= maxLength) {
    return text
  }

  return text.slice(0, maxLength) + '...'
}

/**
 * Format a duration in seconds as HH:MM:SS.
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration (e.g. "00:05:32")
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds || isNaN(seconds)) return '00:00:00'
  return new Date(seconds * 1000).toISOString().substring(11, 19)
}

/**
 * Format a date string with both date and time.
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date+time string
 */
export function formatDateTime(dateString: string | null | undefined): string {
  return formatDate(dateString, true)
}

/**
 * "Smart" date formatter: shows time-of-day for today, weekday for this week,
 * otherwise a short date. Replaces the per-component relative date formatters
 * that were inlined in FilesTable / similar.
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
export function formatDateSmart(dateString: string | null | undefined): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return 'Invalid date'

  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 86400000) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diff < 604800000) return date.toLocaleDateString([], { weekday: 'short' })
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

/**
 * Format a date string as a full locale string (date + time). Replaces the
 * per-component `new Date(x).toLocaleString()` wrappers.
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date+time string
 */
export function formatDateFull(dateString: string | null | undefined): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return ''
  return date.toLocaleString()
}

/**
 * Format a timestamp as a relative "time ago" string (e.g. "2m ago", "3h ago").
 * @param {string|number|Date} timestamp - The timestamp to format
 * @returns {string} Relative time string
 */
export function formatRelativeTime(timestamp: string | number | Date | null | undefined): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (isNaN(date.getTime())) return ''

  const diff = Math.max(0, Date.now() - date.getTime())
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 30) return `${days}d ago`
  return formatDate(timestamp instanceof Date ? timestamp.toISOString() : String(timestamp))
}
