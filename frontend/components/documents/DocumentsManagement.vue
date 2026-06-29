<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-start">
      <div>
        <h2 class="text-2xl font-bold text-slate-900 dark:text-white">Documents</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          View and manage processed documents and document groups
        </p>
      </div>
    </div>

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
        <div class="flex items-center space-x-3">
          <span class="text-sm text-slate-500 dark:text-slate-400">
            {{ totalCount }} document{{ totalCount !== 1 ? 's' : '' }}
          </span>

          <div v-if="selectedDocuments.length > 0" class="flex items-center space-x-2">
            <span class="text-sm text-slate-700 dark:text-slate-300">
              {{ selectedDocuments.length }} selected
            </span>
            <BaseButton
              variant="link"
              tone="green"
              class="text-sm font-medium"
              @click="createGroupFromSelection"
            >
              Create Group
            </BaseButton>
            <span class="text-slate-300 dark:text-slate-600">|</span>
            <BaseButton
              variant="link"
              tone="blue"
              class="text-sm font-medium"
              @click="performBatchAction('reprocess')"
            >
              Reprocess
            </BaseButton>
            <BaseButton
              variant="link"
              tone="blue"
              class="text-sm font-medium"
              @click="performBatchAction('export')"
            >
              Export
            </BaseButton>
            <BaseButton
              variant="link"
              tone="red"
              class="text-sm font-medium"
              @click="performBatchAction('delete')"
            >
              Delete
            </BaseButton>
            <button
              class="text-sm text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-300"
              @click="selectedDocuments = []"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      <!-- Documents Grid/List -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <LoadingSpinner size="large" />
      </div>

      <!-- Empty State: No documents (either no documents exist or filters returned no results) -->
      <EmptyState
        v-else-if="hasLoadedDocuments && serverItems.length === 0"
        :title="hasActiveFilters ? 'No documents match your filters' : 'No documents found'"
        :description="
          hasActiveFilters
            ? 'Try adjusting or clearing your filters to see more results'
            : filters.search
              ? 'Try adjusting your search or filters'
              : 'Process some files to see documents here'
        "
        :action-text="hasActiveFilters ? 'Clear All Filters' : ''"
        @action="clearFilters"
      >
        <template #icon>
          <Search class="h-12 w-12 mx-auto text-slate-400 dark:text-slate-500" aria-hidden="true" />
        </template>
      </EmptyState>

      <!-- True Empty State: No documents processed yet -->
      <EmptyState
        v-else-if="!hasLoadedDocuments && serverItems.length === 0"
        title="No documents yet"
        description="Process some files in the Files & Preprocessing tab to see documents here"
      >
        <template #icon>
          <FileText
            class="h-12 w-12 mx-auto text-slate-400 dark:text-slate-500"
            aria-hidden="true"
          />
        </template>
      </EmptyState>

      <!-- Documents Table -->
      <DocumentsTable
        v-else
        :documents="serverItems"
        :selected-documents="selectedDocuments"
        :are-all-selected="areAllDocumentsSelected"
        :pagination="tablePagination"
        @toggle-select-all="toggleSelectAll"
        @toggle-selection="toggleDocumentSelection"
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

      <!-- Create Document Group Modal (from documents tab) -->
      <CreateDocumentGroupModal
        v-if="showCreateGroupModal"
        :documents="documents"
        :project-id="projectId"
        :selected-document-ids="createGroupWithDocs"
        @close="handleCreateGroupModalClose"
        @save="handleCreateGroupModalSave"
      />
    </div>

    <div v-else-if="activeTab === 'groups'">
      <DocumentGroups
        :project-id="projectId"
        @refresh="handleGroupsRefresh"
        @view-document="viewDocument"
      />
    </div>

    <!-- Document Viewer Modal (moved outside tabs to be always available) -->
    <DocumentViewer
      :open="showDocumentViewer"
      :document="viewingDocument"
      :project-id="projectId"
      @close="showDocumentViewer = false"
      @reprocess="reprocessDocument"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileText, Search } from '@lucide/vue'
import { documentsApi } from '@/services/documentsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { filesApi } from '@/services/filesApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { authApi } from '@/services/authApi'
import { useToast } from '@/composables/useToast'
import { debounce } from 'perfect-debounce'
import { setEngineLabels } from '@/utils/ocrLabels'
import { getDateRangeBounds } from '@/utils/dateRange'
import LoadingSpinner from '../common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useFileDownload } from '@/composables/useFileDownload'
import { usePagination } from '@/composables/usePagination'
import DocumentViewer from './DocumentViewer.vue'
import BatchActionsModal from './BatchActionsModal.vue'
import DocumentGroups from './DocumentsGroups.vue'
import CreateDocumentGroupModal from './CreateDocumentGroupModal.vue'
import DocumentsFilters from './DocumentsFilters.vue'
import DocumentsTable from './DocumentsTable.vue'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
})

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { downloadFromApi } = useFileDownload()

