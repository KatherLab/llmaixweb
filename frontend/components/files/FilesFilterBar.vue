<template>
  <FilterBar
    :search="search"
    :search-placeholder="$t('files.filter.search_placeholder')"
    :total-count="totalCount"
    :item-label="$t('files.filter.item_label')"
    :active-filters="activeFilters"
    @update:search="(v) => (search = v)"
    @search-input="onSearchInput"
    @clear-all="emit('clear-filters')"
    @clear-filter="clearFilter"
  >
    <template #filters>
      <!-- Status Filter -->
      <select v-model="status" :class="inlineSelectClass" @change="emit('fetch')">
        <option value="">{{ $t('files.filter.status_all') }}</option>
        <option value="not_preprocessed">{{ $t('files.filter.status_not_processed') }}</option>
        <option value="processing">{{ $t('files.filter.status_processing') }}</option>
        <option value="completed">{{ $t('files.filter.status_completed') }}</option>
        <option value="failed">{{ $t('files.filter.status_failed') }}</option>
      </select>

      <!-- File Type Filter -->
      <select v-model="fileType" :class="inlineSelectClass" @change="emit('fetch')">
        <option value="">{{ $t('files.filter.type_all') }}</option>
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
      <select v-model="dateRange" :class="inlineSelectClass" @change="onDateRangeChange">
        <option value="">{{ $t('files.filter.date_all') }}</option>
        <option value="today">{{ $t('files.filter.date_today') }}</option>
        <option value="yesterday">{{ $t('files.filter.date_yesterday') }}</option>
        <option value="week">{{ $t('files.filter.date_week') }}</option>
        <option value="month">{{ $t('files.filter.date_month') }}</option>
        <option value="custom">{{ $t('files.filter.date_custom') }}</option>
      </select>
    </template>

    <!-- Custom date range: applied explicitly via the Apply button (no fetch
         on every input change — picking a range means touching both fields). -->
    <template v-if="dateRange === 'custom'" #custom-range>
      <div class="flex items-center gap-2">
        <label :class="labelClass" for="files-filter-date-from">{{
          $t('files.filter.date_from')
        }}</label>
        <input
          id="files-filter-date-from"
          v-model="customFrom"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
        />
      </div>
      <div class="flex items-center gap-2">
        <label :class="labelClass" for="files-filter-date-to">{{
          $t('files.filter.date_to')
        }}</label>
        <input
          id="files-filter-date-to"
          v-model="customTo"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
        />
      </div>
      <BaseButton variant="ghost" size="sm" @click="emit('fetch')">{{
        $t('files.filter.apply')
      }}</BaseButton>
    </template>
  </FilterBar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDateRangeLabel } from '@/utils/dateRange'
import FilterBar from '@/components/common/FilterBar.vue'
import type { ActiveFilter } from '@/components/common/FilterBar.vue'
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

const { t } = useI18n({ useScope: 'global' })

// Filter state — each is a v-model on the parent so fetchFiles/selectAllFiles can read it.
const search = defineModel<string>('search', { default: '' })
const status = defineModel<string>('status', { default: '' })
const fileType = defineModel<string>('fileType', { default: '' })
const dateRange = defineModel<string>('dateRange', { default: '' })
const customFrom = defineModel<string>('customFrom', { default: '' })
const customTo = defineModel<string>('customTo', { default: '' })

// `selectClass` carries `w-full`, which inside FilterBar's `flex flex-wrap` row
// forces every dropdown onto its own line at 100% width. Drop `w-full` (and
// pin a sensible auto width) so the selects sit inline and wrap naturally.
const inlineSelectClass = selectClass.replace('w-full', 'w-auto min-w-[9rem]')

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

// Active filter chips (unified rendering via FilterBar's activeFilters prop)
const activeFilters = computed<ActiveFilter[]>(() => {
  const chips: ActiveFilter[] = []
  if (search.value)
    chips.push({
      key: 'search',
      label: t('files.filter.chip_search', { value: search.value }),
      color: 'blue',
    })
  if (status.value)
    chips.push({
      key: 'status',
      label: t('files.filter.chip_status', { value: status.value }),
      color: 'green',
    })
  if (fileType.value)
    chips.push({
      key: 'fileType',
      label: t('files.filter.chip_type', { value: getFileTypeLabel(fileType.value) }),
      color: 'purple',
    })
  if (dateRange.value && dateRange.value !== 'custom')
    chips.push({
      key: 'dateRange',
      label: t('files.filter.chip_date', { value: getDateRangeLabel(dateRange.value) }),
      color: 'orange',
    })
  if (dateRange.value === 'custom' && customFrom.value)
    chips.push({
      key: 'customDateRange',
      label: t('files.filter.chip_date', {
        value: `${customFrom.value} → ${customTo.value || t('files.filter.present')}`,
      }),
      color: 'orange',
    })
  return chips
})

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

// Consolidated clear: a single entry point for removing one filter.
const clearFilter = (key: string): void => {
  if (key === 'customDateRange') {
    customFrom.value = ''
    customTo.value = ''
    dateRange.value = ''
  } else if (key === 'search') {
    search.value = ''
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  } else if (key === 'status') {
    status.value = ''
  } else if (key === 'fileType') {
    fileType.value = ''
  } else if (key === 'dateRange') {
    dateRange.value = ''
  }
  emit('fetch')
}
</script>
