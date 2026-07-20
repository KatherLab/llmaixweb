<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <PageHeader
      title="Documents"
      subtitle="View and manage processed documents and document groups"
      :sticky="false"
      class="mb-6"
    />

    <BaseTabGroup v-model="activeTab" :tabs="tabs">
      <template #tab="{ tab }">
        {{ tab.label }}
        <StatusBadge color="gray" class="ml-2">{{ tab.badge }}</StatusBadge>
      </template>
    </BaseTabGroup>

    <!-- Tab Content -->
    <div v-if="activeTab === 'documents'">
      <!-- Filters and Search -->
      <DocumentsFilters
        v-model:search="filters.search"
        v-model:ocr-engine="filters.ocrEngine"
        v-model:date-range="filters.dateRange"
        v-model:include-archived="filters.includeArchived"
        v-model:custom-date-from="customDateFrom"
        v-model:custom-date-to="customDateTo"
        :total-count="totalCount"
        @fetch="fetchDocuments"
        @date-range-change="handleDateRangeChange"
        @apply-custom-range="applyCustomDateRange"
        @clear-filters="clearFilters"
        @clear-filter="handleClearFilter"
      />

      <!-- Batch Actions -->
      <div class="flex justify-between items-center mb-4">
        <span class="text-sm text-content-muted">
          {{ totalCount }} document{{ totalCount !== 1 ? 's' : '' }}
        </span>
      </div>

      <!-- Documents Grid/List -->
      <SkeletonTable v-if="isLoading" :columns="4" :rows="8" />

      <!-- Inline error state: a failed fetch must not masquerade as
           "no documents" — show the error with a retry instead. -->
      <ErrorBanner
        v-else-if="fetchError"
        :message="fetchError"
        retry-text="Retry"
        :retry-loading="isLoading"
        @retry="fetchDocuments"
      />

      <!-- Empty State: no documents at all, or the filters returned nothing.
           (The skeleton/error branches above win until the first load resolves,
           so a single loaded-and-empty state covers both cases — with an
           actionable CTA each way.) -->
      <EmptyState
        v-else-if="hasLoadedDocuments && serverItems.length === 0"
        :title="hasActiveFilters ? 'No documents match your filters' : 'No documents yet'"
        :description="
          hasActiveFilters
            ? 'Try adjusting or clearing your filters to see more results'
            : 'Process some files in the Files & Preprocessing tab to see documents here'
        "
        :action-text="hasActiveFilters ? 'Clear All Filters' : 'Go to Files & Preprocessing'"
        @action="handleEmptyStateAction"
      >
        <template #icon>
          <Search
            v-if="hasActiveFilters"
            class="h-12 w-12 mx-auto text-content-subtle"
            aria-hidden="true"
          />
          <FileText v-else class="h-12 w-12 mx-auto text-content-subtle" aria-hidden="true" />
        </template>
      </EmptyState>

      <!-- Documents Table -->
      <DocumentsTable
        v-else
        :documents="serverItems"
        :selected-documents="selectedDocuments"
        :are-all-selected="areAllDocumentsSelected"
        :select-all-busy="isSelectingAllDocs"
        sort-by="created_at"
        :sort-order="sortOrder"
        :pagination="tablePagination"
        @toggle-select-all="toggleSelectAll"
        @toggle-selection="toggleDocumentSelection"
        @select-all-documents="selectAllDocuments"
        @clear-selection="clearSelection"
        @sort="handleSort"
        @view="viewDocument"
        @download="downloadDocument"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
      />

      <!-- Batch Actions Modal -->
      <BatchActionsModal
        :open="showBatchActions"
        :action="batchAction"
        :documents="selectedDocuments"
        :project-id="projectId"
        @close="showBatchActions = false"
        @complete="handleBatchComplete"
        @deleted="handleDocumentsDeleted"
      />

      <!-- Floating Batch Toolbar -->
      <BatchActionBar
        :count="selectedDocuments.length"
        count-label="document"
        @clear="selectedDocuments = []"
      >
        <BaseButton variant="secondary" size="sm" @click="createGroupFromSelection">
          <FolderPlus class="w-4 h-4" />
          Create Group
        </BaseButton>
        <BaseButton variant="secondary" size="sm" @click="performBatchAction('reprocess')">
          <RefreshCw class="w-4 h-4" />
          Reprocess
        </BaseButton>
        <Tooltip text="Export is coming soon">
          <BaseButton variant="secondary" size="sm" disabled>
            <Download class="w-4 h-4" />
            Export
          </BaseButton>
        </Tooltip>
        <BaseButton variant="danger" size="sm" @click="performBatchAction('delete')">
          <Trash2 class="w-4 h-4" />
          Delete
        </BaseButton>
      </BatchActionBar>

      <!-- Create Document Group Modal (from documents tab) -->
      <CreateDocumentGroupModal
        v-if="showCreateGroupModal"
        :open="showCreateGroupModal"
        :documents="documents"
        :project-id="projectId"
        :selected-document-ids="createGroupWithDocs"
        @close="handleCreateGroupModalClose"
        @save="handleCreateGroupModalSave"
      />
    </div>

    <div v-else-if="activeTab === 'groups'">
      <DocumentGroups :project-id="projectId" @refresh="handleGroupsRefresh" />
    </div>

    <!-- Document Viewer Modal (moved outside tabs to be always available) -->
    <DocumentViewer
      :open="showDocumentViewer"
      :document="viewingDocument!"
      :project-id="projectId"
      :index="viewerGlobalIndex"
      :total="totalCount"
      :has-prev="viewerHasPrev"
      :has-next="viewerHasNext"
      @close="closeDocumentViewer"
      @reprocess="reprocessDocument"
      @restored="handleVersionRestored"
      @prev="viewerPrev"
      @next="viewerNext"
    />

    <!-- Document Group Viewer (opened via ?group= deep-link from preprocessing history) -->
    <ViewDocumentGroupModal
      v-if="viewingGroup"
      :open="showViewGroup"
      :group="viewingGroup"
      :project-id="projectId"
      @close="closeGroupViewer"
      @edit="closeGroupViewer"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { isAxiosError } from 'axios'
