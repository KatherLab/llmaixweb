/**
 * API service for evaluation resources (under /project/{projectId}/evaluation...).
 * Note the path inconsistency: list/detail use singular `evaluation`, while the
 * bulk download uses plural `evaluations/download`. Preserved as-is.
 */
import { api } from './api'

export const evaluationsApi = {
  list(projectId, params = {}) {
    return api.get(`/project/${projectId}/evaluation`, { params })
  },
  get(projectId, evaluationId) {
    return api.get(`/project/${projectId}/evaluation/${evaluationId}`)
  },
  delete(projectId, evaluationId) {
    return api.delete(`/project/${projectId}/evaluation/${evaluationId}`)
  },
  getDocument(projectId, evaluationId, documentId) {
    return api.get(`/project/${projectId}/evaluation/${evaluationId}/document/${documentId}`)
  },
  getErrors(projectId, evaluationId, params = {}) {
    return api.get(`/project/${projectId}/evaluation/${evaluationId}/errors`, { params })
  },
  // Bulk export. `params` carries format + flags + repeated `evaluation_ids[]`.
  download(projectId, params = {}) {
    return api.get(`/project/${projectId}/evaluations/download`, {
      params,
      responseType: 'blob',
    })
  },
}
