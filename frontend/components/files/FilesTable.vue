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
    @toggle-selection="$emit('toggle-selection', $event)"
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
            class="text-sm font-medium text-slate-900 dark:text-white truncate max-w-xs"
            :title="file.file_name"
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
              @click.stop="$emit('configure-import', file)"
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
      <span class="text-sm text-slate-600 dark:text-slate-400">
        {{ formatFileSize(file.file_size, 'Unknown') }}
      </span>
    </template>

    <template #cell-created_at="{ row: file }">
      <span
        class="text-sm text-slate-600 dark:text-slate-400"
        :title="formatDateFull(file.created_at)"
      >
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
        @click.stop="$emit('view-history', file)"
      >
        <Clock class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="blue"
        title="Preview"
        aria-label="Preview"
        @click.stop="$emit('preview', file)"
      >
        <Eye class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="green"
        title="Download"
        aria-label="Download"
        @click.stop="$emit('download', file)"
      >
        <CloudDownload class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="red"
        title="Delete"
        aria-label="Delete"
        @click.stop="$emit('delete', file)"
      >
        <Trash2 class="w-4 h-4" aria-hidden="true" />
      </BaseButton>
    </template>

    <template #empty-icon>
      <FilePlus class="h-12 w-12 mx-auto text-slate-300 dark:text-slate-600" aria-hidden="true" />
    </template>
  </DataTable>
</template>

<script setup>
import { computed } from 'vue'
import { Clock, CloudDownload, Eye, FilePlus, Trash2 } from '@lucide/vue'
import FileIcon from '@/components/common/FileIcon.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import DataTable from '@/components/common/DataTable.vue'
import { formatFileSize, formatDateSmart, formatDateFull } from '@/utils/formatters'

const props = defineProps({
  files: { type: Array, required: true },
  selectedFiles: { type: Array, required: true },
  sortBy: { type: String, default: 'created_at' },
  sortOrder: { type: String, default: 'desc' },
  pagination: {
    type: Object,
    default: () => ({ page: 1, page_size: 25, total: 0, total_pages: 0, start: 0, end: 0 }),
  },
})

defineEmits([
  'toggle-selection',
  'toggle-all',
  'preview',
  'download',
  'delete',
  'configure-import',
  'page-change',
  'page-size-change',
  'sort',
  'view-history',
  'select-all-files',
  'clear-selection',
])

const allSelected = computed(
  () => props.files.length > 0 && props.selectedFiles.length === props.files.length,
)

const columns = [
  { key: 'file_name', label: 'File', sortable: true },
  { key: 'file_type', label: 'Type', sortable: true },
  { key: 'file_size', label: 'Size', sortable: true },
  { key: 'created_at', label: 'Uploaded', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
]

function isCSVXLSX(file) {
  if (!file || !file.file_type) return false
  return (
    file.file_type === 'text/csv' ||
    file.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    file.file_type === 'application/vnd.ms-excel'
  )
}

function getFileTypeLabel(mimeType) {
  const typeMap = {
    'application/pdf': 'PDF',
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'text/plain': 'Text',
    'text/csv': 'CSV',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
    'application/vnd.ms-excel': 'Excel',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
  }
  return typeMap[mimeType] || 'File'
}

function getStatusLabel(file) {
  const status = file._status || 'not_preprocessed'
  const labelMap = {
    completed: 'Processed',
    processing: 'Processing',
    failed: 'Failed',
    not_preprocessed: 'Not preprocessed',
  }
  return labelMap[status] || 'Not preprocessed'
}
</script>
