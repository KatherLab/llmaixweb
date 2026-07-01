/**
 * API service for trial resources.
 */
import { api } from './api'
import type { ApiBody, BlobResponse, QueryParams } from '@/types'
import type {
  EvaluationSummary,
  PaginatedTrialResults,
  PaginatedTrials,
  Trial,
  TrialCreate,
  TrialFilter,
  TrialUpdate,
} from '@/types'

export const trialsApi = {
  list(projectId: number | string, params: TrialFilter = {}) {
    return api.get(`/project/${projectId}/trial`, {
      params,
    }) as Promise<ApiBody<PaginatedTrials>>
  },
  get(projectId: number | string, trialId: number | string, params: QueryParams = {}) {
    return api.get(`/project/${projectId}/trial/${trialId}`, {
      params,
    }) as Promise<ApiBody<Trial>>
  },
  listResults(projectId: number | string, trialId: number | string, params: QueryParams = {}) {
    return api.get(`/project/${projectId}/trial/${trialId}/results`, {
      params,
    }) as Promise<ApiBody<PaginatedTrialResults>>
  },
  create(projectId: number | string, data: TrialCreate) {
    return api.post(`/project/${projectId}/trial`, data) as Promise<ApiBody<Trial>>
  },
  update(projectId: number | string, trialId: number | string, data: TrialUpdate) {
    return api.patch(`/project/${projectId}/trial/${trialId}`, data) as Promise<ApiBody<Trial>>
  },
  delete(projectId: number | string, trialId: number | string) {
    return api.delete(`/project/${projectId}/trial/${trialId}`) as Promise<ApiBody<unknown>>
  },
  cancel(projectId: number | string, trialId: number | string, keepProcessed = false) {
    return api.post(
      `/project/${projectId}/trial/${trialId}/cancel`,
      {},
      { params: { keep_processed: keepProcessed } },
    ) as Promise<ApiBody<unknown>>
  },
  download(projectId: number | string, trialId: number | string, params: QueryParams) {
    return api.get(`/project/${projectId}/trial/${trialId}/download`, {
      params,
      responseType: 'blob',
    }) as Promise<BlobResponse>
  },
  evaluate(projectId: number | string, trialId: number | string, groundtruthId: number | string) {
    return api.post(
      `/project/${projectId}/trial/${trialId}/evaluate`,
      {},
      { params: { groundtruth_id: groundtruthId } },
    ) as Promise<ApiBody<EvaluationSummary>>
  },
}
