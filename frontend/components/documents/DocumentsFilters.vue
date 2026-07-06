<template>
  <FilterBar
    :search="search"
    search-placeholder="Search documents..."
    :total-count="totalCount"
    item-label="documents"
    :active-filters="activeFilters"
    class="mb-4"
    @update:search="(v) => (search = v)"
    @clear-all="emit('clear-filters')"
    @clear-filter="(key) => emit('clear-filter', key)"
  >
    <template #filters>
      <!-- OCR Engine Filter -->
      <select v-model="ocrEngine" :class="inlineSelectClass" @change="emit('fetch')">
        <option value="">All OCR Engines</option>
        <option value="pypdf">Embedded Text (pypdf)</option>
        <option value="tesseract">Local OCR (Tesseract)</option>
        <option value="mistral_ocr">Mistral OCR</option>
        <option value="llm_vision">Vision LLM</option>
      </select>

      <!-- Date Range Filter -->
      <select v-model="dateRange" :class="inlineSelectClass" @change="emit('date-range-change')">
        <option value="">All Time</option>
        <option value="today">Today</option>
        <option value="yesterday">Yesterday</option>
        <option value="week">Last 7 Days</option>
        <option value="month">Last 30 Days</option>
        <option value="custom">Custom Range...</option>
      </select>

      <!-- Archived Toggle (inline with other filters) -->
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          v-model="includeArchived"
          type="checkbox"
          :class="checkboxClass"
          @change="emit('fetch')"
        />
        <span class="text-sm text-slate-700 dark:text-slate-300">
          Include archived versions
          <span v-if="includeArchived" class="text-xs text-slate-500 dark:text-slate-400 ml-1">
            (showing document history)
          </span>
        </span>
      </label>
    </template>

    <template v-if="dateRange === 'custom'" #custom-range>
      <div class="flex items-center gap-2">
        <label :class="labelClass">From:</label>
        <input
          v-model="customDateFrom"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('apply-custom-range')"
        />
      </div>
      <div class="flex items-center gap-2">
        <label :class="labelClass">To:</label>
        <input
          v-model="customDateTo"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('apply-custom-range')"
        />
      </div>
      <button
        class="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
        @click="emit('apply-custom-range')"
      >
        Apply
      </button>
    </template>
  </FilterBar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getDateRangeLabel } from '@/utils/dateRange'
import FilterBar from '@/components/common/FilterBar.vue'
import type { ActiveFilter } from '@/components/common/FilterBar.vue'
import { inputClass, selectClass, labelClass, checkboxClass } from '@/utils/formStyles'

interface Props {
  totalCount?: number
}

withDefaults(defineProps<Props>(), {
  totalCount: 0,
})

const emit = defineEmits<{
  fetch: []
  'date-range-change': []
  'apply-custom-range': []
  'clear-filters': []
  'clear-filter': [field: string]
}>()

// Filter state — each is a v-model on the parent so fetchDocuments/watchers can read it.
const search = defineModel<string>('search', { default: '' })
const ocrEngine = defineModel<string>('ocrEngine', { default: '' })
const dateRange = defineModel<string>('dateRange', { default: '' })
const includeArchived = defineModel<boolean>('includeArchived', { default: false })
const customDateFrom = defineModel<string>('customDateFrom', { default: '' })
const customDateTo = defineModel<string>('customDateTo', { default: '' })

// `selectClass` carries `w-full`, which inside FilterBar's `flex flex-wrap` row
// forces every dropdown onto its own line at 100% width. Drop `w-full` (and
// pin a sensible auto width) so the selects sit inline and wrap naturally.
const inlineSelectClass = selectClass.replace('w-full', 'w-auto min-w-[9rem]')

// OCR engine labels mapping (for filter chip display)
const ocrEngineLabels: Record<string, string> = {
  pypdf: 'Embedded Text',
  tesseract: 'Local OCR',
  mistral_ocr: 'Mistral OCR',
  llm_vision: 'Vision LLM',
}

const getOcrEngineLabel = (engine: string): string => ocrEngineLabels[engine] || engine

// Active filter chips (unified rendering via FilterBar's activeFilters prop)
const activeFilters = computed<ActiveFilter[]>(() => {
  const chips: ActiveFilter[] = []
  if (search.value) chips.push({ key: 'search', label: `Search: "${search.value}"`, color: 'blue' })
  if (ocrEngine.value)
    chips.push({
      key: 'ocrEngine',
      label: `OCR: ${getOcrEngineLabel(ocrEngine.value)}`,
      color: 'purple',
    })
  if (dateRange.value && dateRange.value !== 'custom')
    chips.push({
      key: 'dateRange',
      label: `Date: ${getDateRangeLabel(dateRange.value)}`,
      color: 'orange',
    })
  if (dateRange.value === 'custom' && customDateFrom.value)
    chips.push({
      key: 'customDate',
      label: `Date: ${customDateFrom.value} → ${customDateTo.value || 'present'}`,
      color: 'orange',
    })
  if (includeArchived.value)
    chips.push({ key: 'includeArchived', label: 'Archived', color: 'gray' })
  return chips
})
</script>
