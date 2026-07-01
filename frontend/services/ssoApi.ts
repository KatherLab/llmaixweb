/**
 * API service for SSO / OIDC resources.
 *
 * Public SSO flow endpoints (`/auth/sso/*`) and admin provider CRUD
 * (`/admin/sso/*`). Self-service identity endpoints live under `/user/me/*`
 * and are exposed via usersApi (listMyIdentities / deleteMyIdentity) — kept
 * there because they're auth-adjacent rather than SSO-flow-specific.
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type {
  IdentityProviderCreate,
  IdentityProviderResponse,
  IdentityProviderUpdate,
} from '@/types'

export const ssoApi = {
  // ── Admin: provider CRUD ──
  listProviders() {
    return api.get('/admin/sso/providers') as Promise<ApiBody<IdentityProviderResponse[]>>
  },
  createProvider(payload: IdentityProviderCreate) {
    return api.post('/admin/sso/providers', payload) as Promise<ApiBody<IdentityProviderResponse>>
  },
  updateProvider(providerId: number | string, payload: IdentityProviderUpdate) {
    return api.patch(`/admin/sso/providers/${providerId}`, payload) as Promise<
      ApiBody<IdentityProviderResponse>
    >
  },
  deleteProvider(providerId: number | string) {
    return api.delete(`/admin/sso/providers/${providerId}`) as Promise<ApiBody<unknown>>
  },
}

/**
 * Build the backend SSO login URL for a provider slug. The browser navigates
 * here directly (full-page redirect to the IdP), so it must be an absolute URL
 * — in dev that's the backend origin, in prod the relative path is proxied.
 */
export function ssoLoginUrl(slug: string, redirect = '/'): string {
  const base = (api.defaults.baseURL ?? '').replace(/\/$/, '')
  const params = new URLSearchParams({ redirect })
  return `${base}/auth/sso/${slug}/login?${params.toString()}`
}
