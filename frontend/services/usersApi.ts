/**
 * API service for user resources (`/user/*`).
 * Covers user CRUD, invitations, and the auth-adjacent flows that live
 * under `/user/*` (first-admin, password reset, invitation validation).
 */
import { api } from './api'
import type { SupportedLocale } from '@/i18n'
import type { ApiBody } from '@/types'
import type {
  FirstAdminCheckResponse,
  InvitationInfo,
  InvitationResponse,
  NotificationPreferences,
  NotificationPreferencesUpdate,
  PasswordChange,
  PasswordResetConfirm,
  PasswordSet,
  UserCreate,
  UserIdentityResponse,
  UserResponse,
  UserSelfUpdate,
  UserUpdateAdmin,
} from '@/types'

const URLENCODED = { 'Content-Type': 'application/x-www-form-urlencoded' }

export const usersApi = {
  list() {
    return api.get('/user') as Promise<ApiBody<UserResponse[]>>
  },
  me() {
    return api.get('/user/me') as Promise<ApiBody<UserResponse>>
  },
  /**
   * Update the signed-in user's own profile (display name only).
   *
   * Not `update()`: that hits the admin-only `PATCH /user/{id}`, which a
   * non-admin cannot call. Email is not self-editable — it is the sign-in
   * identity, so changing it is an administrator action in User management.
   */
  updateMe(payload: UserSelfUpdate) {
    return api.patch('/user/me', payload) as Promise<ApiBody<UserResponse>>
  },
  // Linked SSO identities (self-service)
  listMyIdentities() {
    return api.get('/user/me/identities') as Promise<ApiBody<UserIdentityResponse[]>>
  },
  deleteMyIdentity(identityId: number | string) {
    return api.delete(`/user/me/identities/${identityId}`) as Promise<ApiBody<unknown>>
  },
  // Notification settings (self-service)
  getNotificationPreferences() {
    return api.get('/user/me/notification-preferences') as Promise<ApiBody<NotificationPreferences>>
  },
  updateNotificationPreferences(payload: NotificationPreferencesUpdate) {
    return api.patch('/user/me/notification-preferences', payload) as Promise<
      ApiBody<NotificationPreferences>
    >
  },
  /**
   * Mirror the active UI locale onto the account so server-composed email
   * (which runs long after the request, in a Celery worker) can be localized.
   */
  updateLanguage(preferred_language: SupportedLocale) {
    return api.patch('/user/me/language', { preferred_language }) as Promise<ApiBody<UserResponse>>
  },
  create(payload: UserCreate) {
    return api.post('/user', payload) as Promise<ApiBody<UserResponse>>
  },
  update(userId: number | string, payload: UserUpdateAdmin) {
    return api.patch(`/user/${userId}`, payload) as Promise<ApiBody<UserResponse>>
  },
  setPassword(userId: number | string, payload: PasswordSet) {
    return api.post(`/user/${userId}/set-password`, payload) as Promise<ApiBody<unknown>>
  },
  changePassword(payload: PasswordChange) {
    return api.post('/user/change-password', payload) as Promise<ApiBody<unknown>>
  },
  delete(userId: number | string) {
    return api.delete(`/user/${userId}`) as Promise<ApiBody<unknown>>
  },

  // Invitations
  invite(formBody: URLSearchParams | string) {
    return api.post('/user/invite', formBody, { headers: URLENCODED }) as Promise<
      ApiBody<InvitationResponse>
    >
  },
  listInvitations() {
    return api.get('/user/invitations') as Promise<ApiBody<InvitationResponse[]>>
  },
  deleteInvitation(invitationId: number | string) {
    return api.delete(`/user/invitations/${invitationId}`) as Promise<ApiBody<unknown>>
  },
  validateInvitation(token: string) {
    return api.get(`/user/validate-invitation/${token}`) as Promise<ApiBody<InvitationInfo>>
  },

  // First-admin setup
  firstAdminCheck() {
    return api.get('/user/first-admin-check') as Promise<ApiBody<FirstAdminCheckResponse>>
  },
  createFirstAdmin(payload: UserCreate) {
    return api.post('/user/first-admin', payload) as Promise<ApiBody<UserResponse>>
  },

  // Password reset flow
  forgotPassword(email: string) {
    return api.post('/user/forgot-password', { email }) as Promise<ApiBody<unknown>>
  },
  validateResetToken(token: string) {
    return api.get(`/user/validate-reset-token/${token}`) as Promise<ApiBody<{ valid: boolean }>>
  },
  resetPassword(token: string, payload: Omit<PasswordResetConfirm, 'token'>) {
    return api.post(`/user/reset-password/${token}`, payload) as Promise<ApiBody<unknown>>
  },
}
