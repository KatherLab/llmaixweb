/**
 * API service for prompt resources (`/project/{projectId}/prompt/*`).
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type { Prompt, PromptCreate, PromptUpdate } from '@/types'

export const promptsApi = {
  list(projectId: number | string) {
    return api.get(`/project/${projectId}/prompt`) as Promise<ApiBody<Prompt[]>>
  },
  get(projectId: number | string, promptId: number | string) {
    return api.get(`/project/${projectId}/prompt/${promptId}`) as Promise<ApiBody<Prompt>>
  },
  create(projectId: number | string, payload: PromptCreate) {
    return api.post(`/project/${projectId}/prompt`, payload) as Promise<ApiBody<Prompt>>
  },
  update(projectId: number | string, promptId: number | string, payload: PromptUpdate) {
    return api.put(`/project/${projectId}/prompt/${promptId}`, payload) as Promise<ApiBody<Prompt>>
  },
  delete(projectId: number | string, promptId: number | string) {
    return api.delete(`/project/${projectId}/prompt/${promptId}`) as Promise<ApiBody<unknown>>
  },
}
