/**
 * API service for SSO / OIDC resources.
 *
 * Public SSO flow endpoints (`/auth/sso/*`) and admin provider CRUD
 * (`/admin/sso/*`). Self-service identity endpoints live under `/user/me/*`
 * and are exposed via usersApi (listMyIdentities / deleteMyIdentity) — kept
 * there because they're auth-adjacent rather than SSO-flow-specific.
 */
import { api } from './api'

export const ssoApi = {
  // ── Admin: provider CRUD ──
  listProviders() {
    return api.get('/admin/sso/providers')
  },
  createProvider(payload) {
    return api.post('/admin/sso/providers', payload)
  },
  updateProvider(providerId, payload) {
    return api.patch(`/admin/sso/providers/${providerId}`, payload)
  },
  deleteProvider(providerId) {
    return api.delete(`/admin/sso/providers/${providerId}`)
  },
}

/**
 * Build the backend SSO login URL for a provider slug. The browser navigates
 * here directly (full-page redirect to the IdP), so it must be an absolute URL
 * — in dev that's the backend origin, in prod the relative path is proxied.
 */
export function ssoLoginUrl(slug, redirect = '/') {
  const base = api.defaults.baseURL.replace(/\/$/, '')
  const params = new URLSearchParams({ redirect })
  return `${base}/auth/sso/${slug}/login?${params.toString()}`
}
