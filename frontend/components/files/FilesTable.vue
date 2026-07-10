<template>
  <DataTable
    :columns="columns"
    :items="files"
    row-key="id"
    selectable
    :selected-keys="selectedFiles"
    :all-selected="allSelected"
    :total-selected="selectedFiles.length"
    :sort-by="sortBy"
    :sort-order="sortOrder"
    :pagination="pagination"
    :page-size-options="[25, 50, 100, 250]"
    item-label="files"
    empty-title="No files found"
    @toggle-selection="onToggleSelection"
    @toggle-all="$emit('toggle-all')"
    @select-all="$emit('select-all-files')"
    @clear-selection="$emit('clear-selection')"
    @sort="$emit('sort', $event)"
    @page-change="$emit('page-change', $event)"
    @page-size-change="$emit('page-size-change', $event)"
  >
    <template #cell-file_name="{ row: file }">
      <div class="flex items-center gap-3">
        <FileIcon :file-type="file.file_type" :size="32" />
        <div class="min-w-0">
          <p
            class="text-sm font-medium text-content truncate max-w-xs"
            :title="file.file_name ?? undefined"
          >
            {{ file.file_name }}
          </p>
          <div class="flex items-center gap-2 mt-0.5">
            <span
              v-if="isCSVXLSX(file) && !file.preprocessing_strategy"
              class="inline-flex items-center px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 text-xs font-medium"
            >
              Needs Import Config
            </span>
            <span
              v-else-if="isCSVXLSX(file) && file.preprocessing_strategy"
              class="inline-flex items-center px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 text-xs font-medium"
            >
              {{ file.preprocessing_strategy === 'row_by_row' ? 'Row-by-Row' : 'Full Table' }}
            </span>
            <BaseButton
              v-if="isCSVXLSX(file)"
              variant="ghost"
              size="sm"
              class="text-xs underline"
              @click.stop="onConfigureImport(file)"
            >
              {{ file.preprocessing_strategy ? 'Edit' : 'Configure' }}
            </BaseButton>
          </div>
        </div>
      </div>
    </template>

    <template #cell-file_type="{ row: file }">
      <StatusBadge color="gray" class="font-medium">
        {{ getFileTypeLabel(file.file_type) }}
      </StatusBadge>
    </template>

    <template #cell-file_size="{ row: file }">
      <span class="text-sm text-content-muted">
        {{ formatFileSize(file.file_size, 'Unknown') }}
      </span>
    </template>

    <template #cell-created_at="{ row: file }">
      <span class="text-sm text-content-muted" :title="formatDateFull(file.created_at)">
        {{ formatDateSmart(file.created_at) }}
      </span>
    </template>

    <template #cell-status="{ row: file }">
      <StatusBadge :status="file._status || 'not_preprocessed'" class="font-medium">
        {{ getStatusLabel(file) }}
      </StatusBadge>
    </template>

    <template #row-actions="{ row: file }">
      <BaseButton
        variant="icon"
        tone="purple"
        title="Preprocessing History"
        aria-label="Preprocessing History"
        @click.stop="onViewHistory(file)"
      >
        <Clock class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="blue"
        title="Preview"
        aria-label="Preview"
        @click.stop="onPreview(file)"
      >
        <Eye class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="green"
        title="Download"
        aria-label="Download"
        @click.stop="onDownload(file)"
      >
        <CloudDownload class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="red"
        title="Delete"
        aria-label="Delete"
        @click.stop="onDelete(file)"
      >
        <Trash2 class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
    </template>

    <template #empty-icon>
      <FilePlus class="h-12 w-12 mx-auto text-content-subtle" aria-hidden="true" />
    </template>
  </DataTable>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock, CloudDownload, Eye, FilePlus, Trash2 } from '@lucide/vue'
import FileIcon from '@/components/common/FileIcon.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import DataTable from '@/components/common/DataTable.vue'
import { formatFileSize, formatDateSmart, formatDateFull } from '@/utils/formatters'
import type { FileWithTasks } from '@/composables/usePreprocessingUpdates'

