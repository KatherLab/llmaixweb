<template>
  <div :class="t.wrapper">
    <!-- Table -->
    <div class="overflow-x-auto">
      <!-- "Select All" banner - shown when files are selected and there are more pages -->
      <div
        v-if="selectedFiles.length > 0 && pagination.total > pagination.page_size"
        class="bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 px-4 py-2"
      >
        <div class="flex items-center justify-between">
          <p class="text-sm text-blue-800 dark:text-blue-300">
            <span class="font-medium">{{ selectedFiles.length }}</span>
            file{{ selectedFiles.length !== 1 ? 's' : '' }} selected
            <span
              v-if="selectedFiles.length < pagination.total"
              class="text-blue-600 dark:text-blue-400"
            >
              out of {{ pagination.total }} total
            </span>
          </p>
          <BaseButton
            v-if="selectedFiles.length < pagination.total"
            variant="ghost"
            size="sm"
            class="font-medium underline"
            @click="$emit('select-all-files')"
          >
            Select all {{ pagination.total }} files in project
          </BaseButton>
          <BaseButton
            v-if="selectedFiles.length === pagination.total"
            variant="ghost"
            size="sm"
            @click="$emit('clear-selection')"
          >
            Clear selection
          </BaseButton>
        </div>
      </div>

      <table :class="t.table">
        <thead :class="t.thead">
          <tr>
            <th scope="col" :class="[t.th, 'text-left']">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected"
                class="h-4 w-4 text-blue-600 border-slate-300 dark:border-slate-600 rounded focus:ring-blue-500"
                @change="$emit('toggle-all')"
              />
            </th>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              :class="[
                t.th,
                'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors select-none',
              ]"
              @click="$emit('sort', column.key)"
            >
              <div class="flex items-center gap-1">
                {{ column.label }}
                <ChevronDown
                  v-if="sortBy === column.key"
                  :class="['w-4 h-4 transition-transform', sortOrder === 'asc' ? 'rotate-180' : '']"
                />
              </div>
            </th>
            <th scope="col" :class="[t.th, 'text-right']">Actions</th>
          </tr>
        </thead>
        <tbody :class="t.tbody">
          <tr
            v-for="file in files"
            :key="file.id"
            :class="[
              'hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors',
              selectedFiles.includes(file.id) ? 'bg-blue-50 dark:bg-slate-800' : '',
            ]"
          >
            <td class="px-4 py-3 whitespace-nowrap">
              <input
                type="checkbox"
                :checked="selectedFiles.includes(file.id)"
                class="h-4 w-4 text-blue-600 border-slate-300 dark:border-slate-600 rounded focus:ring-blue-500"
                @click.stop="$emit('toggle-selection', file.id)"
              />
            </td>
            <td class="px-4 py-3">
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
                      {{
                        file.preprocessing_strategy === 'row_by_row' ? 'Row-by-Row' : 'Full Table'
                      }}
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
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <StatusBadge color="gray" class="font-medium">
                {{ getFileTypeLabel(file.file_type) }}
              </StatusBadge>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              {{ formatFileSize(file.file_size, 'Unknown') }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
              <span :title="formatDateFull(file.created_at)">{{
                formatDateSmart(file.created_at)
              }}</span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
              <StatusBadge :status="file._status || 'not_preprocessed'" class="font-medium">
                {{ getStatusLabel(file) }}
              </StatusBadge>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-right">
              <div class="flex items-center justify-end gap-1">
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
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <EmptyState v-if="files.length === 0" title="No files found">
      <template #icon>
        <FilePlus class="h-12 w-12 mx-auto text-slate-300 dark:text-slate-600" aria-hidden="true" />
      </template>
    </EmptyState>

    <!-- Pagination -->
    <PaginationControls
      :model-value="pagination.page"
      :total-pages="pagination.total_pages"
      :visible-pages="visiblePages"
      :total-items="pagination.total"
      :page-size="pagination.page_size"
      :show-page-size-selector="true"
      :page-size-options="[25, 50, 100, 250]"
      item-label="files"
      @update:model-value="$emit('page-change', $event)"
      @update:page-size="$emit('page-size-change', $event)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ChevronDown, Clock, CloudDownload, Eye, FilePlus, Trash2 } from '@lucide/vue'
import FileIcon from '@/components/common/FileIcon.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import { formatFileSize, formatDateSmart, formatDateFull } from '@/utils/formatters'
import { useTableClasses } from '@/composables/useTableClasses'
import { computeVisiblePages } from '@/composables/usePagination'

const t = useTableClasses()

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

const emit = defineEmits([
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
const someSelected = computed(
  () => props.selectedFiles.length > 0 && props.selectedFiles.length < props.files.length,
)

const visiblePages = computed(() =>
  computeVisiblePages(props.pagination.page, props.pagination.total_pages),
)

const columns = [
  { key: 'file_name', label: 'File' },
  { key: 'file_type', label: 'Type' },
  { key: 'file_size', label: 'Size' },
  { key: 'created_at', label: 'Uploaded' },
  { key: 'status', label: 'Status' },
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
