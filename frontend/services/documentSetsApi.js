/**
 * API service for document-set resources (`/project/{projectId}/document-set/*`).
 */
import { api } from './api'

export const documentSetsApi = {
  list(projectId, params = {}) {
    return api.get(`/project/${projectId}/document-set`, { params })
  },
  create(projectId, payload) {
    return api.post(`/project/${projectId}/document-set`, payload)
  },
  update(projectId, setId, payload) {
    return api.patch(`/project/${projectId}/document-set/${setId}`, payload)
  },
  // `deleteDocuments` toggles the `delete_documents` query param (also removes
  // the set's documents, not just the grouping). Returns deleted document ids.
  delete(projectId, setId, deleteDocuments = false) {
    return api.delete(`/project/${projectId}/document-set/${setId}`, {
      params: deleteDocuments ? { delete_documents: true } : {},
    })
  },
  getStats(projectId, setId) {
    return api.get(`/project/${projectId}/document-set/${setId}/stats`)
  },
  downloadAll(projectId, setId) {
    return api.post(
      `/project/${projectId}/document-set/${setId}/download-all`,
      {},
      {
        responseType: 'blob',
      },
    )
  },
}
