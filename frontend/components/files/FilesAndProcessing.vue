<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Files & Preprocessing</h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Upload files and run OCR preprocessing
        </p>
      </div>
      <div class="flex items-center space-x-3">
        <button
          class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
          @click="showUploadModal = true"
        >
          <svg
            class="w-5 h-5 mr-2 text-gray-500 dark:text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m4-3L4 16m0 0l8-8m0 0l8 8"
            />
          </svg>
          Upload Files
        </button>
      </div>
    </div>

    <!-- Upload Zone (shown whenever there are no files and no active filters,
         including a brand-new project after its initial empty fetch) -->
    <FileDropzone
      v-if="!files.length && !hasActiveFilters"
      v-model:dragging="isDragging"
      @drop="uploadFiles"
      @select="uploadFiles"
    />

    <!-- Filters & Search (only when there are files, or active filters to show/clear) -->
    <FilesFilterBar
      v-else
      v-model:search="searchQuery"
      v-model:status="filterStatus"
      v-model:file-type="filterFileType"
      v-model:date-range="filterDateRange"
      v-model:custom-from="customDateFrom"
      v-model:custom-to="customDateTo"
      :total-count="pagination.total"
      @fetch="onFilterFetch"
      @clear-filters="clearFilters"
    />

    <!-- Hint: Select files to preprocess -->
    <div
      v-if="files.length > 0 && selectedFiles.length === 0 && !hasActivePreprocessingTasks"
      class="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg"
    >
      <svg
        class="w-5 h-5 text-blue-600 flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <p class="text-sm text-blue-800">
        <strong>Next step:</strong> Select files from the table below, then click
        <span class="font-semibold">Configure Preprocessing</span> to extract text from your
        documents.
      </p>
      <button
        class="ml-auto text-sm text-blue-600 hover:text-blue-800 font-medium"
        @click="selectedFiles = files.map((f) => f.id)"
      >
        Select all
      </button>
    </div>

    <!-- Loading Indicator -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="large" />
    </div>

    <!-- Files Table -->
    <FilesTable
      v-else-if="hasLoadedFiles && files.length"
      :files="displayFiles"
      :selected-files="selectedFiles"
      :sort-by="sortBy"
      :sort-order="sortOrder"
      :pagination="pagination"
      @toggle-selection="toggleSelection"
      @toggle-all="toggleSelectAll"
      @preview="previewFile"
      @download="downloadFile"
      @delete="confirmDeleteFile"
      @configure-import="openImportConfigModal"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      @sort="handleSort"
      @view-history="handleViewHistory"
      @select-all-files="selectAllFiles"
      @clear-selection="clearSelection"
    />

    <!-- Slide-in Preprocessing History Panel -->
    <PreprocessingHistoryPanel
      :open="showHistoryPanel"
      :history-file="historyFile"
      :highlight-task-id="highlightTaskId"
      @close="showHistoryPanel = false"
      @navigate="navigateToDocument"
      @retry="retryFailedFiles"
      @cancel="cancelPreprocessingTask"
      @process="processFileAndClose"
      @process-panel="processFileAndClosePanel"
    />

    <!-- Empty State: filters active but returned nothing -->
    <div
      v-if="!files.length && !isDragging && hasLoadedFiles && hasActiveFilters"
      class="text-center py-12"
    >
      <svg
        class="mx-auto h-16 w-16 text-gray-300"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      <p class="mt-4 text-lg font-medium text-gray-900 dark:text-white">
        No files match your filters
      </p>
      <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
        Try adjusting or clearing your filters to see more results
      </p>
      <button
        class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        @click="clearFilters"
      >
        Clear All Filters
      </button>
    </div>

    <!-- Floating Batch Toolbar -->
    <div
      v-if="selectedFiles.length > 0"
      class="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50"
    >
      <div
        class="bg-gray-900 text-white rounded-xl shadow-2xl px-6 py-3 flex items-center space-x-4"
      >
        <span class="font-medium"
          >{{ selectedFiles.length }} file{{ selectedFiles.length !== 1 ? 's' : '' }} selected</span
        >
        <!-- Warning indicator for unconfigured CSV/XLSX -->
        <span
          v-if="unconfiguredCsvXlsxFiles.length > 0"
          class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500 text-white"
          :title="
            unconfiguredCsvXlsxFiles.map((f) => f.file_name).join(', ') +
            ' need(s) import configuration'
          "
        >
          <svg class="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          {{ unconfiguredCsvXlsxFiles.length }} needs config
        </span>
        <button
          class="text-sm text-gray-300 hover:text-white underline"
          @click="selectedFiles = []"
        >
          Clear
        </button>
        <div class="w-px h-5 bg-gray-700" />
        <button
          :disabled="unconfiguredCsvXlsxFiles.length > 0"
          :class="[
            'inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            unconfiguredCsvXlsxFiles.length > 0
              ? 'bg-gray-600 cursor-not-allowed opacity-75'
              : 'bg-blue-600 hover:bg-blue-700',
          ]"
          @click="openProcessingPanel"
        >
          <svg
            v-if="unconfiguredCsvXlsxFiles.length === 0"
            class="w-4 h-4 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <svg v-else class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          {{
            unconfiguredCsvXlsxFiles.length > 0
              ? 'Configure Files First'
              : 'Configure Preprocessing'
          }}
        </button>
      </div>
    </div>

    <!-- Slide-in Preprocessing Config Panel -->
    <PreprocessingConfigPanel
      :open="showProcessingPanel"
      :selected-files="selectedFiles"
      :get-file-by-id="getFileById"
      :unconfigured-csv-xlsx-files="unconfiguredCsvXlsxFiles"
      :can-start-processing="canStartProcessing"
      :is-submitting="isSubmitting"
      :docling-ocr-enabled="doclingOcrEnabled"
      :mistral-ocr-enabled="mistralOcrEnabled"
      :vision-ocr-enabled="visionOcrEnabled"
      @close="showProcessingPanel = false"
      @remove-file="toggleSelection"
      @clear-and-close="clearSelectionAndClosePanel"
      @start="startProcessing"
    />

    <!-- Upload Modal -->
    <UploadFilesModal
      :open="showUploadModal"
      @close="showUploadModal = false"
      @files="uploadFiles"
    />

    <!-- File Preview Modal -->
    <FilePreviewModal
      v-if="previewingFile"
      :file="previewingFile"
      :project-id="projectId"
      @close="previewingFile = null"
    />

    <!-- File Import Config Modal -->
    <FileImportConfigModal
      v-if="showImportConfigModal && configuringFile"
      :file="configuringFile"
      :project-id="projectId"
      @close="
        () => {
          showImportConfigModal = false
          configuringFile = null
        }
      "
      @saved="
        () => {
          showImportConfigModal = false
          configuringFile = null
          fetchFiles()
          emit('files-changed')
        }
      "
    />

    <!-- Duplicate Preview Confirmation Modal -->
    <DuplicatePreviewModal
      :open="showDuplicatePreviewModal"
      :duplicate-preview="duplicatePreview"
      @confirm="onDuplicateConfirm"
      @cancel="cancelDuplicatePreview"
    />
  </div>