import { useRoute, useRouter } from 'vue-router'
import { Download, FileText, FolderPlus, RefreshCw, Search, Trash2 } from '@lucide/vue'
import { documentsApi } from '@/services/documentsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { filesApi } from '@/services/filesApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { authApi } from '@/services/authApi'
import { useToast } from '@/composables/useToast'
import { debounce } from 'perfect-debounce'
import { setEngineLabels } from '@/utils/ocrLabels'
import { getDateRangeBounds } from '@/utils/dateRange'
import SkeletonTable from '@/components/common/SkeletonTable.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BatchActionBar from '@/components/common/BatchActionBar.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useFileDownload } from '@/composables/useFileDownload'
import { usePagination } from '@/composables/usePagination'
import DocumentViewer from './DocumentViewer.vue'
import BatchActionsModal from './BatchActionsModal.vue'
import DocumentGroups from './DocumentsGroups.vue'
import CreateDocumentGroupModal from './CreateDocumentGroupModal.vue'
import ViewDocumentGroupModal from './ViewDocumentGroupModal.vue'
import DocumentsFilters from './DocumentsFilters.vue'
import DocumentsTable from './DocumentsTable.vue'
import { extractErrorMessage } from '@/utils/errors'
import type {
  DocumentListItem,
  DocumentSetCreate,
  DocumentSetSummary,
  PreprocessingTaskCreate,
} from '@/types'

interface Props {
  projectId: string | number
}

const props = defineProps<Props>()

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { downloadFromApi } = useFileDownload()

// State
const documents = ref<DocumentListItem[]>([]) // All documents for groups modal
const allDocumentsLoaded = ref<boolean>(false) // Track if we've fetched all documents
const isLoading = ref<boolean>(true)
const selectedDocuments = ref<number[]>([])
const viewingDocument = ref<DocumentListItem | null>(null)
const showDocumentViewer = ref<boolean>(false)
const showBatchActions = ref<boolean>(false)
const batchAction = ref<string>('')
const itemsPerPage = ref<number>(50)
const totalCount = ref<number>(0) // total rows on the server (after filters) — must be declared before usePagination (its getTotal reads it eagerly during setup)
const pagination = usePagination({
  getTotal: () => totalCount.value,
  // Pass the ref (not a snapshot) so totalPages/offset track page-size changes.
  pageSize: itemsPerPage,
})
const currentPage = pagination.currentPage
const activeTab = ref<string>('documents')
const showCreateGroupModal = ref<boolean>(false)
const createGroupWithDocs = ref<number[]>([]) // Documents to pre-select when creating group
const serverItems = ref<DocumentListItem[]>([]) // current page rows from the server
const documentGroupsCount = ref<number>(0) // count of document groups

