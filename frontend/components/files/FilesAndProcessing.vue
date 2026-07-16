<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <PageHeader
      title="Files"
      subtitle="Upload files and run OCR preprocessing"
      :sticky="false"
      class="mb-6"
    >
      <template #actions>
        <BaseButton variant="secondary" @click="showUploadModal = true">
          <Upload class="w-5 h-5 text-content-muted" />
          Upload Files
        </BaseButton>
      </template>
    </PageHeader>

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
    <Callout
      v-if="files.length > 0 && selectedFiles.length === 0 && !hasActivePreprocessingTasks"
      variant="info"
      class="flex items-center gap-2"
    >
      <p class="text-sm">
        <strong>Next step:</strong> Select files from the table below, then click
        <span class="font-semibold">Configure Preprocessing</span> to extract text from your
        documents.
      </p>
      <BaseButton
        variant="ghost"
        size="sm"
        class="ml-auto font-medium"
        :disabled="isSelectingAll"
        @click="selectAllFiles"
      >
        {{ isSelectingAll ? 'Selecting…' : `Select all ${pagination.total}` }}
      </BaseButton>
    </Callout>

    <!-- Global preprocessing progress banner: aggregates every active task so
         a user running a 50-file batch can see progress (and cancel) without
         opening the per-file history panel. -->
    <div
      v-if="activePreprocessingSummary"
      class="mb-4 rounded-card border border-default bg-surface-muted p-4"
    >
      <div class="flex items-center gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-medium text-content">
              Preprocessing
              <span class="text-content-muted font-normal">
                {{ activePreprocessingSummary.processed }} of
                {{ activePreprocessingSummary.total }} files
                <span
                  v-if="activePreprocessingSummary.failed > 0"
                  class="text-red-600 dark:text-red-400"
                >
                  · {{ activePreprocessingSummary.failed }} failed
                </span>
              </span>
            </p>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-xs text-content-subtle tabular-nums"
                >{{ activePreprocessingSummary.percent }}%</span
              >
              <BaseButton variant="ghost" size="sm" @click="viewActiveTaskDetails">
                View details
              </BaseButton>
              <BaseButton
                v-if="activePreprocessingSummary.cancelableTask"
                variant="ghost"
                size="sm"
                class="text-red-600 dark:text-red-400 hover:text-red-700"
                @click="cancelPreprocessingTask(activePreprocessingSummary.cancelableTask)"
              >
                Cancel
              </BaseButton>
            </div>
          </div>
          <div class="mt-2 h-1.5 w-full bg-surface-sunken rounded-full overflow-hidden">
            <div
              class="h-full bg-primary transition-all duration-500"
              :style="{ width: activePreprocessingSummary.percent + '%' }"
            ></div>
          </div>
          <p v-if="activePreprocessingSummary.etaLabel" class="mt-1.5 text-xs text-content-subtle">
            {{ activePreprocessingSummary.etaLabel }}
          </p>
        </div>
      </div>
    </div>

    <!-- Loading Indicator -->
    <SkeletonTable v-if="isLoading" :columns="5" :rows="8" />

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
      @navigate-group="navigateToGroup"
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
        <Search class="h-16 w-16 mx-auto text-content-subtle" aria-hidden="true" />
      </template>
    </EmptyState>

    <!-- Floating Batch Toolbar -->
    <BatchActionBar :count="selectedFiles.length" count-label="file" @clear="selectedFiles = []">
      <template #warning>
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
      </template>

      <BaseButton :disabled="unconfiguredCsvXlsxFiles.length > 0" @click="openProcessingPanel">
        <Settings v-if="unconfiguredCsvXlsxFiles.length === 0" class="w-4 h-4" />
        <AlertTriangle v-else class="w-4 h-4" />
        {{
          unconfiguredCsvXlsxFiles.length > 0 ? 'Configure Files First' : 'Configure Preprocessing'
        }}
      </BaseButton>
      <BaseButton variant="danger" @click="confirmDeleteSelected">
        <Trash2 class="w-4 h-4" />
        Delete
      </BaseButton>
    </BatchActionBar>

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
      :progress="uploadProgress"
      @close="onUploadModalClose"
      @files="uploadFiles"
    />

    <!-- File Preview Modal -->
    <FilePreviewModal
      :open="showFilePreview"
      :file="previewingFile"
      :files="displayFiles"
      :project-id="projectId"
      @close="showFilePreview = false"
      @navigate="onPreviewNavigate"
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
      :submitting="isStartingProcessing"
      @confirm="onDuplicateConfirm"
      @cancel="cancelDuplicatePreview"
    />

    <!-- Delete file (with optional cascade + impact preview) -->
    <BatchActionsModal
      :open="showDeleteFileModal"
      action="delete"
      mode="files"
      :documents="filesToDeleteIds"
      :project-id="projectId"
      @deleted="onFilesDeleted"
      @close="closeDeleteFileModal"
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
import { AlertTriangle, Search, Settings, Trash2, Upload } from '@lucide/vue'
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
import SkeletonTable from '@/components/common/SkeletonTable.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import BatchActionBar from '@/components/common/BatchActionBar.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import BatchActionsModal from '@/components/documents/BatchActionsModal.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
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
const filesToDeleteIds = ref<number[]>([])
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
const isSelectingAll = ref(false) // fetching all file ids across pages

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
// Re-entrancy guard for the "start preprocessing" action specifically. Separate
// from isSubmitting (which is already true on the no-duplicate path when
// confirmAndStartProcessing runs), so a double-click on the duplicate-modal
// confirm can't dispatch two identical preprocessing tasks.
const isStartingProcessing = ref(false)
// Re-entrancy guard for the batch upload loop (see uploadFiles).
const isUploading = ref(false)
// Live progress for the upload modal so large batches aren't a silent spinner.
interface UploadProgressState {
  total: number
  completed: number // finished (succeeded or failed)
  succeeded: number
  currentIndex: number // 1-based index of the file being uploaded
  currentName: string
  currentPercent: number // 0-100 for the in-flight file
  failures: { name: string; message: string }[]
  done: boolean // whole batch finished (modal shows a summary)
}
const uploadProgress = ref<UploadProgressState | null>(null)

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

  // Derive this file's status from its OWN per-file subtask, not the parent
  // task's aggregate status. A parent task can be FAILED (e.g. finalized by the
  // orphan sweeper after a restart) while most of its files completed and
  // produced documents — using the parent status would wrongly show every file
  // in the batch as "failed". Fall back to the parent status only when the
  // per-file entry is missing.
  const fileTask = latestTask.file_tasks?.find((ft) => ft.file_id === file.id)
  const status = String((fileTask?.status ?? latestTask.status) || '').toLowerCase()

  if (['pending', 'processing', 'in_progress'].includes(status)) {
    return 'processing'
  } else if (status === 'completed') {
    return 'completed'
  } else {
    return 'failed'
  }
}

