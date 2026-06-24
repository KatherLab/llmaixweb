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