</template>

<script setup>
import { ref, computed, toRef, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { filesApi } from '@/services/filesApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { authApi } from '@/services/authApi'
import { useToast } from 'vue-toastification'
import FilePreviewModal from '@/components/files/FilePreviewModal.vue'
import FilesTable from '@/components/files/FilesTable.vue'
import FileImportConfigModal from '@/components/files/FileImportConfigModal.vue'
import FileDropzone from '@/components/files/FileDropzone.vue'
import FilesFilterBar from '@/components/files/FilesFilterBar.vue'
import PreprocessingHistoryPanel from '@/components/files/PreprocessingHistoryPanel.vue'
import PreprocessingConfigPanel from '@/components/files/PreprocessingConfigPanel.vue'
import UploadFilesModal from '@/components/files/UploadFilesModal.vue'
import DuplicatePreviewModal from '@/components/files/DuplicatePreviewModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { setEngineLabels } from '@/utils/ocrLabels'
import { getDateRangeBounds } from '@/utils/dateRange'
import { useFileDownload } from '@/composables/useFileDownload'
import { usePreprocessingUpdates } from '@/composables/usePreprocessingUpdates'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
})

const emit = defineEmits(['files-changed'])
const toast = useToast()
const router = useRouter()
const { downloadBlob } = useFileDownload()

