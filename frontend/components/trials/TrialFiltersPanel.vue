<template>
  <FilterBar
    :search="filters.search"
    :search-placeholder="$t('trials.filters.search_placeholder')"
    :total-count="totalTrials"
    :item-label="$t('trials.filters.item_label')"
    :active-filters="activeFilters"
    @update:search="(v) => (filters.search = v)"
    @search-input="emit('input')"
    @clear-all="emit('clear-all')"
    @clear-filter="clearFilter"
  >
    <template #filters>
      <!-- Status -->
      <select v-model="filters.status" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">{{ $t('trials.filters.all_status') }}</option>
        <option value="pending">{{ $t('trials.status.pending') }}</option>
        <option value="processing">{{ $t('trials.status.processing') }}</option>
        <option value="completed">{{ $t('trials.status.completed') }}</option>
        <option value="failed">{{ $t('trials.status.failed') }}</option>
        <option value="cancelled">{{ $t('trials.status.cancelled') }}</option>
      </select>

      <!-- Schema -->
      <select v-model="filters.schema_id" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">{{ $t('trials.filters.all_schemas') }}</option>
        <option v-for="schema in schemas" :key="schema.id" :value="schema.id">
          {{ schema.schema_name }}
        </option>
      </select>

      <!-- Prompt -->
      <select v-model="filters.prompt_id" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">{{ $t('trials.filters.all_prompts') }}</option>
        <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id">
          {{ prompt.name }}
        </option>
      </select>

      <!-- Document Group -->
      <select v-model="filters.document_set_id" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">{{ $t('trials.filters.all_groups') }}</option>
        <option v-for="group in documentGroups" :key="group.id" :value="group.id">
          {{ group.name }}
        </option>
      </select>

      <!-- LLM Model -->
      <select v-model="filters.llm_model" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">{{ $t('trials.filters.all_models') }}</option>
        <option v-for="model in availableTrialModels" :key="model" :value="model">
          {{ model }}
        </option>
      </select>

      <!-- Errors -->
      <select v-model="filters.has_failures" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">{{ $t('trials.filters.all') }}</option>
        <option value="true">{{ $t('trials.filters.has_errors') }}</option>
        <option value="false">{{ $t('trials.filters.no_errors') }}</option>
      </select>

      <!-- Date Range -->
      <select
        v-model="filters.dateRange"
        :class="inlineSelectClass"
        @change="handleDateRangeChange"
      >
        <option value="">{{ $t('trials.filters.all_time') }}</option>
        <option value="today">{{ $t('trials.filters.today') }}</option>
        <option value="yesterday">{{ $t('trials.filters.yesterday') }}</option>
        <option value="week">{{ $t('trials.filters.last_7_days') }}</option>
        <option value="month">{{ $t('trials.filters.last_30_days') }}</option>
        <option value="custom">{{ $t('trials.filters.custom_range') }}</option>
      </select>
    </template>

    <template v-if="filters.dateRange === 'custom'" #custom-range>
      <div class="flex items-center gap-2">
        <label :class="labelClass" for="trial-filter-date-from">{{
          $t('trials.filters.from')
        }}</label>
        <input
          id="trial-filter-date-from"
          v-model="customDateFrom"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('apply')"
        />
      </div>
      <div class="flex items-center gap-2">
        <label :class="labelClass" for="trial-filter-date-to">{{ $t('trials.filters.to') }}</label>
        <input
          id="trial-filter-date-to"
          v-model="customDateTo"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('apply')"
        />
      </div>
      <button
        class="px-3 py-1.5 text-sm text-primary hover:text-primary transition-colors"
        type="button"
        @click="emit('apply')"
      >
        {{ $t('trials.filters.apply') }}
      </button>
    </template>
  </FilterBar>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDateRangeLabel } from '@/utils/dateRange'
import FilterBar from '@/components/common/FilterBar.vue'
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'
import type { Schema, Prompt, DocumentSetSummary } from '@/types'

/** Two-way bound filter state shared with the parent (TrialsManagement). */
interface TrialFilters {
  search: string
  status: string
  schema_id: string | number
  prompt_id: string | number
  document_set_id: string | number
  llm_model: string
  has_failures: string
  dateRange: string
  [key: string]: unknown
}

interface FilterChip {
  key: string
  label: string
  color: string
}

// `selectClass` carries `w-full`, which inside FilterBar's `flex flex-wrap` row
// forces every dropdown onto its own line at 100% width. Drop `w-full` (and
// pin a sensible auto width) so the selects sit inline and wrap naturally.
const inlineSelectClass = selectClass.replace('w-full', 'w-auto min-w-[9rem]')