// Tab config for BaseTabGroup (badges rendered via #tab scoped slot to keep StatusBadge styling)
const tabs = computed(() => [
  { label: 'All Documents', value: 'documents', badge: totalCount.value },
  { label: 'Document Groups', value: 'groups', badge: documentGroupsCount.value },
])

// Filters
interface FilterState {
  search: string
  dateRange: string
  ocrEngine: string
  includeArchived: boolean
}

const filters = ref<FilterState>({
  search: '',
  dateRange: '',
  ocrEngine: '',
  includeArchived: false,
})

// Custom date range state
const customDateFrom = ref<string>('')
const customDateTo = ref<string>('')

// Track if we've ever loaded documents (for filter UX)
const hasLoadedDocuments = ref<boolean>(false)

// Inline error for a failed list fetch (rendered via ErrorBanner + Retry).
const fetchError = ref<string>('')

// Check if any filters are active
const hasActiveFilters = computed<boolean>(() => {
  return (
    !!filters.value.search ||
    !!filters.value.dateRange ||
    !!filters.value.ocrEngine ||
    (filters.value.dateRange === 'custom' && !!customDateFrom.value) ||
    filters.value.includeArchived
  )
})

// Compute date bounds for date range filter
const computeDateBounds = (range: string) => {
  return getDateRangeBounds(range, customDateFrom.value, customDateTo.value)
}

// Handle date range change
const handleDateRangeChange = (): void => {
  if (filters.value.dateRange === 'custom') {
    // Don't fetch yet - wait for user to select dates
    return
  }
  currentPage.value = 1
  fetchDocuments()
}

// Apply custom date range
const applyCustomDateRange = (): void => {
  currentPage.value = 1
  fetchDocuments()
}

// Stats - using server-side totalCount

// Server-side pagination - totalPages from usePagination composable
const totalPages = pagination.totalPages

// Pagination object for the DataTable (shape: { page, page_size, total, total_pages })
const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: itemsPerPage.value,
  total: totalCount.value,
  total_pages: totalPages.value,
}))

const handlePageChange = (page: number): void => {
  currentPage.value = page
}

const handlePageSizeChange = (size: number): void => {
  itemsPerPage.value = size
  currentPage.value = 1
}

// Server-side sort (created_at only — the list endpoint orders solely by
// creation time via sort=created_asc|created_desc).
const sortOrder = ref<'asc' | 'desc'>('desc')
const handleSort = (field: string): void => {
  if (field !== 'created_at') return
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  currentPage.value = 1
  fetchDocuments()
}

// Empty-state CTA: clear filters when they hid everything; otherwise guide the
// user to the Files & Preprocessing step to produce documents.
const handleEmptyStateAction = (): void => {
  if (hasActiveFilters.value) {
    clearFilters()
  } else {
    router.push({ path: `/projects/${props.projectId}`, query: { tab: 'files' } })
  }
}

// Handle highlight query parameter (from preprocessing history "Go to Document"
// navigation). Mirrors the ?group= handling below: the param is stripped on
// CLOSE (see closeDocumentViewer), not on open, and the initial read happens in
// onMounted rather than an immediate watch. Stripping on open was racy against a
// remount of this async tab component — the transient instance opened + cleared
// the param, then the final visible instance mounted with no param and never
// showed the preview (leaving you on the bare documents table).
const handleHighlight = async (): Promise<void> => {
  const highlightId = route.query.highlight
  if (!highlightId) return

  try {
    // Fetch the specific document by ID
    const { data } = await documentsApi.get(props.projectId, highlightId as string | number)
    if (data) {
      // Open the document viewer
      activeTab.value = 'documents'
      viewingDocument.value = data
      showDocumentViewer.value = true
    }
  } catch (error) {
    console.error('Failed to load highlighted document:', error)
    toast.error('Failed to load document')
    // Strip the param so a remount/refresh doesn't retry the failed lookup.
    clearHighlightParam()
  }
}