// State
const files = ref([])
const selectedFiles = ref([])
const searchQuery = ref('')
const filterStatus = ref('')
const filterFileType = ref('')
const filterDateRange = ref('')
const isDragging = ref(false)
const showUploadModal = ref(false)
const showProcessingPanel = ref(false)
const showHistoryPanel = ref(false)
const historyFile = ref(null)
const highlightTaskId = ref(null)
const previewingFile = ref(null)
const fileToDelete = ref(null)
const showImportConfigModal = ref(false)
const configuringFile = ref(null)
const isLoading = ref(true)
const hasLoadedFiles = ref(false) // Track if we've ever loaded files (for filter UX)

// Custom date range state
const customDateFrom = ref('')
const customDateTo = ref('')

// Duplicate preview state
const showDuplicatePreviewModal = ref(false)
const duplicatePreview = ref(null)
const pendingProcessingSettings = ref(null)

// "Select all" across all pages state
const selectAllMode = ref(false) // true = all files in project, false = only current page

// Pagination state
const pagination = ref({
  page: 1,
  page_size: 50,
  total: 0,
  total_pages: 0,
  start: 0,
  end: 0,
})

// Sorting state
const sortBy = ref('created_at')
const sortOrder = ref('desc')

// OCR engine availability (from server settings)
const visionOcrEnabled = ref(false)
const mistralOcrEnabled = ref(false)
const doclingOcrEnabled = ref(true)
const isSubmitting = ref(false)

// Cache for preprocessing tasks to avoid refetching on every file refresh
let cachedTasks = null
let cachedTasksTimestamp = null
const TASKS_CACHE_TTL_MS = 30000 // 30 seconds cache (increased for 50k+ files scaling)

const invalidateTaskCache = () => {
  cachedTasks = null
  cachedTasksTimestamp = null
}

// Compute date bounds for date range filter
const getDateBounds = (range) => {
  return getDateRangeBounds(range, customDateFrom.value, customDateTo.value)
}

// Check if any filters are active (status intentionally excluded — matches original logic)
const hasActiveFilters = computed(() => {
  return searchQuery.value || filterStatus.value || filterFileType.value || filterDateRange.value
})

// Fetch on any filter change emitted by the filter bar (resets to first page)
const onFilterFetch = () => {
  pagination.value.page = 1
  fetchFiles()
}

// Clear all filters
const clearFilters = () => {
  searchQuery.value = ''
  filterStatus.value = ''
  filterFileType.value = ''
  filterDateRange.value = ''
  customDateFrom.value = ''
  customDateTo.value = ''
  pagination.value.page = 1
  fetchFiles()
}

