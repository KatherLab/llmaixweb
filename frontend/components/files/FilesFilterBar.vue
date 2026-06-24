<template>
  <div
    class="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700"
  >
    <!-- Top row: Search + Status + File Type -->
    <div class="flex items-center gap-3">
      <!-- Search -->
      <div class="relative flex-1 max-w-sm">
        <input
          v-model="search"
          type="text"
          placeholder="Search files..."
          class="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          @input="onSearchInput"
        />
        <svg
          class="absolute left-3 top-2.5 h-4 w-4 text-gray-400 dark:text-gray-500"
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
      </div>

      <!-- Status Filter -->
      <select
        v-model="status"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('fetch')"
      >
        <option value="">All Status</option>
        <option value="not_preprocessed">Not Processed</option>
        <option value="processing">Processing</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
      </select>

      <!-- File Type Filter -->
      <select
        v-model="fileType"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('fetch')"
      >
        <option value="">All Types</option>
        <option value="application/pdf">PDF</option>
        <option value="image/png">PNG</option>
        <option value="image/jpeg">JPEG</option>
        <option value="text/csv">CSV</option>
        <option value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">
          XLSX
        </option>
        <option value="application/vnd.ms-excel">XLS</option>
        <option value="text/plain">TXT</option>
        <option value="application/msword">DOC</option>
        <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">
          DOCX
        </option>
      </select>

      <!-- Date Range Filter -->
      <select
        v-model="dateRange"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="onDateRangeChange"
      >
        <option value="">All Time</option>
        <option value="today">Today</option>
        <option value="yesterday">Yesterday</option>
        <option value="week">Last 7 Days</option>
        <option value="month">Last 30 Days</option>
        <option value="custom">Custom Range...</option>
      </select>

      <!-- Clear Filters -->
      <button
        v-if="hasActiveFilters"
        class="px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 transition-colors"
        title="Clear all filters"
        @click="emit('clear-filters')"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      <div class="ml-auto text-sm text-gray-500 dark:text-gray-400">{{ totalCount }} files</div>
    </div>

    <!-- Custom Date Range Picker (shown when "Custom Range" is selected) -->
    <div
      v-if="dateRange === 'custom'"
      class="flex items-center gap-3 mt-3 pt-3 border-t border-gray-200 dark:border-slate-600"
    >
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-600 dark:text-gray-300">From:</label>
        <input
          v-model="customFrom"
          type="date"
          class="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          @change="emit('fetch')"
        />
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-600 dark:text-gray-300">To:</label>
        <input
          v-model="customTo"
          type="date"
          class="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          @change="emit('fetch')"
        />
      </div>
      <button
        class="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
        @click="emit('fetch')"
      >
        Apply
      </button>
    </div>

    <!-- Active Filters Summary -->
    <div
      v-if="hasActiveFilters"
      class="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-slate-600"
    >
      <span class="text-xs text-gray-500 dark:text-gray-400">Active filters:</span>
      <span
        v-if="search"
        class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full"
      >
        Search: "{{ search }}"
        <button class="hover:text-red-600" @click="clearSearch">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </span>
      <span
        v-if="status"
        class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full"
      >
        Status: {{ status }}
        <button class="hover:text-red-600" @click="clearField('status')">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </span>
      <span
        v-if="fileType"
        class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full"
      >
        Type: {{ getFileTypeLabel(fileType) }}
        <button class="hover:text-red-600" @click="clearField('fileType')">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </span>
      <span
        v-if="dateRange && dateRange !== 'custom'"
        class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full"
      >
        Date: {{ getDateRangeLabel(dateRange) }}
        <button class="hover:text-red-600" @click="clearField('dateRange')">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </span>
      <span
        v-if="dateRange === 'custom' && customFrom"
        class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full"
      >
        Date: {{ customFrom }} → {{ customTo || 'present' }}
        <button class="hover:text-red-600" @click="clearCustomDateRange">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getDateRangeLabel } from '@/utils/dateRange'

defineProps({
  totalCount: { type: Number, default: 0 },
})

const emit = defineEmits(['fetch', 'clear-filters'])

// Filter state — each is a v-model on the parent so fetchFiles/selectAllFiles can read it.
const search = defineModel('search', { type: String, default: '' })
const status = defineModel('status', { type: String, default: '' })
const fileType = defineModel('fileType', { type: String, default: '' })
const dateRange = defineModel('dateRange', { type: String, default: '' })
const customFrom = defineModel('customFrom', { type: String, default: '' })
const customTo = defineModel('customTo', { type: String, default: '' })

// File type labels mapping
const fileTypeLabels = {
  'application/pdf': 'PDF',
  'image/png': 'PNG',
  'image/jpeg': 'JPEG',
  'text/csv': 'CSV',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
  'application/vnd.ms-excel': 'XLS',
  'text/plain': 'TXT',
  'application/msword': 'DOC',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
}

const getFileTypeLabel = (type) => fileTypeLabels[type] || type

// Any of the filters being set counts as "active" (drives the clear-X button,
// the active-filters summary, and the parent's empty/upload-state switching).
const hasActiveFilters = computed(
  () => search.value || status.value || fileType.value || dateRange.value,
)

// Debounce timer for search input
let searchDebounceTimer = null

const onSearchInput = () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    emit('fetch')
  }, 300)
}

// Handle date range change — 'custom' waits for date selection, others fetch immediately.
const onDateRangeChange = () => {
  if (dateRange.value === 'custom') return
  emit('fetch')
}

const clearSearch = () => {
  search.value = ''
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  emit('fetch')
}

const clearField = (field) => {
  if (field === 'status') status.value = ''
  else if (field === 'fileType') fileType.value = ''
  else if (field === 'dateRange') dateRange.value = ''
  emit('fetch')
}

const clearCustomDateRange = () => {
  customFrom.value = ''
  customTo.value = ''
  dateRange.value = ''
  emit('fetch')
}
</script>
