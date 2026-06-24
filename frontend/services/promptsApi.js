/**
 * API service for prompt resources (`/project/{projectId}/prompt/*`).
 */
import { api } from './api'

export const promptsApi = {
  list(projectId) {
    return api.get(`/project/${projectId}/prompt`)
  },
  get(projectId, promptId) {
    return api.get(`/project/${projectId}/prompt/${promptId}`)
  },
  create(projectId, payload) {
    return api.post(`/project/${projectId}/prompt`, payload)
  },
  update(projectId, promptId, payload) {
    return api.put(`/project/${projectId}/prompt/${promptId}`, payload)
  },
  delete(projectId, promptId) {
    return api.delete(`/project/${projectId}/prompt/${promptId}`)
  },
}
