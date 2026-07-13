/**
 * API service for file resources (`/project/{projectId}/file/*`).
 */
import { api } from './api'
import type { ApiBody, BlobResponse } from '@/types'
import type { File, FileDependencies, FileFilter, PaginatedFiles } from '@/types'

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

/** A single non-unique case-ID value found in the file. */
export interface IdColumnDuplicate {
  value: string
  count: number
  is_empty: boolean
}

/** Result of `POST /file/{id}/validate-id-column`. */
export interface IdColumnValidation {
  is_valid: boolean
  column_exists: boolean
  case_id_column?: string
  total_rows?: number
  duplicate_rows?: number
  duplicate_value_count?: number
  duplicates: IdColumnDuplicate[]
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
  delete(projectId: number | string, fileId: number | string, cascade = false) {
    // `cascade` maps to the backend `force` flag: delete the file's documents
    // and everything downstream (trials, groups, evaluations) along with it.
    return api.delete(`/project/${projectId}/file/${fileId}`, {
      params: cascade ? { force: true } : undefined,
    }) as Promise<ApiBody<unknown>>
  },
  // Preview what a cascade delete of these files would also remove.
  checkDependencies(projectId: number | string, fileIds: number[]) {
    return api.post(`/project/${projectId}/file/dependencies`, {
      file_ids: fileIds,
    }) as Promise<ApiBody<FileDependencies>>
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
  // Validate that a row-by-row import's case-ID column is unique across the
  // whole file. `config` mirrors the file_metadata (case_id_column, delimiter,
  // encoding, has_header, sheet).
  validateIdColumn(
    projectId: number | string,
    fileId: number | string,
    config: Record<string, unknown>,
  ) {
    return api.post(`/project/${projectId}/file/${fileId}/validate-id-column`, config) as Promise<
      ApiBody<IdColumnValidation>
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
