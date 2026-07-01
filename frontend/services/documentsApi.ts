/**
 * API service for document resources.
 * Replaces inline `api.get(\`/project/${projectId}/document\`)` calls.
 */
import { api } from './api'
import type { ApiBody, DocumentFilter } from '@/types'
import type { Document, PaginatedDocuments } from '@/types'

export const documentsApi = {
  list(projectId: number | string, params: DocumentFilter = {}) {
    return api.get(`/project/${projectId}/document`, {
      params,
    }) as Promise<ApiBody<PaginatedDocuments>>
  },
  get(projectId: number | string, documentId: number | string) {
    return api.get(`/project/${projectId}/document/${documentId}`) as Promise<ApiBody<Document>>
  },
  delete(projectId: number | string, documentId: number | string) {
    return api.delete(`/project/${projectId}/document/${documentId}`) as Promise<ApiBody<unknown>>
  },
}
