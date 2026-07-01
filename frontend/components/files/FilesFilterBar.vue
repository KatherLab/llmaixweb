<template>
  <div
    class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-700"
  >
    <!-- Top row: Search + Status + File Type -->
    <div class="flex items-center gap-3">
      <!-- Search -->
      <SearchInput v-model="search" placeholder="Search files..." @input="onSearchInput" />

      <!-- Status Filter -->
      <select v-model="status" :class="selectClass" @change="emit('fetch')">
        <option value="">All Status</option>
        <option value="not_preprocessed">Not Processed</option>
        <option value="processing">Processing</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
      </select>

      <!-- File Type Filter -->
      <select v-model="fileType" :class="selectClass" @change="emit('fetch')">
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
      <select v-model="dateRange" :class="selectClass" @change="onDateRangeChange">
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
        class="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:text-red-600 dark:hover:text-red-400 transition-colors"
        title="Clear all filters"
        @click="emit('clear-filters')"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="ml-auto text-sm text-slate-500 dark:text-slate-400">{{ totalCount }} files</div>
    </div>

    <!-- Custom Date Range Picker (shown when "Custom Range" is selected) -->
    <div
      v-if="dateRange === 'custom'"
      class="flex items-center gap-3 mt-3 pt-3 border-t border-slate-200 dark:border-slate-600"
    >
      <div class="flex items-center gap-2">
        <label :class="labelClass">From:</label>
        <input
          v-model="customFrom"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('fetch')"
        />
      </div>
      <div class="flex items-center gap-2">
        <label :class="labelClass">To:</label>
        <input
          v-model="customTo"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('fetch')"
        />
      </div>
      <BaseButton variant="ghost" size="sm" @click="emit('fetch')">Apply</BaseButton>
    </div>

    <!-- Active Filters Summary -->
    <div
      v-if="hasActiveFilters"
      class="flex items-center gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-600"
    >
      <span class="text-xs text-slate-500 dark:text-slate-400">Active filters:</span>
      <FilterChip
        v-if="search"
        :label="`Search: &quot;${search}&quot;`"
        color="blue"
        @remove="clearSearch"
      />
      <FilterChip
        v-if="status"
        :label="`Status: ${status}`"
        color="green"
        @remove="clearField('status')"
      />
      <FilterChip
        v-if="fileType"
        :label="`Type: ${getFileTypeLabel(fileType)}`"
        color="purple"
        @remove="clearField('fileType')"
      />
      <FilterChip
        v-if="dateRange && dateRange !== 'custom'"
        :label="`Date: ${getDateRangeLabel(dateRange)}`"
        color="orange"
        @remove="clearField('dateRange')"
      />
      <FilterChip
        v-if="dateRange === 'custom' && customFrom"
        :label="`Date: ${customFrom} → ${customTo || 'present'}`"
        color="orange"
        @remove="clearCustomDateRange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X } from '@lucide/vue'
import { getDateRangeLabel } from '@/utils/dateRange'
import SearchInput from '@/components/common/SearchInput.vue'
import FilterChip from '@/components/common/FilterChip.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'

interface Props {
  totalCount?: number
}

withDefaults(defineProps<Props>(), {
  totalCount: 0,
})

const emit = defineEmits<{
  fetch: []
  'clear-filters': []
}>()

// Filter state — each is a v-model on the parent so fetchFiles/selectAllFiles can read it.
const search = defineModel<string>('search', { default: '' })
const status = defineModel<string>('status', { default: '' })
const fileType = defineModel<string>('fileType', { default: '' })
const dateRange = defineModel<string>('dateRange', { default: '' })
const customFrom = defineModel<string>('customFrom', { default: '' })
const customTo = defineModel<string>('customTo', { default: '' })

// File type labels mapping
const fileTypeLabels: Record<string, string> = {
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

const getFileTypeLabel = (type: string): string => fileTypeLabels[type] || type

// Any of the filters being set counts as "active" (drives the clear-X button,
// the active-filters summary, and the parent's empty/upload-state switching).
const hasActiveFilters = computed(
  () => search.value || status.value || fileType.value || dateRange.value,
)

// Debounce timer for search input
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

const onSearchInput = (): void => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    emit('fetch')
  }, 300)
}

// Handle date range change — 'custom' waits for date selection, others fetch immediately.
const onDateRangeChange = (): void => {
  if (dateRange.value === 'custom') return
  emit('fetch')
}

const clearSearch = (): void => {
  search.value = ''
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  emit('fetch')
}

type FilterableField = 'status' | 'fileType' | 'dateRange'

const clearField = (field: FilterableField): void => {
  if (field === 'status') status.value = ''
  else if (field === 'fileType') fileType.value = ''
  else if (field === 'dateRange') dateRange.value = ''
  emit('fetch')
}

const clearCustomDateRange = (): void => {
  customFrom.value = ''
  customTo.value = ''
  dateRange.value = ''
  emit('fetch')
}
</script>
