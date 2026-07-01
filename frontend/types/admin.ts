import type { QueryParams } from './api'

/** A single admin setting entry returned by `GET /admin/settings`. */
export interface AdminSettingEntry {
  key: string
  category: string
  label: string
  description: string
  type: 'str' | 'int' | 'bool' | string
  readonly: boolean
  secret: boolean
  is_set?: boolean | null
  original: string | null
  override: string | null
  effective: string | null
  overridden: boolean
}

/** `GET /admin/settings` → map of key → entry. */
export type AdminSettings = Record<string, AdminSettingEntry>

/** `PUT /admin/settings` body. */
export interface AdminSettingsUpdate {
  [key: string]: string | boolean | number | null
}

/** `DELETE /admin/settings/{key}` response. */
export interface AdminSettingDeleted {
  deleted: string
}

/** `PUT /admin/settings` response. */
export interface AdminSettingsUpdated {
  updated: boolean
}

/** Celery worker inspect result (highly dynamic). */
export interface CeleryWorkersResponse {
  active: Record<string, unknown>
  registered: Record<string, unknown>
  stats: Record<string, unknown>
  ping: Record<string, unknown>
}

export interface CeleryQueuesResponse {
  reserved: Record<string, unknown>
  scheduled: Record<string, unknown>
  active: Record<string, unknown>
}

export interface CeleryTaskRevokeResponse {
  revoked: string
  terminate: boolean
}

/** Celery admin query params. */
export type CeleryQuery = QueryParams