/**
 * Loose row shape used by the template helpers. DataTable is a generic
 * component (`T extends Record<string, any>`) and vue-tsc types its slot
 * `row` as the constraint rather than the inferred `T`, so the helpers accept
 * this minimal structural type (which `Record<string, any>` is assignable to)
 * instead of `FileWithTasks`.
 */
interface FileRow {
  file_type?: string | null
  file_name?: string | null
  file_size?: number | null
  created_at?: string
  preprocessing_strategy?: string | null
  _status?: string
}

interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
  start: number
  end: number
}

interface Props {
  files: FileWithTasks[]
  selectedFiles: number[]
  sortBy?: string
  sortOrder?: string
  pagination?: Pagination
}

const props = withDefaults(defineProps<Props>(), {
  sortBy: 'created_at',
  sortOrder: 'desc',
  pagination: () => ({ page: 1, page_size: 25, total: 0, total_pages: 0, start: 0, end: 0 }),
})

const emit = defineEmits<{
  'toggle-selection': [fileId: number]
  'toggle-all': []
  preview: [file: FileWithTasks]
  download: [file: FileWithTasks]
  delete: [file: FileWithTasks]
  'configure-import': [file: FileWithTasks]
  'page-change': [page: number]
  'page-size-change': [size: number]
  sort: [field: string]
  'view-history': [file: FileWithTasks]
  'select-all-files': []
  'clear-selection': []
}>()

// Bridge handlers: DataTable emits loose slot/row types (its generic `T` is
// widened to `Record<string, any>` by vue-tsc), so we cast back to the concrete
// types our emits expect. Runtime values are always FileWithTasks / number.
const onToggleSelection = (key: string | number): void => {
  emit('toggle-selection', Number(key))
}
const onPreview = (file: FileRow): void => {
  emit('preview', file as unknown as FileWithTasks)
}
const onDownload = (file: FileRow): void => {
  emit('download', file as unknown as FileWithTasks)
}
const onDelete = (file: FileRow): void => {
  emit('delete', file as unknown as FileWithTasks)
}
const onConfigureImport = (file: FileRow): void => {
  emit('configure-import', file as unknown as FileWithTasks)
}
const onViewHistory = (file: FileRow): void => {
  emit('view-history', file as unknown as FileWithTasks)
}

// "All selected" means every file on THIS page is selected (by id membership),
// not that the selection count equals the page size — otherwise a cross-page
// selection of the same size would falsely render the header as fully checked.
const allSelected = computed(() => {
  if (props.files.length === 0) return false
  const selected = new Set(props.selectedFiles)
  return props.files.every((f) => selected.has(f.id))
})

const columns = [
  { key: 'file_name', label: 'File', sortable: true },
  { key: 'file_type', label: 'Type', sortable: true },
  { key: 'file_size', label: 'Size', sortable: true },
  { key: 'created_at', label: 'Uploaded', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
]

function isCSVXLSX(file: FileRow): boolean {
  if (!file || !file.file_type) return false
  return (
    file.file_type === 'text/csv' ||
    file.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    file.file_type === 'application/vnd.ms-excel'
  )
}

function getFileTypeLabel(mimeType: string | null | undefined): string {
  const typeMap: Record<string, string> = {
    'application/pdf': 'PDF',
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'text/plain': 'Text',
    'text/csv': 'CSV',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
    'application/vnd.ms-excel': 'Excel',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
  }
  return (mimeType && typeMap[mimeType]) || 'File'
}

function getStatusLabel(file: FileRow): string {
  const status = file._status || 'not_preprocessed'
  const labelMap: Record<string, string> = {
    completed: 'Processed',
    processing: 'Processing',
    failed: 'Failed',
    not_preprocessed: 'Not preprocessed',
  }
  return labelMap[status] || 'Not preprocessed'
}
</script>
