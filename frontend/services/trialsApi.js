/**
 * API service for trial resources.
 */
import { api } from './api'

export const trialsApi = {
  list(projectId, params = {}) {
    return api.get(`/project/${projectId}/trial`, { params })
  },
  get(projectId, trialId, params = {}) {
    return api.get(`/project/${projectId}/trial/${trialId}`, { params })
  },
  listResults(projectId, trialId, params = {}) {
    return api.get(`/project/${projectId}/trial/${trialId}/results`, { params })
  },
  create(projectId, data) {
    return api.post(`/project/${projectId}/trial`, data)
  },
  update(projectId, trialId, data) {
    return api.patch(`/project/${projectId}/trial/${trialId}`, data)
  },
  delete(projectId, trialId) {
    return api.delete(`/project/${projectId}/trial/${trialId}`)
  },
  cancel(projectId, trialId, keepProcessed = false) {
    return api.post(
      `/project/${projectId}/trial/${trialId}/cancel`,
      {},
      { params: { keep_processed: keepProcessed } },
    )
  },
  download(projectId, trialId, params) {
    return api.get(`/project/${projectId}/trial/${trialId}/download`, {
      params,
      responseType: 'blob',
    })
  },
  evaluate(projectId, trialId, groundtruthId) {
    return api.post(
      `/project/${projectId}/trial/${trialId}/evaluate`,
      {},
      { params: { groundtruth_id: groundtruthId } },
    )
  },
}