// State
const documents = ref([]) // All documents for groups modal
const allDocumentsLoaded = ref(false) // Track if we've fetched all documents
const isLoading = ref(true)
const selectedDocuments = ref([])
const viewingDocument = ref(null)
const showDocumentViewer = ref(false)
const showBatchActions = ref(false)
const batchAction = ref('')
const itemsPerPage = ref(50)
const totalCount = ref(0) // total rows on the server (after filters) — must be declared before usePagination (its getTotal reads it eagerly during setup)
const pagination = usePagination({
  getTotal: () => totalCount.value,
  pageSize: itemsPerPage.value,
})
const currentPage = pagination.currentPage
const activeTab = ref('documents')
const showCreateGroupModal = ref(false)
const createGroupWithDocs = ref([]) // Documents to pre-select when creating group
const serverItems = ref([]) // current page rows from the server
const documentGroupsCount = ref(0) // count of document groups

// Tab config for BaseTabGroup (badges rendered via #tab scoped slot to keep StatusBadge styling)
const tabs = computed(() => [
  { label: 'All Documents', value: 'documents', badge: totalCount.value },
  { label: 'Document Groups', value: 'groups', badge: documentGroupsCount.value },
])

// Filters
const filters = ref({
  search: '',
  dateRange: '',
  ocrEngine: '',
  includeArchived: false,
})

// Custom date range state
const customDateFrom = ref('')
const customDateTo = ref('')

// Track if we've ever loaded documents (for filter UX)
const hasLoadedDocuments = ref(false)

// Check if any filters are active
const hasActiveFilters = computed(() => {
  return (
    filters.value.search ||
    filters.value.dateRange ||
    filters.value.ocrEngine ||
    (filters.value.dateRange === 'custom' && customDateFrom.value) ||
    filters.value.includeArchived
  )
})

// Compute date bounds for date range filter
const computeDateBounds = (range) => {
  return getDateRangeBounds(range, customDateFrom.value, customDateTo.value)
}

// Handle date range change
const handleDateRangeChange = () => {
  if (filters.value.dateRange === 'custom') {
    // Don't fetch yet - wait for user to select dates
    return
  }
  currentPage.value = 1
  fetchDocuments()
}

