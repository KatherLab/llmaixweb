import type { ISODateString } from './api'

/** Admin-managed OIDC identity provider (full record). */
export interface IdentityProviderResponse {
  id: number
  name: string
  slug: string
  issuer_url: string
  client_id: string
  scopes: string
  enabled: boolean
  has_secret: boolean
  created_at: ISODateString | null
  updated_at: ISODateString | null
}

export interface IdentityProviderCreate {
  name: string
  issuer_url: string
  client_id: string
  client_secret: string
  scopes: string
  enabled: boolean
}

export interface IdentityProviderUpdate {
  name?: string
  issuer_url?: string
  client_id?: string
  client_secret?: string
  scopes?: string
  enabled?: boolean
}

/** A connected SSO identity for the current user (`GET /users/me/identities`). */
export interface UserIdentityResponse {
  id: number
  provider_name: string
  external_subject: string
  created_at: ISODateString | null
  last_login_at: ISODateString | null
}
