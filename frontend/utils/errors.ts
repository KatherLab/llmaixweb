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

import { i18n } from '@/i18n'

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

/**
 * Localize a backend error code (i18n Phase 3). Migrated endpoints send a
 * structured `detail` of `{ code, message, params }`; if the code has a catalog
 * entry we render the translated string, otherwise the caller falls back to the
 * embedded English `message`.
 */
function localizeErrorCode(detail: { code?: unknown; params?: unknown }): string | null {
  const code = detail.code
  if (typeof code !== 'string' || !code.trim()) return null
  const key = `errors.${code}`
  if (!i18n.global.te(key)) return null
  const params =
    detail.params && typeof detail.params === 'object' && !Array.isArray(detail.params)
      ? (detail.params as Record<string, unknown>)
      : {}
  return i18n.global.t(key, params)
}

export function extractErrorMessage(
  err: unknown,
  fallback = i18n.global.t('errors.generic_fallback'),
): string {
  if (!err) return fallback

  // Axios-style error with a response body
  if (isAxiosLike(err)) {
    const response = err.response

    // 413 Payload Too Large: this can come from the backend (JSON detail with a
    // raw byte count) OR from the nginx proxy (an HTML body, which none of the
    // parsing below can read — it would otherwise fall through to axios's
    // opaque "Request failed with status code 413"). Return one friendly,
    // actionable message for both.
    if (response?.status === 413) {
      return i18n.global.t('errors.file_too_large')
    }

    if (response?.data) {
      // Our global 500 handler returns { error_id, message, detail }. Surface
      // the correlation id so the user can quote it to an admin — it takes
      // precedence over the generic "Internal server error." detail string.
      const errorId = response.data.error_id
      if (typeof errorId === 'string' && errorId.trim()) {
        const msg = response.data.message
        const base =
          typeof msg === 'string' && msg.trim() ? msg : i18n.global.t('errors.unexpected')
        return base.includes(errorId)
          ? base
          : `${base}${i18n.global.t('errors.error_id_suffix', { id: errorId })}`
      }

      const detail = response.data.detail
      if (typeof detail === 'string' && detail.trim()) return detail

      // Structured detail objects carry the human-readable text in
      // `detail.message`. A migrated endpoint (i18n Phase 3) also sends a stable
      // `detail.code`; if that code has a catalog entry we render the localized
      // string, otherwise we fall back to the embedded English `message`.
      if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        const localized = localizeErrorCode(detail as { code?: unknown; params?: unknown })
        if (localized !== null) return localized

        const dmsg = (detail as { message?: unknown }).message
        const did = (detail as { error_id?: unknown }).error_id
        if (typeof dmsg === 'string' && dmsg.trim()) {
          if (typeof did === 'string' && did.trim() && !dmsg.includes(did)) {
            return `${dmsg}${i18n.global.t('errors.error_id_suffix', { id: did })}`
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
  const { t } = i18n.global

  if (!isAxiosLike(err) || !err?.response) {
    return t('errors.http.network', { operation })
  }

  const message = typeof err.message === 'string' ? err.message : ''

  switch (err.response.status) {
    case 400:
      return t('errors.http.bad_request', { operation, detail: detail || message })
    case 403:
      return t('errors.http.forbidden', { operation: operation.toLowerCase() })
    case 404:
      return t('errors.http.not_found', { operation })
    case 500:
      return t('errors.http.server', { operation })
    default:
      return t('errors.http.generic', { operation, detail: detail || message })
  }
}
