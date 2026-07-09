/**
 * Audit trail + central error log types.
 *
 * Mirrors the backend Pydantic schemas in `schemas/audit.py` and the
 * `AuditAction` / `AuditOutcome` enums.
 */
import type { ISODateString } from './api'

export type AuditAction =
  // auth
  | 'login_success'
  | 'login_failure'
  | 'logout'
  | 'token_refresh'
  | 'password_change'
  | 'password_reset'
  | 'account_locked'
  | 'sso_login'
  // access (PHI)
  | 'document_view'
  | 'document_download'
  | 'file_download'
  | 'trial_result_view'
  | 'export'
  // mutations
  | 'create'
  | 'update'
  | 'delete'
  // egress
  | 'llm_extraction_call'
  | 'ocr_external_call'
  // admin
  | 'setting_change'
  | 'user_create'
  | 'user_role_change'
  | 'user_deactivate'
  | 'invitation_send'
  | 'sso_provider_change'

export type AuditOutcome = 'success' | 'failure' | 'denied'

export interface AuditLogEntry {
  id: number
  created_at: ISODateString
  actor_user_id: number | null
  actor_email: string | null
  actor_ip: string | null
  action: AuditAction
  resource_type: string | null
  resource_id: string | null
  project_id: number | null
  outcome: AuditOutcome
  detail: Record<string, unknown> | null
  request_id: string | null
}

export interface PaginatedAuditLogs {
  total: number
  limit: number
  offset: number
  items: AuditLogEntry[]
}

export interface ErrorLogEntry {
  id: number
  error_id: string
  created_at: ISODateString
  request_id: string | null
  actor_user_id: number | null
  actor_email: string | null
  method: string | null
  path: string | null
  status_code: number
  exception_type: string | null
  message: string | null
  traceback: string | null
}

export interface PaginatedErrorLogs {
  total: number
  limit: number
  offset: number
  items: ErrorLogEntry[]
}

export interface AuditLogQuery {
  action?: AuditAction
  outcome?: AuditOutcome
  actor_user_id?: number
  resource_type?: string
  project_id?: number
  request_id?: string
  start?: string
  end?: string
  limit?: number
  offset?: number
}
