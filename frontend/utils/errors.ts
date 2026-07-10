/**
 * Shared error-message extraction for API errors.
 *
 * Normalizes the various shapes a backend/axios error can take into a single
 * human-readable string. Replaces the ~47 copy-pasted
 * `err.response?.data?.detail || err.message || 'fallback'` chains scattered
 * across components (which had inconsistent fallback order).
 *
 * @param {unknown} err - The caught error
 * @param {string} [fallback='Something went wrong'] - Fallback message
 * @returns {string} Extracted message
 */

/** A minimal Axios-like error shape (only the fields we inspect). */
interface AxiosLikeError {
  message?: string
  response?: {
    status?: number
    data?: {
      detail?: unknown
      message?: unknown
      error_id?: unknown
    }
  }
}

function isAxiosLike(err: unknown): err is AxiosLikeError {
  return typeof err === 'object' && err !== null
}

export function extractErrorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (!err) return fallback

  // Axios-style error with a response body
  if (isAxiosLike(err)) {
    const response = err.response
    if (response?.data) {
      // Our global 500 handler returns { error_id, message, detail }. Surface
      // the correlation id so the user can quote it to an admin — it takes
      // precedence over the generic "Internal server error." detail string.
      const errorId = response.data.error_id
      if (typeof errorId === 'string' && errorId.trim()) {
        const msg = response.data.message
        const base = typeof msg === 'string' && msg.trim() ? msg : `An unexpected error occurred.`
        return base.includes(errorId) ? base : `${base} (Error ID: ${errorId})`
      }

      const detail = response.data.detail
      if (typeof detail === 'string' && detail.trim()) return detail

      // Structured detail objects (e.g. our 409 `{ message, links }`, or a
      // caught-500 `{ error_id, message }`) carry the human-readable text in
      // `detail.message`; when an `error_id` is present, append it so the user
      // can quote it to an admin.
      if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        const dmsg = (detail as { message?: unknown }).message
        const did = (detail as { error_id?: unknown }).error_id
        if (typeof dmsg === 'string' && dmsg.trim()) {
          if (typeof did === 'string' && did.trim() && !dmsg.includes(did)) {
            return `${dmsg} (Error ID: ${did})`
          }
          return dmsg
        }
      }

      const message = response.data.message
      if (typeof message === 'string' && message.trim()) return message

      // FastAPI validation errors return a list of { msg } objects
      if (Array.isArray(detail) && detail.length) {
        const first = detail[0]
        if (first && typeof first === 'object' && 'msg' in first) {
          const msg = (first as { msg: unknown }).msg
          if (typeof msg === 'string') return msg
        }
      }
    }

    if (typeof err.message === 'string' && err.message.trim()) return err.message
  }

  return fallback
}

/**
 * Describe an API error in the context of a user-facing operation.
 *
 * Maps common HTTP status codes to actionable messages, falling back to the
 * extracted detail. Replaces the copy-pasted `err.response.status` switches in
 * EvaluationView / TrialSelectorModal (and similar). Returns a string suitable
 * for toasts / error banners.
 *
 * @param {unknown} err - The caught error
 * @param {string} operation - Human-readable operation name (e.g. "Loading trials")
 * @returns {string} Human-readable error message
 */
export function describeHttpError(err: unknown, operation: string): string {
  const detail = extractErrorMessage(err, '')

  if (!isAxiosLike(err) || !err?.response) {
    return `Network error during ${operation}. Please check your connection and try again.`
  }

  const message = typeof err.message === 'string' ? err.message : ''

  switch (err.response.status) {
    case 400:
      return `${operation} failed: ${detail || message}`
    case 403:
      return `Permission denied: You don't have access to ${operation.toLowerCase()}.`
    case 404:
      return `Resource not found during ${operation}. Please refresh and try again.`
    case 500:
      return `Server error during ${operation}. Please try again later or contact support.`
    default:
      return `${operation} failed: ${detail || message}`
  }
}
