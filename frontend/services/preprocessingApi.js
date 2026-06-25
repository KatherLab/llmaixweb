/**
 * API service for preprocessing resources (`/project/{projectId}/preprocess/*`).
 */
import { api } from './api'

export const preprocessingApi = {
  list(projectId, params = {}) {
    return api.get(`/project/${projectId}/preprocess`, { params })
  },
  get(projectId, taskId) {
    return api.get(`/project/${projectId}/preprocess/${taskId}`)
  },
  // Start a preprocessing run. Body: { file_ids, inline_config, skip_existing? }.
  create(projectId, payload) {
    return api.post(`/project/${projectId}/preprocess`, payload)
  },
  // Dry-run preview of what a preprocessing run would produce.
  preview(projectId, payload) {
    return api.post(`/project/${projectId}/preprocess/preview`, payload)
  },
  cancel(projectId, taskId, keepProcessed = false) {
    return api.post(
      `/project/${projectId}/preprocess/${taskId}/cancel`,
      {},
      { params: { keep_processed: keepProcessed } },
    )
  },
  // GET-triggered action (not a pure read) — requeues failed subtasks.
  retryFailed(projectId, taskId) {
    return api.get(`/project/${projectId}/preprocess/${taskId}/retry-failed`)
  },
}