// Fetch files with preprocessing tasks (paginated)
const fetchFiles = async (options = {}) => {
  const { forceRefreshTasks = false } = options

  try {
    const params = new URLSearchParams({
      page: String(pagination.value.page),
      page_size: String(pagination.value.page_size),
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    })

    // Add search filter
    if (searchQuery.value) {
      params.append('search', searchQuery.value)
    }

    // Add status filter
    if (filterStatus.value) {
      params.append('status', filterStatus.value)
    }

    // Add file type filter
    if (filterFileType.value) {
      params.append('file_type', filterFileType.value)
    }

    // Add date range filter
    if (filterDateRange.value) {
      const { date_from, date_to } = getDateBounds(filterDateRange.value)
      if (date_from) params.append('date_from', date_from)
      if (date_to) params.append('date_to', date_to)
    }

    const response = await filesApi.list(props.projectId, params)
    const data = response.data

    // Update pagination
    pagination.value = {
      page: data.page || 1,
      page_size: data.page_size || 25,
      total: data.total || 0,
      total_pages: data.total_pages || 0,
      start: (data.page - 1) * data.page_size + 1,
      end: Math.min(data.page * data.page_size, data.total),
    }

    // Fetch preprocessing tasks with caching to avoid refetching on every file refresh
    const now = Date.now()
    const needTasks =
      forceRefreshTasks ||
      !cachedTasks ||
      !cachedTasksTimestamp ||
      now - cachedTasksTimestamp > TASKS_CACHE_TTL_MS

    let allTasks = []
    if (needTasks) {
      const tasksResponse = await preprocessingApi.list(props.projectId, { limit: 100 })
      allTasks = tasksResponse.data || []
      cachedTasks = allTasks
      cachedTasksTimestamp = now
    } else {
      allTasks = cachedTasks
    }

    // Build a map: file_id -> [tasks]
    const tasksByFileId = new Map()
    for (const task of allTasks) {
      if (task.file_tasks && Array.isArray(task.file_tasks)) {
        for (const ft of task.file_tasks) {
          const fid = ft.file_id
          if (!tasksByFileId.has(fid)) {
            tasksByFileId.set(fid, [])
          }
          tasksByFileId.get(fid).push(task)
        }
      }
    }

    // Create new file objects with _status and preprocessing_tasks for proper reactivity
    const filesWithTasks = (data.items || []).map((file) => {
      const fileTasks = tasksByFileId.get(file.id) || []
      const sortedTasks = fileTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      return {
        ...file,
        preprocessing_tasks: sortedTasks,
        _status: getFileStatus({ ...file, preprocessing_tasks: sortedTasks }),
      }
    })

    files.value = filesWithTasks

    // Mark that we've loaded files at least once (for filter UX)
    hasLoadedFiles.value = true

    // Update historyFile if panel is open
    if (showHistoryPanel.value && historyFile.value) {
      const updatedHistoryFile = filesWithTasks.find((f) => f.id === historyFile.value.id)
      if (updatedHistoryFile) {
        historyFile.value = { ...updatedHistoryFile }
      }
    }
  } catch (err) {
    console.error('Failed to fetch files:', err)
    toast.error('Failed to load files')
  } finally {
    isLoading.value = false
  }
}

// Display files (for the table - just returns files.value since pagination is server-side)
const displayFiles = computed(() => files.value)

// Get file status based on latest preprocessing task
const getFileStatus = (file) => {
  if (!file || !Array.isArray(file.preprocessing_tasks) || file.preprocessing_tasks.length === 0) {
    return 'not_preprocessed'
  }

  const latestTask = [...file.preprocessing_tasks].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at),
  )[0]

  if (!latestTask) return 'not_preprocessed'

  const status = String(latestTask.status || '').toLowerCase()

  if (['pending', 'processing', 'in_progress'].includes(status)) {
    return 'processing'
  } else if (status === 'completed') {
    return 'completed'
  } else {
    return 'failed'
  }
}

// Pagination handlers
const handlePageChange = (newPage) => {
  if (newPage >= 1 && newPage <= pagination.value.total_pages) {
    pagination.value.page = newPage
    fetchFiles()
  }
}

const handlePageSizeChange = (newSize) => {
  pagination.value.page_size = Number(newSize)
  pagination.value.page = 1 // Reset to first page
  fetchFiles()
}

// Sorting handler
const handleSort = (field) => {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortOrder.value = 'desc'
  }
  pagination.value.page = 1 // Reset to first page
  fetchFiles()
}

// Toggle file selection
const toggleSelection = (fileId) => {
  const idx = selectedFiles.value.indexOf(fileId)
  if (idx > -1) {
    selectedFiles.value.splice(idx, 1)
  } else {
    selectedFiles.value.push(fileId)
  }
}

// Toggle select all (for current page only)
const toggleSelectAll = () => {
  if (selectedFiles.value.length === files.value.length) {
    selectedFiles.value = []
    selectAllMode.value = false
  } else {
    selectedFiles.value = files.value.map((f) => f.id)
    selectAllMode.value = false
  }
}

// Select ALL files across all pages (for 50k+ files)
const selectAllFiles = async () => {
  selectAllMode.value = true
  // Fetch all file IDs from the project (server-side)
  try {
    // We need to fetch all file IDs - use a minimal request
    // This is a one-time operation even for large projects
    const allFileIds = []
    let page = 1
    const pageSize = 250 // Max allowed per page

    while (true) {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
      })

      if (searchQuery.value) params.append('search', searchQuery.value)
      if (filterStatus.value) params.append('file_type', filterStatus.value)

      const response = await filesApi.list(props.projectId, params)
      const fileIds = response.data.items.map((f) => f.id)
      allFileIds.push(...fileIds)

      if (page >= response.data.total_pages) break
      page++
    }

    selectedFiles.value = allFileIds
    toast.success(`Selected all ${allFileIds.length} files`)
  } catch (err) {
    console.error('Failed to select all files:', err)
    toast.error('Failed to select all files')
    selectAllMode.value = false
  }
}

