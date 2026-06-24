/**
 * API service for ground-truth resources (`/project/{projectId}/groundtruth/*`).
 * Includes the nested schema-mapping sub-resource used during evaluation setup.
 */
import { api } from './api'

const MULTIPART = { 'Content-Type': 'multipart/form-data' }

export const groundtruthApi = {
  list(projectId) {
    return api.get(`/project/${projectId}/groundtruth`)
  },
  get(projectId, gtId) {
    return api.get(`/project/${projectId}/groundtruth/${gtId}`)
  },
  // Multipart upload. `formData` includes `file`, `name`, `format`.
  upload(projectId, formData) {
    return api.post(`/project/${projectId}/groundtruth`, formData, { headers: MULTIPART })
  },
  // Rename via multipart FormData (only the `name` field is sent).
  update(projectId, gtId, formData) {
    return api.put(`/project/${projectId}/groundtruth/${gtId}`, formData, { headers: MULTIPART })
  },
  delete(projectId, gtId) {
    return api.delete(`/project/${projectId}/groundtruth/${gtId}`)
  },

  preview(projectId, gtId) {
    return api.get(`/project/${projectId}/groundtruth/${gtId}/preview`)
  },
  setIdColumn(projectId, gtId, payload) {
    return api.put(`/project/${projectId}/groundtruth/${gtId}/id-column`, payload)
  },

  // Schema field mappings
  getMappings(projectId, gtId, schemaId) {
    return api.get(`/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping`)
  },
  setMappings(projectId, gtId, schemaId, mappings) {
    return api.post(
      `/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping`,
      mappings,
    )
  },
  getMappingStatus(projectId, gtId, schemaId) {
    return api.get(`/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping/status`)
  },
}
