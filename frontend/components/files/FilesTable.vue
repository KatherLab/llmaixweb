<template>
  <div
    class="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden"
  >
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

      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50 dark:bg-slate-800">
          <tr>
            <th scope="col" class="px-4 py-3 text-left">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected"
                class="h-4 w-4 text-blue-600 border-gray-300 dark:border-slate-600 rounded focus:ring-blue-500"
                @change="$emit('toggle-all')"
              />
            </th>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              class="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors select-none"
              @click="$emit('sort', column.key)"
            >
              <div class="flex items-center gap-1">
                {{ column.label }}
                <svg
                  v-if="sortBy === column.key"
                  :class="['w-4 h-4 transition-transform', sortOrder === 'asc' ? 'rotate-180' : '']"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </div>
            </th>
            <th
              scope="col"
              class="px-4 py-3 text-right text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-slate-900 divide-y divide-gray-100 dark:divide-slate-700">
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
                class="h-4 w-4 text-blue-600 border-gray-300 dark:border-slate-600 rounded focus:ring-blue-500"
                @click.stop="$emit('toggle-selection', file.id)"
              />
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-3">
                <FileIcon :file-type="file.file_type" :size="32" />
                <div class="min-w-0">
                  <p
                    class="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs"
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
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
              {{ formatFileSize(file.file_size, 'Unknown') }}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
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
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </BaseButton>
                <BaseButton
                  variant="icon"
                  tone="blue"
                  title="Preview"
                  aria-label="Preview"
                  @click.stop="$emit('preview', file)"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    />
                  </svg>
                </BaseButton>
                <BaseButton
                  variant="icon"
                  tone="green"
                  title="Download"
                  aria-label="Download"
                  @click.stop="$emit('download', file)"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                    />
                  </svg>
                </BaseButton>
                <BaseButton
                  variant="icon"
                  tone="red"
                  title="Delete"
                  aria-label="Delete"
                  @click.stop="$emit('delete', file)"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
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
        <svg
          class="h-12 w-12 mx-auto text-gray-300 dark:text-slate-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </template>
    </EmptyState>

    <!-- Pagination -->
    <div
      v-if="pagination.total > 0"
      class="border-t border-gray-200 dark:border-slate-700 px-4 py-3 bg-gray-50 dark:bg-slate-800"
    >
      <div class="flex items-center justify-between">
        <div class="text-sm text-gray-600 dark:text-gray-400">
          Showing <span class="font-medium">{{ pagination.start }}</span> to
          <span class="font-medium">{{ pagination.end }}</span> of
          <span class="font-medium">{{ pagination.total }}</span> files
        </div>
        <div class="flex items-center gap-2">
          <label class="text-sm text-gray-600 dark:text-gray-400">
            Rows per page:
            <select
              v-model="localPageSize"
              class="ml-1 border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 rounded px-2 py-1 text-sm text-gray-900 dark:text-white focus:ring-blue-500 focus:border-blue-500"
              @change="$emit('page-size-change', $event.target.value)"
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="250">250</option>
            </select>
          </label>
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="pagination.page === 1"
            @click="$emit('page-change', pagination.page - 1)"
          >
            Previous
          </BaseButton>
          <span class="text-sm text-gray-600 dark:text-gray-400">
            Page <span class="font-medium">{{ pagination.page }}</span> of
            <span class="font-medium">{{ pagination.totalPages }}</span>
          </span>
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="pagination.page === pagination.totalPages"
            @click="$emit('page-change', pagination.page + 1)"
          >
            Next
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import FileIcon from '@/components/common/FileIcon.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
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

const localPageSize = computed({
  get: () => String(props.pagination.page_size),
  set: (val) => emit('page-size-change', val),
})

const allSelected = computed(
  () => props.files.length > 0 && props.selectedFiles.length === props.files.length,
)
const someSelected = computed(
  () => props.selectedFiles.length > 0 && props.selectedFiles.length < props.files.length,
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