// Apply custom date range
const applyCustomDateRange = () => {
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

const handlePageChange = (page) => {
  currentPage.value = page
}

const handlePageSizeChange = (size) => {
  itemsPerPage.value = size
  currentPage.value = 1
}

// Handle highlight query parameter (from preprocessing history "Go to Document" navigation)
const handleHighlight = async () => {
  const highlightId = route.query.highlight
  if (!highlightId) return

  try {
    // Fetch the specific document by ID
    const { data } = await documentsApi.get(props.projectId, highlightId)
    if (data) {
      // Open the document viewer
      viewingDocument.value = data
      showDocumentViewer.value = true
      // Clear the highlight parameter without reloading
      router.replace({ query: { ...route.query, highlight: undefined } })
    }
  } catch (error) {
    console.error('Failed to load highlighted document:', error)
    toast.error('Failed to load document')
    // Still clear the parameter to avoid repeated errors
    router.replace({ query: { ...route.query, highlight: undefined } })
  }
}

// Watch for route query changes (e.g., highlight parameter from navigation)
watch(
  () => route.query.highlight,
  (newHighlight) => {
    if (newHighlight) {
      handleHighlight()
    }
  },
  { immediate: true },
)

// Methods
const fetchDocuments = async () => {
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
      compute_stats: true, // Get server-side stats
    }

    const { data } = await documentsApi.list(props.projectId, params)
    serverItems.value = data.items
    totalCount.value = data.total

    // Mark that we've loaded documents at least once (for filter UX)
    hasLoadedDocuments.value = true

    // Safety: if you navigated beyond last page due to a filter change, pull back
    if (
      serverItems.value.length === 0 &&
      totalCount.value > 0 &&
      currentPage.value > totalPages.value
    ) {
      currentPage.value = totalPages.value
      await fetchDocuments()
    }
  } catch (error) {
    toast.error('Failed to load documents')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

const toggleDocumentSelection = (docId) => {
  const index = selectedDocuments.value.indexOf(docId)
  if (index > -1) {
    selectedDocuments.value.splice(index, 1)
  } else {
    selectedDocuments.value.push(docId)
  }
}

const toggleSelectAll = () => {
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

const areAllDocumentsSelected = computed(() => {
  return (
    serverItems.value.length > 0 &&
    serverItems.value.every((doc) => selectedDocuments.value.includes(doc.id))
  )
})

const viewDocument = (doc) => {
  viewingDocument.value = doc
  showDocumentViewer.value = true
}

const downloadDocument = async (doc) => {
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

const performBatchAction = (action) => {
  if (selectedDocuments.value.length === 0) {
    toast.warning('Please select documents first')
    return
  }

  batchAction.value = action
  showBatchActions.value = true
}

const createGroupFromSelection = () => {
  if (selectedDocuments.value.length === 0) {
    toast.warning('Please select documents first')
    return
  }
  createGroupWithDocs.value = [...selectedDocuments.value]
  showCreateGroupModal.value = true
}

const handleCreateGroupModalClose = () => {
  showCreateGroupModal.value = false
  createGroupWithDocs.value = []
}

const handleCreateGroupModalSave = async (groupData) => {
  try {
    await documentSetsApi.create(props.projectId, groupData)
    toast.success('Document group created successfully')
    showCreateGroupModal.value = false
    createGroupWithDocs.value = []
    selectedDocuments.value = []
  } catch (error) {
    toast.error('Failed to create document group')
    console.error(error)
  }
}

// Fetch all documents for the CreateDocumentGroupModal
const fetchAllDocuments = async () => {
  if (allDocumentsLoaded.value) {
    return
  }
  try {
    const PAGE_SIZE = 500
    let offset = 0
    let allDocs = []
    let hasMore = true

    while (hasMore) {
      const { data } = await documentsApi.list(props.projectId, { limit: PAGE_SIZE, offset })
      allDocs = allDocs.concat(data.items || [])
      hasMore = data.items && data.items.length === PAGE_SIZE
      offset += PAGE_SIZE
    }

    documents.value = allDocs
    allDocumentsLoaded.value = true
  } catch (error) {
    console.error('Failed to fetch all documents:', error)
    documents.value = []
  }
}

const handleDocumentsDeleted = (deletedIds) => {
  // Remove successfully deleted documents from selection
  selectedDocuments.value = selectedDocuments.value.filter((id) => !deletedIds.includes(id))
}

const handleBatchComplete = () => {
  // Clear selection and close modal - fetchDocuments will be called separately
  selectedDocuments.value = []
  showBatchActions.value = false
  // Refresh the document list
  fetchDocuments()
}

const handleGroupsRefresh = async () => {
  // Refresh both groups and documents (since documents may have been deleted too)
  await fetchDocumentGroupsCount()
  await fetchDocuments()
}

const reprocessDocument = async (doc) => {
  try {
    const fileId = doc.original_file?.id
    if (!fileId) {
      console.error('Original file id not found for this document!')
      toast.error('Original file id not found for this document!')
      return
    }
    const payload = {
      file_ids: [fileId],
      inline_config: {
        name: `Reprocess ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`,
        additional_settings: {},
      },
      force_reprocess: true,
    }
    await preprocessingApi.create(props.projectId, payload)
    toast.success('Document reprocessing started!')
    fetchDocuments()
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to start reprocessing'))
    console.error(error)
  }
}

const clearFilters = () => {
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

const clearSearchFilter = () => {
  filters.value.search = ''
  currentPage.value = 1
  fetchDocuments()
}

const clearOcrEngineFilter = () => {
  filters.value.ocrEngine = ''
  fetchDocuments()
}

const clearDateRangeFilter = () => {
  filters.value.dateRange = ''
  fetchDocuments()
}

const clearArchivedFilter = () => {
  filters.value.includeArchived = false
  fetchDocuments()
}

const clearCustomDateRange = () => {
  customDateFrom.value = ''
  customDateTo.value = ''
  filters.value.dateRange = ''
  fetchDocuments()
}

// Dispatch individual filter-chip clears to the original handlers (preserves per-filter behavior)
const handleClearFilter = (field) => {
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
const fetchDocumentGroupsCount = async () => {
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
  // Load OCR display names from server
  authApi
    .getSettings()
    .then((r) => setEngineLabels(r.data))
    .catch(() => {})
})
</script>
