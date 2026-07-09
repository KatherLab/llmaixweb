/**
 * API service for the audit trail and central error log (`/admin/audit`,
 * `/admin/errors`). Admin-only, read-only.
 */
import { api } from './api'
import type { ApiBody, BlobResponse } from '@/types'
import type { AuditLogQuery, PaginatedAuditLogs, PaginatedErrorLogs } from '@/types'

export const auditApi = {
  list(params: AuditLogQuery = {}) {
    return api.get('/admin/audit', { params }) as Promise<ApiBody<PaginatedAuditLogs>>
  },
  exportCsv(params: AuditLogQuery = {}) {
    return api.get('/admin/audit/export', {
      params,
      responseType: 'blob',
    }) as Promise<BlobResponse>
  },
  listErrors(params: { error_id?: string; limit?: number; offset?: number } = {}) {
    return api.get('/admin/errors', { params }) as Promise<ApiBody<PaginatedErrorLogs>>
  },
}