// Clear selection
const clearSelection = () => {
  selectedFiles.value = []
  selectAllMode.value = false
}

// Clear selection and close the processing panel (for "Select different files")
const clearSelectionAndClosePanel = () => {
  selectedFiles.value = []
  showProcessingPanel.value = false
}

// Navigate to document
const navigateToDocument = (documentId) => {
  // Close the history panel (the panel's scroll lock releases via its open watcher)
  showHistoryPanel.value = false
  // Switch to documents tab and highlight the document
  emit('files-changed') // Trigger parent to refresh if needed
  router.push({
    path: `/projects/${props.projectId}`,
    query: { tab: 'documents', highlight: documentId },
  })
}

// Confirm delete file
const confirmDeleteFile = (file) => {
  fileToDelete.value = file
  // Could open a confirmation modal here - for now we'll use browser confirm
  if (confirm(`Delete "${file.file_name}"? This action cannot be undone.`)) {
    deleteFile(file)
  }
  fileToDelete.value = null
}

// Delete file
const deleteFile = async (file) => {
  try {
    await filesApi.delete(props.projectId, file.id)
    toast.success(`Deleted ${file.file_name}`)
    // Invalidate task cache when files change
    invalidateTaskCache()
    await fetchFiles({ forceRefreshTasks: true })
    emit('files-changed')
  } catch (err) {
    console.error('Failed to delete file:', err)
    toast.error(`Failed to delete ${file.file_name}`)
  }
}

// Open import config modal
const openImportConfigModal = (file) => {
  configuringFile.value = file
  showImportConfigModal.value = true
}

// Get file by ID (for panel display)
const getFileById = (id) => {
  return files.value.find((f) => f.id === id)
}

// Handle view preprocessing history
const handleViewHistory = (file) => {
  historyFile.value = file
  showHistoryPanel.value = true
}

// Process file and close history panel
const processFileAndClose = (file) => {
  quickProcessFile(file)
  showHistoryPanel.value = false
}

// Process file and close panel (for footer button)
const processFileAndClosePanel = (file) => {
  quickProcessFile(file)
  showHistoryPanel.value = false
}

// Retry failed files for a task
const retryFailedFiles = async (taskId) => {
  try {
    await preprocessingApi.retryFailed(props.projectId, taskId)
    toast.success('Retrying failed files...')
    // Refresh files to show new task
    await fetchFiles()
  } catch (err) {
    console.error('Failed to retry failed files:', err)
    toast.error('Failed to retry failed files')
  }
}

// Cancel preprocessing task
const cancelPreprocessingTask = async (task) => {
  if (
    !confirm(
      'Cancel this preprocessing task? Any files still being processed will be marked as failed.',
    )
  ) {
    return
  }
  try {
    await preprocessingApi.cancel(props.projectId, task.id, true)
    toast.success('Preprocessing cancelled')
    // Close the history panel if open
    showHistoryPanel.value = false
    historyFile.value = null
    // Full refresh to get updated state from server
    await fetchFiles()
  } catch (err) {
    console.error('Failed to cancel preprocessing:', err)
    toast.error('Failed to cancel preprocessing')
  }
}

// Preview file
const previewFile = (file) => {
  previewingFile.value = file
}

// Download file
const downloadFile = async (file) => {
  try {
    const response = await filesApi.getContent(props.projectId, file.id)
    downloadBlob(response.data, file.file_name)
  } catch {
    toast.error(`Failed to download ${file.file_name}`)
  }
}

// Quick process single file
const quickProcessFile = (file) => {
  selectedFiles.value = [file.id]
  openProcessingPanel()
}

// Open processing panel
const openProcessingPanel = () => {
  showProcessingPanel.value = true
}

