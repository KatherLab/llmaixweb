/**
 * API service for project resources (top-level `/project` + `/project/activity/*`).
 * Project-scoped sub-resources (files, documents, trials, etc.) have their own modules.
 */
import { api } from './api'

export const projectsApi = {
  list(params = {}) {
    return api.get('/project', { params })
  },
  create(payload) {
    return api.post('/project', payload)
  },
  get(projectId) {
    return api.get(`/project/${projectId}`)
  },
  update(projectId, payload) {
    return api.put(`/project/${projectId}`, payload)
  },
  delete(projectId) {
    return api.delete(`/project/${projectId}`)
  },

  // Recent activity feed (admin ActivityBell)
  activityPreprocess(params = {}) {
    return api.get('/project/activity/preprocess', { params })
  },
  activityTrials(params = {}) {
    return api.get('/project/activity/trials', { params })
  },
}
