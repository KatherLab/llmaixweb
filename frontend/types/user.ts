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
  last_login_at: ISODateString | null
  has_sso?: boolean | null
}

export interface UserCreate {
  email: string
  password: string
  full_name: string
  invitation_token?: string | null
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
