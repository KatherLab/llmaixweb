/**
 * API service for schema resources (`/project/{projectId}/schema/*`).
 */
import { api } from './api'

export const schemasApi = {
  list(projectId) {
    return api.get(`/project/${projectId}/schema`)
  },
  get(projectId, schemaId) {
    return api.get(`/project/${projectId}/schema/${schemaId}`)
  },
  create(projectId, payload) {
    return api.post(`/project/${projectId}/schema`, payload)
  },
  update(projectId, schemaId, payload) {
    return api.put(`/project/${projectId}/schema/${schemaId}`, payload)
  },
  delete(projectId, schemaId) {
    return api.delete(`/project/${projectId}/schema/${schemaId}`)
  },
  getFieldTypes(projectId, schemaId) {
    return api.get(`/project/${projectId}/schema/${schemaId}/field_types`)
  },
}
