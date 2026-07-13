/**
 * API service for document-set resources (`/project/{projectId}/document-set/*`).
 */
import { api } from './api'
import type { ApiBody, BlobResponse } from '@/types'
import type {
  DocumentSet,
  DocumentSetCreate,
  DocumentSetFilter,
  DocumentSetStats,
  DocumentSetSummary,
  DocumentSetUpdate,
  PaginatedDocumentSets,
} from '@/types'

export const documentSetsApi = {
  list(projectId: number | string, params: DocumentSetFilter = {}) {
    return api.get(`/project/${projectId}/document-set`, {
      params,
    }) as Promise<ApiBody<PaginatedDocumentSets>>
  },
  get(projectId: number | string, setId: number | string) {
    return api.get(`/project/${projectId}/document-set/${setId}`) as Promise<
      ApiBody<DocumentSetSummary>
    >
  },
  create(projectId: number | string, payload: DocumentSetCreate) {
    return api.post(`/project/${projectId}/document-set`, payload) as Promise<ApiBody<DocumentSet>>
  },
  update(projectId: number | string, setId: number | string, payload: DocumentSetUpdate) {
    return api.patch(`/project/${projectId}/document-set/${setId}`, payload) as Promise<
      ApiBody<DocumentSet>
    >
  },
  // `deleteDocuments` toggles the `delete_documents` query param (also removes
  // the set's documents, not just the grouping). Returns deleted document ids.
  delete(projectId: number | string, setId: number | string, deleteDocuments = false) {
    return api.delete(`/project/${projectId}/document-set/${setId}`, {
      params: deleteDocuments ? { delete_documents: true } : {},
    }) as Promise<ApiBody<{ deleted_document_ids?: number[] }>>
  },
  getStats(projectId: number | string, setId: number | string) {
    return api.get(`/project/${projectId}/document-set/${setId}/stats`) as Promise<
      ApiBody<DocumentSetStats>
    >
  },
  downloadAll(projectId: number | string, setId: number | string) {
    return api.post(
      `/project/${projectId}/document-set/${setId}/download-all`,
      {},
      {
        responseType: 'blob',
      },
    ) as Promise<BlobResponse>
  },
}
