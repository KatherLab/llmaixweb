/**
 * API service for document resources.
 * Replaces inline `api.get(\`/project/${projectId}/document\`)` calls.
 */
import { api } from './api'

export const documentsApi = {
  list(projectId, params = {}) {
    return api.get(`/project/${projectId}/document`, { params })
  },
  get(projectId, documentId) {
    return api.get(`/project/${projectId}/document/${documentId}`)
  },
  delete(projectId, documentId) {
    return api.delete(`/project/${projectId}/document/${documentId}`)
  },
  reprocess(projectId, data) {
    return api.post(`/project/${projectId}/preprocess`, data)
  },
}