// Remove the ?highlight= param once the viewer is closed (or the lookup failed).
const clearHighlightParam = (): void => {
  if (route.query.highlight) {
    router.replace({ query: { ...route.query, highlight: undefined } })
  }
}

// Close the document viewer and strip the deep-link param (see the strip-on-close
// rationale on closeGroupViewer).
const closeDocumentViewer = (): void => {
  showDocumentViewer.value = false
  pendingViewerSelect.value = null
  clearHighlightParam()
}

// Read the ?highlight= param and open its viewer. Called from onMounted (reliable
// once mounted) and from a watcher for the already-mounted case.
const consumeHighlightParam = (): void => {
  if (route.query.highlight) handleHighlight()
}

// Already-mounted case: the highlight param changes while DocumentsManagement is
// the active tab (mount-time reads happen in onMounted).
watch(
  () => route.query.highlight,
  (newHighlight) => {
    if (newHighlight) {
      consumeHighlightParam()
    }
  },
)

// Already-mounted case: the group param changes while DocumentsManagement is the
// active tab (mount-time reads happen in onMounted).
watch(
  () => route.query.group,
  (newGroup) => {
    if (newGroup) {
      consumeGroupParam()
    }
  },
)

// Open the auto-generated group's viewer directly (from preprocessing history
// "Go to Group" navigation for row-by-row CSV/XLSX runs) instead of the first
// document. Driven by a DOM event dispatched by ProjectDetail once this (async)
// component has mounted — the route param alone is racy against the async mount.
const viewingGroup = ref<DocumentSetSummary | null>(null)
const showViewGroup = ref<boolean>(false)

// Remove the ?group= param from the URL (once the group viewer is closed or the
// lookup failed). Kept separate so we DON'T strip it during the mount window —
// see consumeGroupParam.
const clearGroupParam = (): void => {
  if (route.query.group) {
    router.replace({ query: { ...route.query, group: undefined } })
  }
}

const openGroupById = async (groupId: string | number): Promise<void> => {
  try {
    const { data } = await documentSetsApi.get(props.projectId, groupId)
    if (data) {
      activeTab.value = 'groups'
      viewingGroup.value = data
      showViewGroup.value = true
    }
  } catch (error) {
    // The group may have been deleted since the link was created (e.g. the user
    // removed the group but kept its documents). Fall back to the documents list
    // rather than dead-ending. (If the group was deleted *with* its documents,
    // the preprocessing task itself is cleaned up server-side, so this link is
    // already gone.)
    if (isAxiosError(error) && error.response?.status === 404) {
      activeTab.value = 'documents'
      toast.info('That document group no longer exists — showing all documents instead.')
    } else {
      console.error('Failed to load document group:', error)
      toast.error('Failed to load document group')
    }
    // Nothing to close on failure — strip the param so a refresh doesn't retry.
    clearGroupParam()
  }
}

// Close the group viewer and strip the deep-link param. Clearing happens HERE
// (on close) rather than on open: the Documents tab is an async component behind
// an out-in transition, so it can mount more than once during navigation — if we
// stripped the param on the first mount, the final (visible) instance would read
// an empty param and never open the modal. Leaving it until close means every
// instance that mounts still sees it and opens.
const closeGroupViewer = (): void => {
  showViewGroup.value = false
  clearGroupParam()
}

// Read the ?group= param and open its viewer. Called from onMounted (reliable
// once mounted) and from a watcher for the already-mounted case.
const consumeGroupParam = (): void => {
  const groupId = route.query.group
  if (groupId) openGroupById(groupId as string)
}

