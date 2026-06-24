/**
 * API service for user resources (`/user/*`).
 * Covers user CRUD, invitations, and the auth-adjacent flows that live
 * under `/user/*` (first-admin, password reset, invitation validation).
 */
import { api } from './api'

const URLENCODED = { 'Content-Type': 'application/x-www-form-urlencoded' }

export const usersApi = {
  list() {
    return api.get('/user')
  },
  me() {
    return api.get('/user/me')
  },
  create(payload) {
    return api.post('/user', payload)
  },
  update(userId, payload) {
    return api.patch(`/user/${userId}`, payload)
  },
  setPassword(userId, payload) {
    return api.post(`/user/${userId}/set-password`, payload)
  },
  changePassword(payload) {
    return api.post('/user/change-password', payload)
  },
  delete(userId) {
    return api.delete(`/user/${userId}`)
  },

  // Invitations
  invite(formBody) {
    return api.post('/user/invite', formBody, { headers: URLENCODED })
  },
  listInvitations() {
    return api.get('/user/invitations')
  },
  deleteInvitation(invitationId) {
    return api.delete(`/user/invitations/${invitationId}`)
  },
  validateInvitation(token) {
    return api.get(`/user/validate-invitation/${token}`)
  },

  // First-admin setup
  firstAdminCheck() {
    return api.get('/user/first-admin-check')
  },
  createFirstAdmin(payload) {
    return api.post('/user/first-admin', payload)
  },

  // Password reset flow
  forgotPassword(email) {
    return api.post('/user/forgot-password', { email })
  },
  validateResetToken(token) {
    return api.get(`/user/validate-reset-token/${token}`)
  },
  resetPassword(token, payload) {
    return api.post(`/user/reset-password/${token}`, payload)
  },
}
