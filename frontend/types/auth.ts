import type { ISODateString } from './api'
import type { UserRole } from './enums'

/** Public settings returned pre-login by `GET /auth/settings` (raw dict, no Pydantic model). */
export interface PublicAuthSettings {
  banner_enabled: boolean
  banner_text: string
  banner_color: string
  require_invitation: boolean
  sso_enabled: boolean
  sso_providers: SsoProviderPublic[]
  mistral_ocr_enabled: boolean
  vision_ocr_enabled: boolean
  vision_ocr_model: string
  vision_ocr_prompt: string
  mistral_ocr_display_name: string
  mistral_ocr_display_subtitle: string
  vision_ocr_display_name: string
  vision_ocr_display_subtitle: string
  docling_serve_enabled: boolean
  docling_serve_display_name: string
  docling_serve_display_subtitle: string
}

/** Minimal provider info shown on the login page. */
export interface SsoProviderPublic {
  slug: string
  name: string
}

/** User object embedded in the login/refresh `Token` response. Matches `UserResponse`. */
export interface AuthTokenUser {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  last_login_at: ISODateString | null
  has_sso?: boolean | null
}

/** Response for `/login` and `/auth/refresh`. */
export interface TokenResponse {
  access_token: string
  token_type: string
  user: AuthTokenUser
  refresh_token?: string | null
}

/** Request body for `/auth/logout`. */
export interface LogoutRequest {
  refresh_token?: string | null
  everywhere?: boolean
}

/** Options accepted by `authStore.logout()`. */
export interface LogoutOptions {
  serverSide: boolean
  everywhere?: boolean
}
