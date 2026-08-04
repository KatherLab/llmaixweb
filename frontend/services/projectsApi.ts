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
  ProjectShare,
  ProjectShareCreate,
  ProjectShareUpdate,
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

  // Sharing. Reading the collaborator list needs only read access; every
  // mutation is owner-only, except removing your own share ("leave project").
  listShares(projectId: number | string) {
    return api.get(`/project/${projectId}/share`) as Promise<ApiBody<ProjectShare[]>>
  },
  addShare(projectId: number | string, payload: ProjectShareCreate) {
    return api.post(`/project/${projectId}/share`, payload) as Promise<ApiBody<ProjectShare>>
  },
  updateShare(projectId: number | string, shareId: number, payload: ProjectShareUpdate) {
    return api.patch(`/project/${projectId}/share/${shareId}`, payload) as Promise<
      ApiBody<ProjectShare>
    >
  },
  removeShare(projectId: number | string, shareId: number) {
    return api.delete(`/project/${projectId}/share/${shareId}`) as Promise<ApiBody<unknown>>
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