// Check if any selected CSV/XLSX files lack preprocessing strategy
const unconfiguredCsvXlsxFiles = computed(() => {
  return files.value.filter((f) => {
    if (!selectedFiles.value.includes(f.id)) return false
    const isCsvXlsx =
      f.file_type === 'text/csv' ||
      f.file_type === 'application/vnd.ms-excel' ||
      f.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return isCsvXlsx && !f.preprocessing_strategy
  })
})

// Can start processing
const canStartProcessing = computed(() => {
  return (
    selectedFiles.value.length > 0 &&
    !isSubmitting.value &&
    unconfiguredCsvXlsxFiles.value.length === 0
  )
})

// Check if any files have active preprocessing tasks
const hasActivePreprocessingTasks = computed(() => {
  return files.value.some((f) =>
    f.preprocessing_tasks?.some((t) =>
      ['pending', 'processing', 'in_progress'].includes(String(t.status || '').toLowerCase()),
    ),
  )
})

// Check for duplicates and start processing (or show confirmation).
// Receives the built settings payload from PreprocessingConfigPanel.
const startProcessing = async (payload) => {
  if (!canStartProcessing.value) return

  isSubmitting.value = true

  // Store settings for later use
  pendingProcessingSettings.value = payload

  try {
    // First, check for duplicates
    const previewResponse = await preprocessingApi.preview(
      props.projectId,
      pendingProcessingSettings.value,
    )

    duplicatePreview.value = previewResponse.data

    // Only show modal if there are same-config duplicates (not just different OCR configs)
    // Also show if PDFs with embedded text exist (to inform user OCR won't affect result)
    const hasSameConfigDuplicates =
      previewResponse.data.same_config_duplicates &&
      previewResponse.data.same_config_duplicates.length > 0
    const hasPdfsWithEmbeddedText =
      previewResponse.data.pdfs_with_embedded_text &&
      previewResponse.data.pdfs_with_embedded_text.length > 0

    if (hasSameConfigDuplicates || hasPdfsWithEmbeddedText) {
      showDuplicatePreviewModal.value = true
      isSubmitting.value = false // Reset loading state while waiting for user confirmation
      return // Exit early - actual processing happens after confirmation
    }

    // No same-config duplicates - proceed directly
    await confirmAndStartProcessing()
  } catch (err) {
    console.error('Failed to check for duplicates:', err)
    isSubmitting.value = false
    const detail = err.response?.data?.detail
    let errorMsg = 'Failed to check for existing documents'
    if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0]
      errorMsg = firstError.msg || JSON.stringify(firstError)
    } else if (typeof detail === 'string') {
      errorMsg = detail
    }
    toast.error(errorMsg)
    pendingProcessingSettings.value = null
  }
}

// Cancel duplicate preview and close modal
const cancelDuplicatePreview = () => {
  showDuplicatePreviewModal.value = false
  duplicatePreview.value = null
  pendingProcessingSettings.value = null
  isSubmitting.value = false
}

// User confirmed the duplicate preview modal — proceed with the skipExisting choice.
const onDuplicateConfirm = ({ skipExisting }) => {
  confirmAndStartProcessing(skipExisting)
}

