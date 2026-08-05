import type { SupportedLocale } from '@/i18n'
import type { ISODateString } from './api'
import type { UserRole } from './enums'

/** Public user slice embedded in Project.owner etc. */
export interface UserPublic {
  id: number
  full_name: string
  email: string
}

/** Full user record returned by admin/user endpoints. */
export interface UserResponse {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  /** UI locale, mirrored from the language switcher; notification email uses it. */
  preferred_language?: SupportedLocale | null
  last_login_at: ISODateString | null
  has_sso?: boolean | null
  // Whether this user may access projects they don't own (admin + the
  // ADMIN_ALL_PROJECT_ACCESS deployment flag). Populated by `/me`.
  can_access_all_projects?: boolean
}

export interface UserCreate {
  email: string
  password: string
  full_name: string
  invitation_token?: string | null
}

/**
 * The fields a user may change about their own account (`PATCH /user/me`).
 * Mirrors the backend allowlist — email is absent on purpose.
 */
export interface UserSelfUpdate {
  full_name: string
}

export interface UserUpdateAdmin {
  full_name?: string | null
  email?: string | null
  role?: UserRole | null
  is_active?: boolean | null
}

export interface PasswordChange {
  old_password: string
  new_password: string
}

export interface PasswordSet {
  new_password: string
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirm {
  token: string
  new_password: string
}

export interface PasswordResetValidate {
  valid: boolean
}

export interface InvitationResponse {
  id: number
  email: string
  token: string
  is_used: boolean
  email_sent: boolean
  created_at: ISODateString | null
  expires_at: ISODateString | null
}

export interface InvitationInfo {
  valid: boolean
  email: string | null
}

/** Response for `GET /users/first-admin-check`. */
export interface FirstAdminCheckResponse {
  allow_first_admin_setup: boolean
}

/**
 * Effective notification settings for the current user (`GET
 * /user/me/notification-preferences`). Always present — users who never touched
 * the settings get the server defaults.
 */
export interface NotificationPreferences {
  /** Preprocessing tasks and extraction runs reaching a terminal state. */
  job_finished: boolean
  /** Being granted access to a project, or having that access changed. */
  project_shared: boolean
  /** Password changes, account lockouts, SSO identities linked/unlinked. */
  security: boolean
  /** Operational alerts. Only ever sent to admins. */
  admin_alerts: boolean
  /** Suppress job email while a WebSocket session is open. */
  only_when_away: boolean
  /** Per-user minimum job duration; null means use the server default. */
  min_job_seconds: number | null
  /** Not a preference: whether this instance can send email at all. */
  email_configured: boolean
}

export type NotificationPreferencesUpdate = Partial<
  Omit<NotificationPreferences, 'email_configured'>
>

/** Response for `POST /admin/settings/test-email`. */
export interface TestEmailResponse {
  sent: boolean
  recipient: string | null
}
