<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-2xl font-bold text-slate-900 dark:text-white">Files & Preprocessing</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Upload files and run OCR preprocessing
        </p>
      </div>
      <div class="flex items-center space-x-3">
        <BaseButton variant="secondary" @click="showUploadModal = true">
          <Upload class="w-5 h-5 mr-2 text-slate-500 dark:text-slate-400" />
          Upload Files
        </BaseButton>
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
      class="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg"
    >
      <Info class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
      <p class="text-sm text-blue-800 dark:text-blue-300">
        <strong>Next step:</strong> Select files from the table below, then click
        <span class="font-semibold">Configure Preprocessing</span> to extract text from your
        documents.
      </p>
      <BaseButton
        variant="ghost"
        size="sm"
        class="ml-auto font-medium"
        @click="selectedFiles = files.map((f) => f.id)"
      >
        Select all
      </BaseButton>
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
    <EmptyState
      v-if="!files.length && !isDragging && hasLoadedFiles && hasActiveFilters"
      title="No files match your filters"
      description="Try adjusting or clearing your filters to see more results"
      action-text="Clear All Filters"
      @action="clearFilters"
    >
      <template #icon>
        <Search class="h-16 w-16 mx-auto text-slate-300 dark:text-slate-600" aria-hidden="true" />
      </template>
    </EmptyState>

    <!-- Floating Batch Toolbar -->
    <div
      v-if="selectedFiles.length > 0"
      class="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50"
    >
      <div
        class="bg-slate-900 text-white rounded-xl shadow-2xl px-6 py-3 flex items-center space-x-4"
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
          <AlertTriangle class="w-3 h-3 mr-1" />
          {{ unconfiguredCsvXlsxFiles.length }} needs config
        </span>
        <BaseButton
          variant="ghost"
          size="sm"
          class="text-slate-300 underline"
          @click="selectedFiles = []"
        >
          Clear
        </BaseButton>
        <div class="w-px h-5 bg-slate-700" />
        <BaseButton :disabled="unconfiguredCsvXlsxFiles.length > 0" @click="openProcessingPanel">
          <Settings v-if="unconfiguredCsvXlsxFiles.length === 0" class="w-4 h-4 mr-2" />
          <AlertTriangle v-else class="w-4 h-4 mr-2" />
          {{
            unconfiguredCsvXlsxFiles.length > 0
              ? 'Configure Files First'
              : 'Configure Preprocessing'
          }}
        </BaseButton>
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
      :open="showFilePreview"
      :file="previewingFile"
      :project-id="projectId"
      @close="showFilePreview = false"
    />

    <!-- File Import Config Modal -->
    <FileImportConfigModal
      :open="showImportConfigModal && !!configuringFile"
      :file="configuringFile"
      :project-id="projectId"
      @close="showImportConfigModal = false"
      @saved="
        () => {
          showImportConfigModal = false
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

    <!-- Delete file confirmation -->
    <ConfirmationDialog
      :open="showDeleteFileConfirm"
      title="Delete file?"
      :message="`Delete “${fileToDelete?.file_name}”? This action cannot be undone.`"
      confirm-text="Delete"
      cancel-text="Cancel"
      confirm-variant="danger"
      @confirm="executeDeleteFile"
      @cancel="showDeleteFileConfirm = false"
    />

    <!-- Cancel preprocessing task confirmation -->
    <ConfirmationDialog
      :open="showCancelTaskConfirm"
      title="Cancel preprocessing task?"
      message="Any files still being processed will be marked as failed."
      confirm-text="Cancel task"
      cancel-text="Keep running"
      confirm-variant="danger"
      @confirm="executeCancelTask"
      @cancel="showCancelTaskConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, toRef, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { AlertTriangle, Info, Search, Settings, Upload } from '@lucide/vue'
import { filesApi } from '@/services/filesApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { authApi } from '@/services/authApi'
import { useToast } from '@/composables/useToast'
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
import BaseButton from '@/components/common/BaseButton.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { setEngineLabels } from '@/utils/ocrLabels'
import { getDateRangeBounds } from '@/utils/dateRange'
import { useFileDownload } from '@/composables/useFileDownload'
import { usePreprocessingUpdates } from '@/composables/usePreprocessingUpdates'
import type { FileWithTasks } from '@/composables/usePreprocessingUpdates'
import { extractErrorMessage } from '@/utils/errors'
import type {
  File as FileModel,
  PreprocessingTask,
  PreprocessingTaskCreate,
  PreprocessingDuplicatePreview,
} from '@/types'

interface Props {
  projectId: string | number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'files-changed': []
}>()
const toast = useToast()
const router = useRouter()
const { downloadBlob } = useFileDownload()

// State
const files = ref<FileWithTasks[]>([])
const selectedFiles = ref<number[]>([])
const searchQuery = ref('')
const filterStatus = ref('')
const filterFileType = ref('')
const filterDateRange = ref('')
const isDragging = ref(false)
const showUploadModal = ref(false)
const showProcessingPanel = ref(false)
const showHistoryPanel = ref(false)
const historyFile = ref<FileWithTasks | null>(null)
const highlightTaskId = ref<number | null>(null)
const previewingFile = ref<FileModel | null>(null)
const showFilePreview = ref(false)
const fileToDelete = ref<FileModel | null>(null)
const showImportConfigModal = ref(false)
const configuringFile = ref<FileModel | null>(null)
const isLoading = ref(true)
const hasLoadedFiles = ref(false) // Track if we've ever loaded files (for filter UX)

// Custom date range state
const customDateFrom = ref('')
const customDateTo = ref('')

// Duplicate preview state
const showDuplicatePreviewModal = ref(false)
const duplicatePreview = ref<PreprocessingDuplicatePreview | null>(null)
const pendingProcessingSettings = ref<PreprocessingTaskCreate | null>(null)

// "Select all" across all pages state
const selectAllMode = ref(false) // true = all files in project, false = only current page

interface PaginationState {
  page: number
  page_size: number
  total: number
  total_pages: number
  start: number
  end: number
}

// Pagination state
const pagination = ref<PaginationState>({
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
let cachedTasks: PreprocessingTask[] | null = null
let cachedTasksTimestamp: number | null = null
const TASKS_CACHE_TTL_MS = 30000 // 30 seconds cache (increased for 50k+ files scaling)

const invalidateTaskCache = (): void => {
  cachedTasks = null
  cachedTasksTimestamp = null
}

// Compute date bounds for date range filter
const getDateBounds = (range: string): { date_from?: string; date_to?: string } => {
  return getDateRangeBounds(range, customDateFrom.value, customDateTo.value)
}

// Check if any filters are active (status intentionally excluded — matches original logic)
const hasActiveFilters = computed(() => {
  return searchQuery.value || filterStatus.value || filterFileType.value || filterDateRange.value
})

// Fetch on any filter change emitted by the filter bar (resets to first page)
const onFilterFetch = (): void => {
  pagination.value.page = 1
  fetchFiles()
}

// Clear all filters
const clearFilters = (): void => {
  searchQuery.value = ''
  filterStatus.value = ''
  filterFileType.value = ''
  filterDateRange.value = ''
  customDateFrom.value = ''
  customDateTo.value = ''
  pagination.value.page = 1
  fetchFiles()
}

// Get file status based on latest preprocessing task
const getFileStatus = (file: FileWithTasks): string => {
  if (!file || !Array.isArray(file.preprocessing_tasks) || file.preprocessing_tasks.length === 0) {
    return 'not_preprocessed'
  }

  const latestTask = [...file.preprocessing_tasks].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
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

// Fetch files with preprocessing tasks (paginated)
const fetchFiles = async (options: { forceRefreshTasks?: boolean } = {}): Promise<void> => {
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

    const response = await filesApi.list(
      props.projectId,
      params as unknown as Record<string, unknown>,
    )
    const data = response.data as {
      items?: FileModel[]
      page?: number
      page_size?: number
      total?: number
      total_pages?: number
    }

    // Update pagination
    const page = data.page || 1
    const pageSize = data.page_size || 25
    const total = data.total || 0
    pagination.value = {
      page,
      page_size: pageSize,
      total,
      total_pages: data.total_pages || 0,
      start: (page - 1) * pageSize + 1,
      end: Math.min(page * pageSize, total),
    }

    // Fetch preprocessing tasks with caching to avoid refetching on every file refresh
    const now = Date.now()
    const needTasks =
      forceRefreshTasks ||
      !cachedTasks ||
      !cachedTasksTimestamp ||
      now - cachedTasksTimestamp > TASKS_CACHE_TTL_MS

    let allTasks: PreprocessingTask[] = []
    if (needTasks) {
      const tasksResponse = await preprocessingApi.list(props.projectId, { limit: 100 })
      allTasks = (tasksResponse.data as PreprocessingTask[]) || []
      cachedTasks = allTasks
      cachedTasksTimestamp = now
    } else {
      allTasks = cachedTasks ?? []
    }

    // Build a map: file_id -> [tasks]
    const tasksByFileId = new Map<number, PreprocessingTask[]>()
    for (const task of allTasks) {
      if (task.file_tasks && Array.isArray(task.file_tasks)) {
        for (const ft of task.file_tasks) {
          const fid = ft.file_id
          if (!tasksByFileId.has(fid)) {
            tasksByFileId.set(fid, [])
          }
          tasksByFileId.get(fid)!.push(task)
        }
      }
    }

    // Create new file objects with _status and preprocessing_tasks for proper reactivity
    const filesWithTasks: FileWithTasks[] = (data.items || []).map((file) => {
      const fileTasks = tasksByFileId.get(file.id) || []
      const sortedTasks = fileTasks.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )
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
      const updatedHistoryFile = filesWithTasks.find((f) => f.id === historyFile.value!.id)
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

// Pagination handlers
const handlePageChange = (newPage: number): void => {
  if (newPage >= 1 && newPage <= pagination.value.total_pages) {
    pagination.value.page = newPage
    fetchFiles()
  }
}

const handlePageSizeChange = (newSize: number | string): void => {
  pagination.value.page_size = Number(newSize)
  pagination.value.page = 1 // Reset to first page
  fetchFiles()
}

// Sorting handler
const handleSort = (field: string): void => {
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
const toggleSelection = (fileId: number): void => {
  const idx = selectedFiles.value.indexOf(fileId)
  if (idx > -1) {
    selectedFiles.value.splice(idx, 1)
  } else {
    selectedFiles.value.push(fileId)
  }
}

// Toggle select all (for current page only)
const toggleSelectAll = (): void => {
  if (selectedFiles.value.length === files.value.length) {
    selectedFiles.value = []
    selectAllMode.value = false
  } else {
    selectedFiles.value = files.value.map((f) => f.id)
    selectAllMode.value = false
  }
}

// Select ALL files across all pages (for 50k+ files)
const selectAllFiles = async (): Promise<void> => {
  selectAllMode.value = true
  // Fetch all file IDs from the project (server-side)
  try {
    // We need to fetch all file IDs - use a minimal request
    // This is a one-time operation even for large projects
    const allFileIds: number[] = []
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

      const response = await filesApi.list(
        props.projectId,
        params as unknown as Record<string, unknown>,
      )
      const respData = response.data as { items: FileModel[]; total_pages: number }
      const fileIds = respData.items.map((f) => f.id)
      allFileIds.push(...fileIds)

      if (page >= respData.total_pages) break
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
const clearSelection = (): void => {
  selectedFiles.value = []
  selectAllMode.value = false
}

// Clear selection and close the processing panel (for "Select different files")
const clearSelectionAndClosePanel = (): void => {
  selectedFiles.value = []
  showProcessingPanel.value = false
}

// Navigate to document
const navigateToDocument = (documentId: number): void => {
  // Close the history panel (the panel's scroll lock releases via its open watcher)
  showHistoryPanel.value = false
  // Switch to documents tab and highlight the document
  emit('files-changed') // Trigger parent to refresh if needed
  router.push({
    path: `/projects/${props.projectId}`,
    query: { tab: 'documents', highlight: documentId },
  })
}

// Confirm delete file (confirmed via ConfirmationDialog)
const showDeleteFileConfirm = ref(false)
const confirmDeleteFile = (file: FileModel): void => {
  fileToDelete.value = file
  showDeleteFileConfirm.value = true
}
const executeDeleteFile = async (): Promise<void> => {
  const file = fileToDelete.value
  showDeleteFileConfirm.value = false
  if (!file) return
  await deleteFile(file)
  fileToDelete.value = null
}

// Delete file
const deleteFile = async (file: FileModel): Promise<void> => {
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
const openImportConfigModal = (file: FileModel): void => {
  configuringFile.value = file
  showImportConfigModal.value = true
}

// Get file by ID (for panel display)
const getFileById = (id: number): FileWithTasks | undefined => {
  return files.value.find((f) => f.id === id)
}

// Handle view preprocessing history
const handleViewHistory = (file: FileWithTasks): void => {
  historyFile.value = file
  showHistoryPanel.value = true
}

// Process file and close history panel
const processFileAndClose = (file: FileWithTasks): void => {
  quickProcessFile(file)
  showHistoryPanel.value = false
}

// Process file and close panel (for footer button)
const processFileAndClosePanel = (file: FileWithTasks): void => {
  quickProcessFile(file)
  showHistoryPanel.value = false
}

// Retry failed files for a task
const retryFailedFiles = async (taskId: number): Promise<void> => {
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

// Cancel preprocessing task (confirmed via ConfirmationDialog)
const showCancelTaskConfirm = ref(false)
const pendingCancelTask = ref<PreprocessingTask | null>(null)
const cancelPreprocessingTask = (task: PreprocessingTask): void => {
  pendingCancelTask.value = task
  showCancelTaskConfirm.value = true
}
const executeCancelTask = async (): Promise<void> => {
  const task = pendingCancelTask.value
  showCancelTaskConfirm.value = false
  pendingCancelTask.value = null
  if (!task) return
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
const previewFile = (file: FileModel): void => {
  previewingFile.value = file
  showFilePreview.value = true
}

// Download file
const downloadFile = async (file: FileModel): Promise<void> => {
  try {
    const response = await filesApi.getContent(props.projectId, file.id)
    downloadBlob(response.data, file.file_name || 'download')
  } catch {
    toast.error(`Failed to download ${file.file_name}`)
  }
}

// Quick process single file
const quickProcessFile = (file: FileModel): void => {
  selectedFiles.value = [file.id]
  openProcessingPanel()
}

// Open processing panel
const openProcessingPanel = (): void => {
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
const startProcessing = async (payload: PreprocessingTaskCreate): Promise<void> => {
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

    duplicatePreview.value = previewResponse.data as PreprocessingDuplicatePreview

    // Only show modal if there are same-config duplicates (not just different OCR configs)
    // Also show if PDFs with embedded text exist (to inform user OCR won't affect result)
    const previewData = duplicatePreview.value
    const hasSameConfigDuplicates =
      !!previewData.same_config_duplicates && previewData.same_config_duplicates.length > 0
    const hasPdfsWithEmbeddedText =
      !!previewData.pdfs_with_embedded_text && previewData.pdfs_with_embedded_text.length > 0

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
    const errorMsg = extractErrorMessage(err, 'Failed to check for existing documents')
    toast.error(errorMsg)
    pendingProcessingSettings.value = null
  }
}

// Cancel duplicate preview and close modal
const cancelDuplicatePreview = (): void => {
  showDuplicatePreviewModal.value = false
  duplicatePreview.value = null
  pendingProcessingSettings.value = null
  isSubmitting.value = false
}

// User confirmed the duplicate preview modal — proceed with the skipExisting choice.
const onDuplicateConfirm = ({ skipExisting }: { skipExisting: boolean }): void => {
  confirmAndStartProcessing(skipExisting)
}

// Confirm and start processing (called after user approves duplicate preview)
const confirmAndStartProcessing = async (skipExisting = false): Promise<void> => {
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
    const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    let errorMsg = 'Failed to start preprocessing'

    // Handle structured error response
    if (detail && typeof detail === 'object') {
      const d = detail as { code?: string; message?: string }
      if (d.code === 'csv_xlsx_needs_config') {
        errorMsg = d.message || 'CSV/XLSX files need import configuration'
      } else if (d.code === 'files_already_being_processed') {
        errorMsg = d.message || 'One or more files are already being processed'
      } else if (d.code === 'no_ocr_engine_enabled') {
        errorMsg = d.message || 'No OCR engine enabled'
      } else if (d.message) {
        errorMsg = d.message
      }
    } else if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0] as { msg?: string }
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
const uploadFiles = async (fileList: File[]): Promise<void> => {
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
const fetchOcrSettings = async (): Promise<void> => {
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
const handleExpandTask = (event: Event): void => {
  const customEvent = event as CustomEvent<{ id?: string | number }>
  const taskId = customEvent.detail?.id
  if (!taskId) return

  // Try to find and expand the task, retrying a few times if files aren't loaded yet
  const tryExpandTask = (attempts = 0): void => {
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
  document.addEventListener('expand-preprocessing-task', handleExpandTask as EventListener)
})

onUnmounted(() => {
  stopWebSocket()
  document.removeEventListener('expand-preprocessing-task', handleExpandTask as EventListener)
})
</script>