// Methods
const fetchDocuments = async (): Promise<void> => {
  isLoading.value = true
  try {
    const { date_from, date_to } = computeDateBounds(filters.value.dateRange)
    const params = {
      limit: itemsPerPage.value,
      offset: (currentPage.value - 1) * itemsPerPage.value,
      search: filters.value.search || undefined,
      date_from: date_from || undefined,
      date_to: date_to || undefined,
      include_archived: filters.value.includeArchived || undefined,
      ocr_engine: filters.value.ocrEngine || undefined,
      sort: (sortOrder.value === 'asc' ? 'created_asc' : 'created_desc') as
        'created_asc' | 'created_desc',
      compute_stats: true, // Get server-side stats
    }

    const { data } = await documentsApi.list(props.projectId, params)
    serverItems.value = data.items
    totalCount.value = data.total

    // Mark that we've loaded documents at least once (for filter UX)
    hasLoadedDocuments.value = true

    // If this fetch was triggered by viewer prev/next crossing a page boundary,
    // land on the first/last document of the freshly loaded page.
    if (pendingViewerSelect.value && showDocumentViewer.value && serverItems.value.length) {
      viewingDocument.value =
        pendingViewerSelect.value === 'first'
          ? serverItems.value[0]!
          : serverItems.value[serverItems.value.length - 1]!
    }
    pendingViewerSelect.value = null

    // Safety: if you navigated beyond last page due to a filter change, pull back
    if (
      serverItems.value.length === 0 &&
      totalCount.value > 0 &&
      currentPage.value > totalPages.value
    ) {
      currentPage.value = totalPages.value
      await fetchDocuments()
    }

    fetchError.value = ''
  } catch (error) {
    fetchError.value = extractErrorMessage(error, 'Failed to load documents')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

const toggleDocumentSelection = (docId: number): void => {
  const index = selectedDocuments.value.indexOf(docId)
  if (index > -1) {
    selectedDocuments.value.splice(index, 1)
  } else {
    selectedDocuments.value.push(docId)
  }
}

const toggleSelectAll = (): void => {
  if (areAllDocumentsSelected.value) {
    // Deselect all - remove current page items from selection
    const currentPageIds = serverItems.value.map((doc) => doc.id)
    selectedDocuments.value = selectedDocuments.value.filter((id) => !currentPageIds.includes(id))
  } else {
    // Select all items on current page
    const currentPageIds = serverItems.value.map((doc) => doc.id)
    const newIds = currentPageIds.filter((id) => !selectedDocuments.value.includes(id))
    selectedDocuments.value = [...selectedDocuments.value, ...newIds]
  }
}

const areAllDocumentsSelected = computed<boolean>(() => {
  return (
    serverItems.value.length > 0 &&
    serverItems.value.every((doc) => selectedDocuments.value.includes(doc.id))
  )
})

// Cross-page "select all": the batch endpoints take explicit id lists, so we
// page through the list endpoint (max page size) with the current filters and
// collect every matching document id. Mirrors the Files tab's selectAllFiles.
const isSelectingAllDocs = ref<boolean>(false)
const selectAllDocuments = async (): Promise<void> => {
  if (isSelectingAllDocs.value) return
  isSelectingAllDocs.value = true
  try {
    // Snapshot the filters ONCE before paging so a filter change mid-loop
    // can't mix pages from different filter sets.
    const { date_from, date_to } = computeDateBounds(filters.value.dateRange)
    const baseParams = {
      search: filters.value.search || undefined,
      date_from: date_from || undefined,
      date_to: date_to || undefined,
      include_archived: filters.value.includeArchived || undefined,
      ocr_engine: filters.value.ocrEngine || undefined,
      compute_stats: false,
    }
    const PAGE_SIZE = 500 // endpoint max
    let offset = 0
    const allIds: number[] = []
    while (true) {
      const { data } = await documentsApi.list(props.projectId, {
        ...baseParams,
        limit: PAGE_SIZE,
        offset,
      })
      allIds.push(...(data.items || []).map((d) => d.id))
      if (!data.items || data.items.length < PAGE_SIZE) break
      offset += PAGE_SIZE
    }
    selectedDocuments.value = allIds
    toast.success(`Selected all ${allIds.length} documents`)
  } catch (error) {
    console.error('Failed to select all documents:', error)
    toast.error('Failed to select all documents')
  } finally {
    isSelectingAllDocs.value = false
  }
}

const clearSelection = (): void => {
  selectedDocuments.value = []
}

const viewDocument = (doc: DocumentListItem): void => {
  viewingDocument.value = doc
  showDocumentViewer.value = true
}

// --- Document viewer prev/next ---
// Nav is page-aware: moving past a page boundary loads the adjacent page and
// selects its first/last document, so the counter can show the true corpus-wide
// position (e.g. "51 / 320") instead of a page-local one that looks like the end.
const viewerIndex = computed(() =>
  viewingDocument.value
    ? serverItems.value.findIndex((d) => d.id === viewingDocument.value!.id)
    : -1,
)
// Global 0-based position across all pages (after filters).
const viewerGlobalIndex = computed(() =>
  viewerIndex.value < 0 ? -1 : (currentPage.value - 1) * itemsPerPage.value + viewerIndex.value,
)
const viewerHasPrev = computed(() => viewerGlobalIndex.value > 0)
const viewerHasNext = computed(
  () => viewerGlobalIndex.value >= 0 && viewerGlobalIndex.value < totalCount.value - 1,
)
// After a page load triggered by viewer nav, select this end of the new page.
const pendingViewerSelect = ref<'first' | 'last' | null>(null)
const viewerPrev = (): void => {
  const i = viewerIndex.value
  if (i > 0) {
    viewingDocument.value = serverItems.value[i - 1]!
  } else if (currentPage.value > 1) {
    pendingViewerSelect.value = 'last'
    currentPage.value -= 1 // triggers fetchDocuments via watcher
  }
}
const viewerNext = (): void => {
  const i = viewerIndex.value
  if (i >= 0 && i < serverItems.value.length - 1) {
    viewingDocument.value = serverItems.value[i + 1]!
  } else if (currentPage.value < totalPages.value) {
    pendingViewerSelect.value = 'first'
    currentPage.value += 1 // triggers fetchDocuments via watcher
  }
}

const downloadDocument = async (doc: DocumentListItem): Promise<void> => {
  try {
    const fileId = doc.preprocessed_file?.id || doc.original_file?.id
    if (!fileId) {
      toast.error('No file available for download')
      return
    }

    await downloadFromApi(
      () => filesApi.getContent(props.projectId, fileId),
      doc.original_file?.file_name || `document_${doc.id}.pdf`,
    )
  } catch (error) {
    toast.error('Failed to download document')
    console.error(error)
  }
}

const performBatchAction = (action: string): void => {
  if (selectedDocuments.value.length === 0) {
    toast.warning('Please select documents first')
    return
  }

  batchAction.value = action
  showBatchActions.value = true
}

const createGroupFromSelection = (): void => {
  if (selectedDocuments.value.length === 0) {
    toast.warning('Please select documents first')
    return
  }
  createGroupWithDocs.value = [...selectedDocuments.value]
  showCreateGroupModal.value = true
}

const handleCreateGroupModalClose = (): void => {
  showCreateGroupModal.value = false
  createGroupWithDocs.value = []
}

const handleCreateGroupModalSave = async (groupData: DocumentSetCreate): Promise<void> => {
  try {
    await documentSetsApi.create(props.projectId, groupData)
    toast.success('Document group created')
    showCreateGroupModal.value = false
    createGroupWithDocs.value = []
    selectedDocuments.value = []
  } catch (error) {
    toast.error('Failed to create document group')
    console.error(error)
  }
}

// Fetch all documents for the CreateDocumentGroupModal
const fetchAllDocuments = async (): Promise<void> => {
  if (allDocumentsLoaded.value) {
    return
  }
  try {
    const PAGE_SIZE = 500
    let offset = 0
    let allDocs: DocumentListItem[] = []
    let hasMore = true

    while (hasMore) {
      const { data } = await documentsApi.list(props.projectId, { limit: PAGE_SIZE, offset })
      allDocs = allDocs.concat(data.items || [])
      hasMore = !!data.items && data.items.length === PAGE_SIZE
      offset += PAGE_SIZE
    }

    documents.value = allDocs
    allDocumentsLoaded.value = true
  } catch (error) {
    console.error('Failed to fetch all documents:', error)
    documents.value = []
  }
}

const handleDocumentsDeleted = (deletedIds: number[]): void => {
  // Remove successfully deleted documents from selection
  selectedDocuments.value = selectedDocuments.value.filter((id) => !deletedIds.includes(id))
}

const handleBatchComplete = (): void => {
  // Clear selection and close modal - fetchDocuments will be called separately
  selectedDocuments.value = []
  showBatchActions.value = false
  // Refresh the document list
  fetchDocuments()
}

const handleGroupsRefresh = async (): Promise<void> => {
  // Refresh both groups and documents (since documents may have been deleted too)
  await fetchDocumentGroupsCount()
  await fetchDocuments()
}

// A version was restored (copied to a new latest, no reprocessing). Refresh the
// list and, if the new latest is on the current page, focus it in the viewer.
const handleVersionRestored = async (documentId: number): Promise<void> => {
  await fetchDocuments()
  const restored = serverItems.value.find((d) => d.id === documentId)
  if (restored) viewingDocument.value = restored
}

const reprocessDocument = async (doc: Partial<DocumentListItem>): Promise<void> => {
  try {
    const fileId = doc.original_file?.id
    if (!fileId) {
      console.error('Original file id not found for this document!')
      toast.error('Original file id not found for this document!')
      return
    }
    // Reuse the document's original OCR engine/settings so the reprocess doesn't
    // silently fall back to defaults (which can change extraction results).
    const payload: PreprocessingTaskCreate = {
      file_ids: [fileId],
      inline_config: {
        name: `Reprocess ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`,
        additional_settings: doc.preprocessing_config?.additional_settings ?? {},
      },
      force_reprocess: true,
    }
    await preprocessingApi.create(props.projectId, payload)
    toast.success('Document reprocessing started')
    fetchDocuments()
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to start reprocessing'))
    console.error(error)
  }
}

const clearFilters = (): void => {
  filters.value = {
    search: '',
    dateRange: '',
    ocrEngine: '',
    includeArchived: false,
  }
  customDateFrom.value = ''
  customDateTo.value = ''
  currentPage.value = 1
  fetchDocuments()
}

const clearSearchFilter = (): void => {
  filters.value.search = ''
  currentPage.value = 1
  fetchDocuments()
}

const clearOcrEngineFilter = (): void => {
  filters.value.ocrEngine = ''
  fetchDocuments()
}

const clearDateRangeFilter = (): void => {
  filters.value.dateRange = ''
  fetchDocuments()
}

const clearArchivedFilter = (): void => {
  filters.value.includeArchived = false
  fetchDocuments()
}

const clearCustomDateRange = (): void => {
  customDateFrom.value = ''
  customDateTo.value = ''
  filters.value.dateRange = ''
  fetchDocuments()
}

// Dispatch individual filter-chip clears to the original handlers (preserves per-filter behavior)
const handleClearFilter = (field: string): void => {
  if (field === 'search') clearSearchFilter()
  else if (field === 'ocrEngine') clearOcrEngineFilter()
  else if (field === 'dateRange') clearDateRangeFilter()
  else if (field === 'includeArchived') clearArchivedFilter()
  else if (field === 'customDate') clearCustomDateRange()
}

// Debounced search
const debouncedSearch = debounce(() => {
  currentPage.value = 1
  fetchDocuments()
}, 300)

// Watchers
watch(() => filters.value.search, debouncedSearch)

watch(
  () => filters.value.dateRange,
  () => {
    currentPage.value = 1
    fetchDocuments()
  },
)

watch([currentPage, itemsPerPage], fetchDocuments)

// Watch for create group modal - fetch all documents when opened
watch(
  () => showCreateGroupModal.value,
  (isOpen) => {
    if (isOpen && !allDocumentsLoaded.value) {
      fetchAllDocuments()
    }
  },
)

// Fetch document groups count
const fetchDocumentGroupsCount = async (): Promise<void> => {
  try {
    const { data } = await documentSetsApi.list(props.projectId, {
      include_auto_generated: true,
    })
    documentGroupsCount.value = data.total
  } catch (error) {
    console.error('Failed to fetch document groups count:', error)
  }
}

// Lifecycle
onMounted(() => {
  fetchDocuments()
  fetchDocumentGroupsCount()
  // Deep-link "Go to Document": open the document viewer if arriving with ?highlight=.
  consumeHighlightParam()
  // Deep-link "Go to Group": open the group viewer if arriving with ?group=.
  consumeGroupParam()
  // Load OCR display names from server
  authApi
    .getSettings()
    .then((r) => setEngineLabels(r.data))
    .catch(() => {})
})
</script>
