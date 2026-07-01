<template>
  <FilterBar
    :search="filters.search"
    search-placeholder="Search trials..."
    :total-count="totalTrials"
    item-label="trials"
    :active-filters="activeFilters"
    @update:search="(v) => (filters.search = v)"
    @search-input="emit('input')"
    @clear-all="emit('clear-all')"
    @clear-filter="clearFilter"
  >
    <template #filters>
      <!-- Status -->
      <select v-model="filters.status" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">All Status</option>
        <option value="pending">Pending</option>
        <option value="processing">Processing</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
        <option value="cancelled">Cancelled</option>
      </select>

      <!-- Schema -->
      <select v-model="filters.schema_id" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">All Schemas</option>
        <option v-for="schema in schemas" :key="schema.id" :value="schema.id">
          {{ schema.schema_name }}
        </option>
      </select>

      <!-- Prompt -->
      <select v-model="filters.prompt_id" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">All Prompts</option>
        <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id">
          {{ prompt.name }}
        </option>
      </select>

      <!-- Document Group -->
      <select v-model="filters.document_set_id" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">All Groups</option>
        <option v-for="group in documentGroups" :key="group.id" :value="group.id">
          {{ group.name }}
        </option>
      </select>

      <!-- LLM Model -->
      <select v-model="filters.llm_model" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">All Models</option>
        <option v-for="model in availableTrialModels" :key="model" :value="model">
          {{ model }}
        </option>
      </select>

      <!-- Errors -->
      <select v-model="filters.has_failures" :class="inlineSelectClass" @change="emit('apply')">
        <option value="">All</option>
        <option value="true">Has errors</option>
        <option value="false">No errors</option>
      </select>

      <!-- Date Range -->
      <select
        v-model="filters.dateRange"
        :class="inlineSelectClass"
        @change="handleDateRangeChange"
      >
        <option value="">All Time</option>
        <option value="today">Today</option>
        <option value="yesterday">Yesterday</option>
        <option value="week">Last 7 Days</option>
        <option value="month">Last 30 Days</option>
        <option value="custom">Custom Range...</option>
      </select>
    </template>

    <template v-if="filters.dateRange === 'custom'" #custom-range>
      <div class="flex items-center gap-2">
        <label :class="labelClass">From:</label>
        <input
          v-model="customDateFrom"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('apply')"
        />
      </div>
      <div class="flex items-center gap-2">
        <label :class="labelClass">To:</label>
        <input
          v-model="customDateTo"
          type="date"
          :class="[inputClass, 'px-3 py-1.5']"
          @change="emit('apply')"
        />
      </div>
      <button
        class="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
        type="button"
        @click="emit('apply')"
      >
        Apply
      </button>
    </template>
  </FilterBar>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
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

// Two-way bound filter state (parent owns the source of truth via defineModel).
const filters = defineModel<TrialFilters>('filters', { required: true })
const customDateFrom = defineModel<string>('customDateFrom', { default: '' })
const customDateTo = defineModel<string>('customDateTo', { default: '' })

// Label maps for chips
const statusLabels: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

const dateRangeLabel = (range: string): string => getDateRangeLabel(range)
const statusLabel = (status: string): string => statusLabels[status] || status
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
    chips.push({ key: 'search', label: `Search: "${filters.value.search}"`, color: 'blue' })
  if (filters.value.status)
    chips.push({
      key: 'status',
      label: `Status: ${statusLabel(filters.value.status)}`,
      color: 'green',
    })
  if (filters.value.schema_id)
    chips.push({
      key: 'schema_id',
      label: `Schema: ${schemaName(filters.value.schema_id)}`,
      color: 'blue',
    })
  if (filters.value.prompt_id)
    chips.push({
      key: 'prompt_id',
      label: `Prompt: ${promptName(filters.value.prompt_id)}`,
      color: 'teal',
    })
  if (filters.value.document_set_id)
    chips.push({
      key: 'document_set_id',
      label: `Group: ${groupName(filters.value.document_set_id)}`,
      color: 'cyan',
    })
  if (filters.value.llm_model)
    chips.push({ key: 'llm_model', label: `Model: ${filters.value.llm_model}`, color: 'purple' })
  if (filters.value.has_failures !== '' && filters.value.has_failures !== null)
    chips.push({
      key: 'has_failures',
      label: `Errors: ${filters.value.has_failures === 'true' ? 'Has errors' : 'No errors'}`,
      color: 'red',
    })
  if (filters.value.dateRange && filters.value.dateRange !== 'custom')
    chips.push({
      key: 'dateRange',
      label: `Date: ${dateRangeLabel(filters.value.dateRange)}`,
      color: 'orange',
    })
  if (filters.value.dateRange === 'custom' && customDateFrom.value)
    chips.push({
      key: 'customDateRange',
      label: `Date: ${customDateFrom.value} → ${customDateTo.value || 'present'}`,
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