// Fetch files with preprocessing tasks (paginated)
// Append the currently-active list filters to a params object. Shared by
// fetchFiles and selectAllFiles so "select all across pages" selects exactly
// the filtered set that's shown (not a broader search/status-only set).
const appendFileFilters = (params: URLSearchParams): void => {
  if (searchQuery.value) params.append('search', searchQuery.value)
  if (filterStatus.value) params.append('status', filterStatus.value)
  if (filterFileType.value) params.append('file_type', filterFileType.value)
  if (filterDateRange.value) {
    const { date_from, date_to } = getDateBounds(filterDateRange.value)
    if (date_from) params.append('date_from', date_from)
    if (date_to) params.append('date_to', date_to)
  }
}

const fetchFiles = async (options: { forceRefreshTasks?: boolean } = {}): Promise<void> => {
  const { forceRefreshTasks = false } = options

  try {
    const params = new URLSearchParams({
      page: String(pagination.value.page),
      page_size: String(pagination.value.page_size),
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    })

    appendFileFilters(params)

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

// Toggle select all for the CURRENT page, by id membership (not length). Using
// length equality wrongly wiped a cross-page selection whenever its size didn't
// match the current page's row count. This adds/removes only the current page's
// ids, preserving any selection made on other pages.
const toggleSelectAll = (): void => {
  const pageIds = files.value.map((f) => f.id)
  const allOnPageSelected =
    pageIds.length > 0 && pageIds.every((id) => selectedFiles.value.includes(id))
  if (allOnPageSelected) {
    const pageSet = new Set(pageIds)
    selectedFiles.value = selectedFiles.value.filter((id) => !pageSet.has(id))
  } else {
    const merged = new Set(selectedFiles.value)
    pageIds.forEach((id) => merged.add(id))
    selectedFiles.value = [...merged]
  }
  selectAllMode.value = false
}

// Select ALL files across all pages (for 50k+ files)
const selectAllFiles = async (): Promise<void> => {
  if (isSelectingAll.value) return
  selectAllMode.value = true
  isSelectingAll.value = true
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

      appendFileFilters(params)

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
  } finally {
    isSelectingAll.value = false
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

// Navigate to the auto-generated document group (row-by-row CSV/XLSX runs)
const navigateToGroup = (documentSetId: number): void => {
  showHistoryPanel.value = false
  emit('files-changed')
  router.push({
    path: `/projects/${props.projectId}`,
    query: { tab: 'documents', group: documentSetId },
  })
}

// Delete file — handled by BatchActionsModal (mode='files'), which shows the
// cascade checkbox + impact preview and reports success/failure via toasts.
const showDeleteFileModal = ref(false)
const confirmDeleteFile = (file: FileModel): void => {
  filesToDeleteIds.value = [file.id]
  showDeleteFileModal.value = true
}
// Batch delete: every currently selected file (works across pages via
// selectAllFiles). Reuses the same cascade/impact-preview modal as single delete.
const confirmDeleteSelected = (): void => {
  if (!selectedFiles.value.length) return
  filesToDeleteIds.value = [...selectedFiles.value]
  showDeleteFileModal.value = true
}
// Prune successfully deleted ids from the selection so batch actions can't
// operate on a file that no longer exists.
const onFilesDeleted = (ids: number[]): void => {
  selectedFiles.value = selectedFiles.value.filter((id) => !ids.includes(id))
}
// Modal closed (after any delete attempts) — refresh the file list.
const closeDeleteFileModal = async (): Promise<void> => {
  showDeleteFileModal.value = false
  filesToDeleteIds.value = []
  invalidateTaskCache()
  await fetchFiles({ forceRefreshTasks: true })
  emit('files-changed')
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

// Navigate between files from within the preview modal (prev/next / keyboard).
const onPreviewNavigate = (file: FileModel): void => {
  previewingFile.value = file
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

// Aggregate view of all currently-active preprocessing tasks for the global
// progress banner. Derived from `files` (reactive, kept fresh by the WS
// subscription) rather than the cached task list, so the bar updates live.
interface ActivePreprocessingSummary {
  total: number
  processed: number
  failed: number
  percent: number
  etaLabel: string
  cancelableTask: PreprocessingTask | null
}

const activePreprocessingSummary = computed<ActivePreprocessingSummary | null>(() => {
  const activeStatuses = ['pending', 'processing', 'in_progress']
  const seenTaskIds = new Set<number>()
  let total = 0
  let processed = 0
  let failed = 0
  let etaSeconds = 0
  let cancelableTask: PreprocessingTask | null = null

  for (const file of files.value) {
    for (const task of file.preprocessing_tasks || []) {
      if (!activeStatuses.includes(String(task.status || '').toLowerCase())) continue
      if (seenTaskIds.has(task.id)) continue
      seenTaskIds.add(task.id)
      // Prefer runtime meta totals (set by the pipeline); fall back to the
      // top-level counts which are populated for completed/in-flight tasks.
      const meta = task.meta
      const tTotal = meta?.total_files ?? task.total_files ?? 0
      const tProcessed = meta?.completed_files ?? task.processed_files ?? 0
      const tFailed = meta?.failed_files ?? task.failed_files ?? 0
      total += tTotal
      processed += tProcessed
      failed += tFailed
      if (meta?.eta_seconds && meta.eta_seconds > etaSeconds) etaSeconds = meta.eta_seconds
      // Any non-pending active task can be cancelled.
      if (!cancelableTask && String(task.status || '').toLowerCase() !== 'pending') {
        cancelableTask = task
      }
    }
  }

  if (total === 0 && seenTaskIds.size === 0) return null
  // When only pending (no totals yet), show an indeterminate-ish state.
  if (total === 0) {
    return {
      total: 0,
      processed: 0,
      failed: 0,
      percent: 0,
      etaLabel: 'Starting…',
      cancelableTask,
    }
  }
  const percent = Math.min(100, Math.round((processed / total) * 100))
  const etaLabel = etaSeconds > 0 ? `≈ ${formatDuration(etaSeconds)} remaining` : ''
  return { total, processed, failed, percent, etaLabel, cancelableTask }
})

// Format seconds into a compact human duration (e.g. "4m 30s", "1h 5m").
function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  if (m < 60) return rem ? `${m}m ${rem}s` : `${m}m`
  const h = Math.floor(m / 60)
  const mm = m % 60
  return mm ? `${h}h ${mm}m` : `${h}h`
}

// Open the history panel for the first file that has an active task.
const viewActiveTaskDetails = (): void => {
  const activeStatuses = ['pending', 'processing', 'in_progress']
  const fileWithActive = files.value.find((f) =>
    f.preprocessing_tasks?.some((t) =>
      activeStatuses.includes(String(t.status || '').toLowerCase()),
    ),
  )
  if (fileWithActive) {
    historyFile.value = fileWithActive
    showHistoryPanel.value = true
  }
}

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
  if (isStartingProcessing.value) return // guard against double-click
  isStartingProcessing.value = true

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
    isStartingProcessing.value = false
  }
}

// Upload files
const uploadFiles = async (fileList: File[]): Promise<void> => {
  if (!fileList.length) return
  // Re-entrancy guard: a second drop while an upload loop is running would
  // otherwise run concurrently, and whichever finishes first would close the
  // modal / reset state out from under the other.
  if (isUploading.value) return
  isUploading.value = true
  isSubmitting.value = true

  const failures: { name: string; message: string }[] = []
  const progress: UploadProgressState = {
    total: fileList.length,
    completed: 0,
    succeeded: 0,
    currentIndex: 0,
    currentName: '',
    currentPercent: 0,
    failures,
    done: false,
  }
  uploadProgress.value = progress

  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i]
    progress.currentIndex = i + 1
    progress.currentName = file.name
    progress.currentPercent = 0
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

      await filesApi.upload(props.projectId, formData, (e) => {
        progress.currentPercent = e.total ? Math.round((e.loaded / e.total) * 100) : 0
      })
      progress.succeeded++
    } catch (err) {
      console.error(`Failed to upload ${file.name}:`, err)
      failures.push({ name: file.name, message: extractErrorMessage(err, 'Upload failed') })
    } finally {
      progress.completed++
    }
  }

  progress.currentPercent = 100
  progress.done = true

  const succeeded = progress.succeeded
  // One summary toast per batch instead of one per file (50 files ≠ 50 toasts).
  if (succeeded > 0) {
    toast.success(`Uploaded ${succeeded} file${succeeded === 1 ? '' : 's'}`)
  }
  if (failures.length > 0) {
    const first = failures[0]
    const more = failures.length > 1 ? ` (+${failures.length - 1} more)` : ''
    toast.error(
      `Failed to upload ${failures.length} file${failures.length === 1 ? '' : 's'}: ` +
        `${first.name} — ${first.message}${more}`,
    )
  }

  isSubmitting.value = false
  isUploading.value = false
  // Keep the modal open on the summary screen when some files failed so the
  // user can see what went wrong; auto-close on a fully successful batch.
  if (failures.length === 0) {
    showUploadModal.value = false
    uploadProgress.value = null
  }
  // Invalidate task cache when files change
  invalidateTaskCache()
  await fetchFiles({ forceRefreshTasks: true })
  emit('files-changed')
}

// Reset upload state when the modal is dismissed (from the summary screen or
// otherwise). Guarded so it can't clear state mid-upload.
const onUploadModalClose = (): void => {
  if (isUploading.value) return
  showUploadModal.value = false
  uploadProgress.value = null
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
