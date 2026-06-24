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
  getSettings() {
    return api.get('/auth/settings')
  },
}
