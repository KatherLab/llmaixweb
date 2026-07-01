/**
 * API service for project resources (top-level `/project` + `/project/activity/*`).
 * Project-scoped sub-resources (files, documents, trials, etc.) have their own modules.
 */
import { api } from './api'
import type { ApiBody, QueryParams } from '@/types'
import type {
  PreprocessingTask,
  Project,
  ProjectCreate,
  ProjectUpdate,
  TrialSummary,
} from '@/types'

export const projectsApi = {
  list(params: QueryParams = {}) {
    return api.get('/project', { params }) as Promise<ApiBody<Project[]>>
  },
  create(payload: ProjectCreate) {
    return api.post('/project', payload) as Promise<ApiBody<Project>>
  },
  get(projectId: number | string) {
    return api.get(`/project/${projectId}`) as Promise<ApiBody<Project>>
  },
  update(projectId: number | string, payload: ProjectUpdate) {
    return api.put(`/project/${projectId}`, payload) as Promise<ApiBody<Project>>
  },
  delete(projectId: number | string) {
    return api.delete(`/project/${projectId}`) as Promise<ApiBody<unknown>>
  },

  // Recent activity feed (admin ActivityBell)
  activityPreprocess(params: QueryParams = {}) {
    return api.get('/project/activity/preprocess', {
      params,
    }) as Promise<ApiBody<PreprocessingTask[]>>
  },
  activityTrials(params: QueryParams = {}) {
    return api.get('/project/activity/trials', {
      params,
    }) as Promise<ApiBody<TrialSummary[]>>
  },
}