const props = defineProps({
  schemas: { type: Array as PropType<Schema[]>, default: () => [] },
  prompts: { type: Array as PropType<Prompt[]>, default: () => [] },
  documentGroups: { type: Array as PropType<DocumentSetSummary[]>, default: () => [] },
  availableTrialModels: { type: Array as PropType<string[]>, default: () => [] },
  totalTrials: { type: Number, default: 0 },
})

const emit = defineEmits<{
  apply: []
  input: []
  'clear-all': []
  'clear-filter': [key: string]
}>()

const { t } = useI18n({ useScope: 'global' })

// Two-way bound filter state (parent owns the source of truth via defineModel).
const filters = defineModel<TrialFilters>('filters', { required: true })
const customDateFrom = defineModel<string>('customDateFrom', { default: '' })
const customDateTo = defineModel<string>('customDateTo', { default: '' })

// Label maps for chips
const statusLabels = (): Record<string, string> => ({
  pending: t('trials.status.pending'),
  processing: t('trials.status.processing'),
  completed: t('trials.status.completed'),
  failed: t('trials.status.failed'),
  cancelled: t('trials.status.cancelled'),
})

const dateRangeLabel = (range: string): string => getDateRangeLabel(range)
const statusLabel = (status: string): string => statusLabels()[status] || status
const schemaName = (id: string | number): string =>
  props.schemas.find((s) => s.id === id)?.schema_name || `#${id}`
const promptName = (id: string | number): string =>
  props.prompts.find((p) => p.id === id)?.name || `#${id}`
const groupName = (id: string | number): string =>
  props.documentGroups.find((g) => g.id === id)?.name || `#${id}`

// Active filter chips (unified rendering via FilterBar's activeFilters prop)
const activeFilters = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.search)
    chips.push({
      key: 'search',
      label: t('trials.filters.chip_search', { value: filters.value.search }),
      color: 'blue',
    })
  if (filters.value.status)
    chips.push({
      key: 'status',
      label: t('trials.filters.chip_status', { value: statusLabel(filters.value.status) }),
      color: 'green',
    })
  if (filters.value.schema_id)
    chips.push({
      key: 'schema_id',
      label: t('trials.filters.chip_schema', { value: schemaName(filters.value.schema_id) }),
      color: 'blue',
    })
  if (filters.value.prompt_id)
    chips.push({
      key: 'prompt_id',
      label: t('trials.filters.chip_prompt', { value: promptName(filters.value.prompt_id) }),
      color: 'teal',
    })
  if (filters.value.document_set_id)
    chips.push({
      key: 'document_set_id',
      label: t('trials.filters.chip_group', { value: groupName(filters.value.document_set_id) }),
      color: 'cyan',
    })
  if (filters.value.llm_model)
    chips.push({
      key: 'llm_model',
      label: t('trials.filters.chip_model', { value: filters.value.llm_model }),
      color: 'purple',
    })
  if (filters.value.has_failures !== '' && filters.value.has_failures !== null)
    chips.push({
      key: 'has_failures',
      label: t('trials.filters.chip_errors', {
        value:
          filters.value.has_failures === 'true'
            ? t('trials.filters.has_errors')
            : t('trials.filters.no_errors'),
      }),
      color: 'red',
    })
  if (filters.value.dateRange && filters.value.dateRange !== 'custom')
    chips.push({
      key: 'dateRange',
      label: t('trials.filters.chip_date', { value: dateRangeLabel(filters.value.dateRange) }),
      color: 'orange',
    })
  if (filters.value.dateRange === 'custom' && customDateFrom.value)
    chips.push({
      key: 'customDateRange',
      label: t('trials.filters.chip_date', {
        value: `${customDateFrom.value} → ${customDateTo.value || t('trials.filters.present')}`,
      }),
      color: 'orange',
    })
  return chips
})

// Don't fetch yet when "Custom Range" is selected — wait for date inputs
const handleDateRangeChange = (): void => {
  if (filters.value.dateRange === 'custom') return
  emit('apply')
}

// Consolidated clear: a single entry point for removing one filter.
const clearFilter = (key: string): void => {
  if (key === 'customDateRange') {
    customDateFrom.value = ''
    customDateTo.value = ''
    filters.value.dateRange = ''
  } else {
    filters.value[key] = ''
  }
  emit('apply')
}
</script>
