/**
 * API service for file resources (`/project/{projectId}/file/*`).
 */
import { api } from './api'
import type { ApiBody, BlobResponse } from '@/types'
import type { File, FileFilter, PaginatedFiles } from '@/types'

const MULTIPART = { 'Content-Type': 'multipart/form-data' }

/** Tabular preview rows (CSV/XLSX) returned by `GET /file/{id}/preview-rows`.
 *
 * `rows` is a 2D array (row → cell values), not an array of row objects.
 * `sheets` and `detected_*` keys are only present for XLSX / CSV respectively.
 */
export interface FilePreviewRows {
  headers: (string | null)[]
  rows: (string | number | boolean | null)[][]
  total_rows: number
  truncated: boolean
  /** CSV only. */
  detected_delimiter?: string
  detected_encoding?: string
  /** XLSX only. */
  sheets?: string[]
}

export const filesApi = {
  list(projectId: number | string, params: FileFilter = {}) {
    return api.get(`/project/${projectId}/file`, {
      params,
    }) as Promise<ApiBody<PaginatedFiles>>
  },
  get(projectId: number | string, fileId: number | string) {
    return api.get(`/project/${projectId}/file/${fileId}`) as Promise<ApiBody<File>>
  },
  delete(projectId: number | string, fileId: number | string) {
    return api.delete(`/project/${projectId}/file/${fileId}`) as Promise<ApiBody<unknown>>
  },

  // Multipart upload. `formData` must include the File + a `file_info` JSON string.
  // Callers upload one file per request (sequential loop); no progress callback is used.
  upload(projectId: number | string, formData: FormData) {
    return api.post(`/project/${projectId}/file`, formData, {
      headers: MULTIPART,
    }) as Promise<ApiBody<File>>
  },
  configure(projectId: number | string, fileId: number | string, payload: Record<string, unknown>) {
    return api.post(`/project/${projectId}/file/${fileId}/configure`, payload) as Promise<
      ApiBody<File>
    >
  },

  // Raw file content as a blob (download or preview).
  getContent(projectId: number | string, fileId: number | string, params: FileFilter = {}) {
    return api.get(`/project/${projectId}/file/${fileId}/content`, {
      params,
      responseType: 'blob',
    }) as Promise<BlobResponse>
  },
  // Tabular preview rows (CSV/XLSX).
  getPreviewRows(projectId: number | string, fileId: number | string, params: FileFilter = {}) {
    return api.get(`/project/${projectId}/file/${fileId}/preview-rows`, {
      params,
    }) as Promise<ApiBody<FilePreviewRows>>
  },
}
