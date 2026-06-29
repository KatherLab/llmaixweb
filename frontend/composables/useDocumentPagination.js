/**
 * Composable for server-side document-list fetching + pagination used by the
 * CreateTrialModal "Individual" document picker, plus the bulk-ID fetch used by
 * the "Smart" picker (date-range / recent-docs selections).
 *
 * Extracted verbatim from CreateTrialModal.vue to keep behavior identical:
 *  - paged `fetchDocuments({ reset })` for the Individual tab
 *  - `fetchAllDocumentIds(query)` looped-pages fetch for Smart/Select-All
 *  - shared `documentLookup` Map (id -> label cache) so the Smart picker can
 *    resolve labels for IDs it never paginated through
 *  - date-range ISO helpers used by the Smart picker
 *
 * Usage:
 *   const {
 *     docsPage, totalDocs, pageSize, page, isLoadingDocs, docsError,
 *     documentLookup, fetchDocuments, fetchAllDocumentIds, getDocLabel,
 *     toISODateStart, toISODateEndExclusive,
 *   } = useDocumentPagination({ getProjectId, getMode, getSearchTerm })
 */
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
import { documentsApi } from '@/services/documentsApi'
import { extractErrorMessage } from '@/utils/errors'

export function useDocumentPagination(options = {}) {
  const { getProjectId, getMode = () => 'individual', getSearchTerm = () => '' } = options

  const toast = useToast()

  // Current page items
  const docsPage = ref([])
  const totalDocs = ref(0)
  // tweak as needed (API allows up to 500)
  const pageSize = ref(50)
  // 1-based
  const page = ref(1)
  const isLoadingDocs = ref(false)
  const docsError = ref(null)

  // id -> label cache (shared with Smart picker)
  const documentLookup = ref(new Map())

  const toISODateStart = (d) => (d ? new Date(`${d}T00:00:00.000Z`).toISOString() : undefined)
  const toISODateEndExclusive = (d) =>
    d ? new Date(`${d}T23:59:59.999Z`).toISOString() : undefined

  const buildDocQueryParams = (opts = {}) => {
    const params = {
      limit: opts.limit != null ? opts.limit : pageSize.value,
      offset: opts.offset != null ? opts.offset : (page.value - 1) * pageSize.value,
    }
    if (opts.search && opts.search.trim()) params.search = opts.search.trim()
    if (opts.config_id != null) params.config_id = opts.config_id
    if (opts.date_from) params.date_from = opts.date_from
    if (opts.date_to) params.date_to = opts.date_to
    if (opts.document_set_id != null) params.document_set_id = opts.document_set_id
    return params
  }

  const fetchDocuments = async ({ reset = false } = {}) => {
    if (getMode() !== 'individual') return
    if (reset) page.value = 1

    isLoadingDocs.value = true
    docsError.value = null

    try {
      const params = buildDocQueryParams({ search: getSearchTerm() })
      const { data } = await documentsApi.list(getProjectId(), params)
      docsPage.value = data.items || []
      totalDocs.value = data.total || 0

      for (const d of docsPage.value) {
        const label = d.document_name || d?.original_file?.file_name || `Document #${d.id}`
        documentLookup.value.set(d.id, label)
      }
    } catch (e) {
      console.error('Failed to fetch documents page:', e)
      docsError.value = extractErrorMessage(e, 'Failed to load documents')
      docsPage.value = []
      totalDocs.value = 0
    } finally {
      isLoadingDocs.value = false
    }
  }

  // Fetch all matching IDs for Smart selections (looped pages)
  const fetchAllDocumentIds = async (q = {}) => {
    const ids = []
    let offset = 0
    // API max
    const limit = 500

    try {
      let params = buildDocQueryParams({ ...q, limit, offset })
      let resp = await documentsApi.list(getProjectId(), params)
      const total = resp.data.total ?? resp.data.items?.length ?? 0

      const pushIds = (items) => {
        for (const d of items) {
          ids.push(d.id)
          const label = d.document_name || d?.original_file?.file_name || `Document #${d.id}`
          documentLookup.value.set(d.id, label)
        }
      }

      pushIds(resp.data.items ?? [])

      while (ids.length < total) {
        offset += limit
        params = buildDocQueryParams({ ...q, limit, offset })
        resp = await documentsApi.list(getProjectId(), params)
        pushIds(resp.data.items ?? [])
      }
    } catch (e) {
      console.error('fetchAllDocumentIds error:', e)
      toast.error('Failed to load matching documents')
    }

    return ids
  }

  const getDocLabel = (docId) => documentLookup.value.get(docId) || `Document #${docId}`

  return {
    docsPage,
    totalDocs,
    pageSize,
    page,
    isLoadingDocs,
    docsError,
    documentLookup,
    buildDocQueryParams,
    fetchDocuments,
    fetchAllDocumentIds,
    getDocLabel,
    toISODateStart,
    toISODateEndExclusive,
  }
}
