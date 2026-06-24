/**
 * API service for file resources (`/project/{projectId}/file/*`).
 */
import { api } from './api'

const MULTIPART = { 'Content-Type': 'multipart/form-data' }

export const filesApi = {
  list(projectId, params = {}) {
    return api.get(`/project/${projectId}/file`, { params })
  },
  get(projectId, fileId) {
    return api.get(`/project/${projectId}/file/${fileId}`)
  },
  delete(projectId, fileId) {
    return api.delete(`/project/${projectId}/file/${fileId}`)
  },

  // Multipart upload. `formData` must include the File + a `file_info` JSON string.
  // Callers upload one file per request (sequential loop); no progress callback is used.
  upload(projectId, formData) {
    return api.post(`/project/${projectId}/file`, formData, { headers: MULTIPART })
  },
  configure(projectId, fileId, payload) {
    return api.post(`/project/${projectId}/file/${fileId}/configure`, payload)
  },

  // Raw file content as a blob (download or preview).
  getContent(projectId, fileId, params = {}) {
    return api.get(`/project/${projectId}/file/${fileId}/content`, {
      params,
      responseType: 'blob',
    })
  },
  // Tabular preview rows (CSV/XLSX).
  getPreviewRows(projectId, fileId, params = {}) {
    return api.get(`/project/${projectId}/file/${fileId}/preview-rows`, { params })
  },
}
