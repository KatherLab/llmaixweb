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
export function extractErrorMessage(err, fallback = 'Something went wrong') {
  if (!err) return fallback

  // Axios-style error with a response body
  const response = err.response
  if (response?.data) {
    const detail = response.data.detail
    if (typeof detail === 'string' && detail.trim()) return detail

    const message = response.data.message
    if (typeof message === 'string' && message.trim()) return message

    // FastAPI validation errors return a list of { msg } objects
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0]
      if (first?.msg) return first.msg
    }
  }

  if (typeof err.message === 'string' && err.message.trim()) return err.message

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
export function describeHttpError(err, operation) {
  const detail = extractErrorMessage(err, '')

  if (!err?.response) {
    return `Network error during ${operation}. Please check your connection and try again.`
  }

  switch (err.response.status) {
    case 400:
      return `${operation} failed: ${detail || err.message}`
    case 403:
      return `Permission denied: You don't have access to ${operation.toLowerCase()}.`
    case 404:
      return `Resource not found during ${operation}. Please refresh and try again.`
    case 500:
      return `Server error during ${operation}. Please try again later or contact support.`
    default:
      return `${operation} failed: ${detail || err.message}`
  }
}
