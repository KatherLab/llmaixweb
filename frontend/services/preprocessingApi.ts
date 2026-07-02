/**
 * API service for preprocessing resources (`/project/{projectId}/preprocess/*`).
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type {
  PreprocessingDuplicatePreview,
  PreprocessingFilter,
  PreprocessingTask,
  PreprocessingTaskCreate,
} from '@/types'

export const preprocessingApi = {
  list(projectId: number | string, params: PreprocessingFilter = {}) {
    return api.get(`/project/${projectId}/preprocess`, {
      params,
    }) as Promise<ApiBody<PreprocessingTask[]>>
  },
  get(projectId: number | string, taskId: number | string) {
    return api.get(`/project/${projectId}/preprocess/${taskId}`) as Promise<
      ApiBody<PreprocessingTask>
    >
  },
  // Start a preprocessing run. Body: { file_ids, inline_config, skip_existing? }.
  create(projectId: number | string, payload: PreprocessingTaskCreate) {
    return api.post(`/project/${projectId}/preprocess`, payload) as Promise<
      ApiBody<PreprocessingTask>
    >
  },
  // Dry-run preview of what a preprocessing run would produce.
  preview(projectId: number | string, payload: PreprocessingTaskCreate) {
    return api.post(`/project/${projectId}/preprocess/preview`, payload) as Promise<
      ApiBody<PreprocessingDuplicatePreview>
    >
  },
  cancel(projectId: number | string, taskId: number | string, keepProcessed = false) {
    return api.post(
      `/project/${projectId}/preprocess/${taskId}/cancel`,
      {},
      { params: { keep_processed: keepProcessed } },
    ) as Promise<ApiBody<unknown>>
  },
  // POST (not GET) — requeues failed subtasks, i.e. mutates state. The
  // backend route is POST deliberately: a GET would be unsafe (browser/crawler
  // prefetch could silently trigger retries).
  retryFailed(projectId: number | string, taskId: number | string) {
    return api.post(`/project/${projectId}/preprocess/${taskId}/retry-failed`) as Promise<
      ApiBody<unknown>
    >
  },
}
