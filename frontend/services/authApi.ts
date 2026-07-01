/**
 * API service for auth resources (`/auth/*`).
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type { PublicAuthSettings, TokenResponse } from '@/types'
import type { LogoutRequest } from '@/types'

const URLENCODED = { 'Content-Type': 'application/x-www-form-urlencoded' }

export const authApi = {
  // OAuth2 password flow: body is a URLSearchParams string, not JSON.
  login(formBody: URLSearchParams | string) {
    return api.post('/auth/login', formBody, {
      headers: URLENCODED,
    }) as Promise<ApiBody<TokenResponse>>
  },
  refresh(refreshToken: string) {
    return api.post('/auth/refresh', {
      refresh_token: refreshToken,
    }) as Promise<ApiBody<TokenResponse>>
  },
  logout(refreshToken: string | null, everywhere = false) {
    return api.post('/auth/logout', {
      refresh_token: refreshToken || null,
      everywhere,
    } satisfies LogoutRequest) as Promise<ApiBody<unknown>>
  },
  getSettings() {
    return api.get('/auth/settings') as Promise<ApiBody<PublicAuthSettings>>
  },
}
