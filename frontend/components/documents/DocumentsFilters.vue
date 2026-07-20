<template>
  <FilterBar
    :search="search"
    :search-placeholder="$t('documents.filters.search_placeholder')"
    :total-count="totalCount"
    :item-label="$t('documents.filters.item_label')"
    :active-filters="activeFilters"
    class="mb-4"
    @update:search="(v) => (search = v)"
    @clear-all="emit('clear-filters')"
    @clear-filter="(key) => emit('clear-filter', key)"
  >
    <template #filters>
      <!-- OCR Engine Filter -->
      <select v-model="ocrEngine" :class="inlineSelectClass" @change="emit('fetch')">
        <option value="">{{ $t('documents.filters.ocr_all') }}</option>
        <option value="pypdf">{{ $t('documents.filters.ocr_pypdf') }}</option>
        <option value="tesseract">{{ $t('documents.filters.ocr_tesseract') }}</option>
        <option value="mistral_ocr">Mistral OCR</option>
        <option value="llm_vision">Vision LLM</option>
      </select>

      <!-- Date Range Filter -->
      <select v-model="dateRange" :class="inlineSelectClass" @change="emit('date-range-change')">
        <option value="">{{ $t('documents.filters.date_all') }}</option>
        <option value="today">{{ $t('documents.filters.date_today') }}</option>
        <option value="yesterday">{{ $t('documents.filters.date_yesterday') }}</option>
        <option value="week">{{ $t('documents.filters.date_week') }}</option>
        <option value="month">{{ $t('documents.filters.date_month') }}</option>
        <option value="custom">{{ $t('documents.filters.date_custom') }}</option>
      </select>

      <!-- Archived Toggle (inline with other filters) -->
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          v-model="includeArchived"
          type="checkbox"
          :class="checkboxClass"
          @change="emit('fetch')"
        />
        <span class="text-sm text-content-muted">
          {{ $t('documents.filters.include_archived') }}
          <span v-if="includeArchived" class="text-xs text-content-muted ml-1">
            {{ $t('documents.filters.showing_history') }}
          </span>
        </span>
      </label>
    </template>

    <!-- Custom date range: applied explicitly via the Apply button (no fetch
         on every input change — picking a range means touching both fields). -->
    <template v-if="dateRange === 'custom'" #custom-range>
      <div class="flex items-center gap-2">
        <label :class="labelClass" for="documents-filter-date-from">{{
          $t('documents.filters.from')
        }}</label>
        <input
          id="documents-filter-date-from"
          v-model="customDateFrom"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
        />
      </div>
      <div class="flex items-center gap-2">
        <label :class="labelClass" for="documents-filter-date-to">{{
          $t('documents.filters.to')
        }}</label>
        <input
          id="documents-filter-date-to"
          v-model="customDateTo"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
        />
      </div>
      <button
        class="px-3 py-1.5 text-sm text-primary hover:text-primary transition-colors"
        @click="emit('apply-custom-range')"
      >
        {{ $t('documents.filters.apply') }}
      </button>
    </template>
  </FilterBar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n({ useScope: 'global' })

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
  pypdf: t('documents.filters.ocr_label_pypdf'),
  tesseract: t('documents.filters.ocr_label_tesseract'),
  mistral_ocr: 'Mistral OCR',
  llm_vision: 'Vision LLM',
}

const getOcrEngineLabel = (engine: string): string => ocrEngineLabels[engine] || engine

// Active filter chips (unified rendering via FilterBar's activeFilters prop)
const activeFilters = computed<ActiveFilter[]>(() => {
  const chips: ActiveFilter[] = []
  if (search.value)
    chips.push({
      key: 'search',
      label: t('documents.filters.chip_search', { query: search.value }),
      color: 'blue',
    })
  if (ocrEngine.value)
    chips.push({
      key: 'ocrEngine',
      label: t('documents.filters.chip_ocr', { label: getOcrEngineLabel(ocrEngine.value) }),
      color: 'purple',
    })
  if (dateRange.value && dateRange.value !== 'custom')
    chips.push({
      key: 'dateRange',
      label: t('documents.filters.chip_date', { label: getDateRangeLabel(dateRange.value) }),
      color: 'orange',
    })
  if (dateRange.value === 'custom' && customDateFrom.value)
    chips.push({
      key: 'customDate',
      label: t('documents.filters.chip_custom_date', {
        from: customDateFrom.value,
        to: customDateTo.value || t('documents.filters.present'),
      }),
      color: 'orange',
    })
  if (includeArchived.value)
    chips.push({
      key: 'includeArchived',
      label: t('documents.filters.chip_archived'),
      color: 'gray',
    })
  return chips
})
</script>