// Confirm and start processing (called after user approves duplicate preview)
const confirmAndStartProcessing = async (skipExisting = false) => {
  if (!pendingProcessingSettings.value) return

  // Add skip_existing flag if user selected it
  if (skipExisting) {
    pendingProcessingSettings.value.skip_existing = true
  }

  try {
    await preprocessingApi.create(props.projectId, pendingProcessingSettings.value)

    const firstSelectedFileId = pendingProcessingSettings.value.file_ids[0]

    toast.success(
      `Preprocessing started for ${pendingProcessingSettings.value.file_ids.length} file(s)`,
    )
    showProcessingPanel.value = false
    showDuplicatePreviewModal.value = false
    selectedFiles.value = []
    duplicatePreview.value = null
    pendingProcessingSettings.value = null

    // Invalidate task cache when starting new preprocessing
    invalidateTaskCache()
    // Refresh files with forced task refresh to show the new task immediately
    await fetchFiles({ forceRefreshTasks: true })

    // Auto-open history panel for the first file to show the new task
    if (firstSelectedFileId) {
      const file = files.value.find((f) => f.id === firstSelectedFileId)
      if (file) {
        historyFile.value = file
        showHistoryPanel.value = true
      }
    }
  } catch (err) {
    console.error('Failed to start processing:', err)
    const detail = err.response?.data?.detail
    let errorMsg = 'Failed to start preprocessing'

    // Handle structured error response
    if (detail && typeof detail === 'object') {
      if (detail.code === 'csv_xlsx_needs_config') {
        errorMsg = detail.message || 'CSV/XLSX files need import configuration'
      } else if (detail.code === 'files_already_being_processed') {
        errorMsg = detail.message || 'One or more files are already being processed'
      } else if (detail.code === 'no_ocr_engine_enabled') {
        errorMsg = detail.message || 'No OCR engine enabled'
      } else if (detail.message) {
        errorMsg = detail.message
      }
    } else if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0]
      errorMsg = firstError.msg || JSON.stringify(firstError)
    } else if (typeof detail === 'string') {
      errorMsg = detail
    }

    toast.error(errorMsg)
  } finally {
    isSubmitting.value = false
  }
}

// Upload files
const uploadFiles = async (fileList) => {
  if (!fileList.length) return

  isSubmitting.value = true

  for (const file of fileList) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append(
        'file_info',
        JSON.stringify({
          file_name: file.name,
          file_type: file.type,
          file_size: file.size,
        }),
      )

      await filesApi.upload(props.projectId, formData)

      toast.success(`Uploaded ${file.name}`)
    } catch (err) {
      console.error(`Failed to upload ${file.name}:`, err)
      toast.error(`Failed to upload ${file.name}`)
    }
  }

  isSubmitting.value = false
  showUploadModal.value = false
  // Invalidate task cache when files change
  invalidateTaskCache()
  await fetchFiles({ forceRefreshTasks: true })
  emit('files-changed')
}

// Fetch OCR settings on mount to use server-provided display names
const fetchOcrSettings = async () => {
  try {
    const res = await authApi.getSettings()
    setEngineLabels(res.data)
    visionOcrEnabled.value = res.data.vision_ocr_enabled || false
    mistralOcrEnabled.value = res.data.mistral_ocr_enabled || false
    doclingOcrEnabled.value =
      res.data.docling_serve_enabled !== undefined ? res.data.docling_serve_enabled : true
    // NOTE: selected-engine reset on disabled engine now handled inside
    // PreprocessingConfigPanel via its availability-prop watcher.
  } catch (err) {
    console.error('Failed to fetch OCR settings:', err)
  }
}

// WebSocket subscription for preprocessing updates
const { start: startWebSocket, stop: stopWebSocket } = usePreprocessingUpdates({
  projectId: toRef(props, 'projectId'),
  files,
  historyFile,
  getFileStatus,
  fetchFiles,
  invalidateTaskCache,
})

// Handle expand-preprocessing-task event from ActivityBell
const handleExpandTask = (event) => {
  const taskId = event.detail?.id
  if (!taskId) return

  // Try to find and expand the task, retrying a few times if files aren't loaded yet
  const tryExpandTask = (attempts = 0) => {
    const fileWithTask = files.value.find((f) =>
      f.preprocessing_tasks?.some((t) => t.id === Number(taskId)),
    )
    if (fileWithTask) {
      // Open the history panel for this file
      historyFile.value = fileWithTask
      showHistoryPanel.value = true
      // Expand the specific task (the panel watches highlightTaskId)
      highlightTaskId.value = Number(taskId)
    } else if (attempts < 5) {
      // Retry after a short delay if files aren't loaded yet
      setTimeout(() => tryExpandTask(attempts + 1), 200)
    }
  }
  tryExpandTask()
}

onMounted(async () => {
  fetchFiles()
  fetchOcrSettings()
  startWebSocket()
  // Listen for expand event from ActivityBell
  document.addEventListener('expand-preprocessing-task', handleExpandTask)
})

onUnmounted(() => {
  stopWebSocket()
  document.removeEventListener('expand-preprocessing-task', handleExpandTask)
  // Ensure scroll lock is released when component unmounts
  document.body.style.overflow = ''
})
</script>
