/**
 * API service for evaluation resources (under /project/{projectId}/evaluation...).
 * Note the path inconsistency: list/detail use singular `evaluation`, while the
 * bulk download uses plural `evaluations/download`. Preserved as-is.
 */
import { api } from './api'
import type { ApiBody, BlobResponse, EvaluationFilter } from '@/types'
import type {
  DocumentEvaluationDetail,
  Evaluation,
  EvaluationDetail,
  EvaluationErrorSummary,
} from '@/types'

export const evaluationsApi = {
  list(projectId: number | string, params: EvaluationFilter = {}) {
    return api.get(`/project/${projectId}/evaluation`, {
      params,
    }) as Promise<ApiBody<Evaluation[]>>
  },
  get(projectId: number | string, evaluationId: number | string) {
    return api.get(`/project/${projectId}/evaluation/${evaluationId}`) as Promise<
      ApiBody<EvaluationDetail>
    >
  },
  delete(projectId: number | string, evaluationId: number | string) {
    return api.delete(`/project/${projectId}/evaluation/${evaluationId}`) as Promise<
      ApiBody<unknown>
    >
  },
  getDocument(
    projectId: number | string,
    evaluationId: number | string,
    documentId: number | string,
  ) {
    return api.get(
      `/project/${projectId}/evaluation/${evaluationId}/document/${documentId}`,
    ) as Promise<ApiBody<DocumentEvaluationDetail>>
  },
  getErrors(
    projectId: number | string,
    evaluationId: number | string,
    params: EvaluationFilter = {},
  ) {
    return api.get(`/project/${projectId}/evaluation/${evaluationId}/errors`, {
      params,
    }) as Promise<ApiBody<EvaluationErrorSummary>>
  },
  // Bulk export. `params` carries format + flags + repeated `evaluation_ids[]`.
  download(projectId: number | string, params: EvaluationFilter = {}) {
    return api.get(`/project/${projectId}/evaluations/download`, {
      params,
      responseType: 'blob',
    }) as Promise<BlobResponse>
  },
}
