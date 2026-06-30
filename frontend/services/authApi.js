/**
 * API service for auth resources (`/auth/*`).
 */
import { api } from './api'

const URLENCODED = { 'Content-Type': 'application/x-www-form-urlencoded' }

export const authApi = {
  // OAuth2 password flow: body is a URLSearchParams string, not JSON.
  login(formBody) {
    return api.post('/auth/login', formBody, { headers: URLENCODED })
  },
  refresh(refreshToken) {
    return api.post('/auth/refresh', { refresh_token: refreshToken })
  },
  logout(refreshToken, everywhere = false) {
    return api.post('/auth/logout', {
      refresh_token: refreshToken || null,
      everywhere,
    })
  },
  getSettings() {
    return api.get('/auth/settings')
  },
}
