<template>
  <div
    class="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700"
  >
    <!-- Top row: Search + Filters -->
    <div class="flex flex-wrap items-center gap-3">
      <!-- Search -->
      <SearchInput v-model="filters.search" placeholder="Search trials..." @input="emit('input')" />

      <!-- Status -->
      <select
        v-model="filters.status"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('apply')"
      >
        <option value="">All Status</option>
        <option value="pending">Pending</option>
        <option value="processing">Processing</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
        <option value="cancelled">Cancelled</option>
      </select>

      <!-- Schema -->
      <select
        v-model="filters.schema_id"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('apply')"
      >
        <option value="">All Schemas</option>
        <option v-for="schema in schemas" :key="schema.id" :value="schema.id">
          {{ schema.schema_name }}
        </option>
      </select>

      <!-- Prompt -->
      <select
        v-model="filters.prompt_id"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('apply')"
      >
        <option value="">All Prompts</option>
        <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id">
          {{ prompt.name }}
        </option>
      </select>

      <!-- Document Group -->
      <select
        v-model="filters.document_set_id"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('apply')"
      >
        <option value="">All Groups</option>
        <option v-for="group in documentGroups" :key="group.id" :value="group.id">
          {{ group.name }}
        </option>
      </select>

      <!-- LLM Model -->
      <select
        v-model="filters.llm_model"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('apply')"
      >
        <option value="">All Models</option>
        <option v-for="model in availableTrialModels" :key="model" :value="model">
          {{ model }}
        </option>
      </select>

      <!-- Errors -->
      <select
        v-model="filters.has_failures"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="emit('apply')"
      >
        <option value="">All</option>
        <option :value="true">Has errors</option>
        <option :value="false">No errors</option>
      </select>

      <!-- Date Range -->
      <select
        v-model="filters.dateRange"
        class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
        @change="handleDateRangeChange"
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
        type="button"
        @click="emit('clear-all')"
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

      <div class="ml-auto text-sm text-gray-500 dark:text-gray-400">{{ totalTrials }} trials</div>
    </div>

    <!-- Custom Date Range Picker (shown when "Custom Range" is selected) -->
    <div
      v-if="filters.dateRange === 'custom'"
      class="flex items-center gap-3 mt-3 pt-3 border-t border-gray-200 dark:border-slate-600"
    >
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-600 dark:text-gray-300">From:</label>
        <input
          v-model="customDateFrom"
          type="date"
          class="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          @change="emit('apply')"
        />
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-600 dark:text-gray-300">To:</label>
        <input
          v-model="customDateTo"
          type="date"
          class="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
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
    </div>

    <!-- Active Filters Summary -->
    <div
      v-if="hasActiveFilters"
      class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-slate-600"
    >
      <span class="text-xs text-gray-500 dark:text-gray-400">Active filters:</span>
      <FilterChip
        v-if="filters.search"
        :label="`Search: &quot;${filters.search}&quot;`"
        color="blue"
        @remove="clearFilter('search')"
      />
      <FilterChip
        v-if="filters.status"
        :label="`Status: ${statusLabel(filters.status)}`"
        color="green"
        @remove="clearFilter('status')"
      />
      <FilterChip
        v-if="filters.schema_id"
        :label="`Schema: ${schemaName(filters.schema_id)}`"
        color="indigo"
        @remove="clearFilter('schema_id')"
      />
      <FilterChip
        v-if="filters.prompt_id"
        :label="`Prompt: ${promptName(filters.prompt_id)}`"
        color="teal"
        @remove="clearFilter('prompt_id')"
      />
      <FilterChip
        v-if="filters.document_set_id"
        :label="`Group: ${groupName(filters.document_set_id)}`"
        color="cyan"
        @remove="clearFilter('document_set_id')"
      />
      <FilterChip
        v-if="filters.llm_model"
        :label="`Model: ${filters.llm_model}`"
        color="purple"
        @remove="clearFilter('llm_model')"
      />
      <FilterChip
        v-if="filters.has_failures !== '' && filters.has_failures !== null"
        :label="`Errors: ${filters.has_failures ? 'Has errors' : 'No errors'}`"
        color="red"
        @remove="clearFilter('has_failures')"
      />
      <FilterChip
        v-if="filters.dateRange && filters.dateRange !== 'custom'"
        :label="`Date: ${dateRangeLabel(filters.dateRange)}`"
        color="orange"
        @remove="clearFilter('dateRange')"
      />
      <FilterChip
        v-if="filters.dateRange === 'custom' && customDateFrom"
        :label="`Date: ${customDateFrom} → ${customDateTo || 'present'}`"
        color="orange"
        @remove="clearFilter('customDateRange')"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getDateRangeLabel } from '@/utils/dateRange'
import FilterChip from '@/components/common/FilterChip.vue'
import SearchInput from '@/components/common/SearchInput.vue'

const props = defineProps({
  schemas: { type: Array, default: () => [] },
  prompts: { type: Array, default: () => [] },
  documentGroups: { type: Array, default: () => [] },
  availableTrialModels: { type: Array, default: () => [] },
  totalTrials: { type: Number, default: 0 },
})

const emit = defineEmits(['apply', 'input', 'clear-all', 'clear-filter'])

// Two-way bound filter state (parent owns the source of truth via defineModel).
const filters = defineModel('filters', { type: Object, required: true })
const customDateFrom = defineModel('customDateFrom', { type: String, default: '' })
const customDateTo = defineModel('customDateTo', { type: String, default: '' })

// Label maps for chips
const statusLabels = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

const dateRangeLabel = (range) => getDateRangeLabel(range)
const statusLabel = (status) => statusLabels[status] || status
const schemaName = (id) => props.schemas.find((s) => s.id === id)?.schema_name || `#${id}`
const promptName = (id) => props.prompts.find((p) => p.id === id)?.name || `#${id}`
const groupName = (id) => props.documentGroups.find((g) => g.id === id)?.name || `#${id}`

// Check if any filters are active
const hasActiveFilters = computed(() => {
  return (
    filters.value.search ||
    filters.value.status ||
    filters.value.schema_id ||
    filters.value.prompt_id ||
    filters.value.document_set_id ||
    filters.value.llm_model ||
    (filters.value.has_failures !== '' && filters.value.has_failures !== null) ||
    filters.value.dateRange
  )
})

// Don't fetch yet when "Custom Range" is selected — wait for date inputs
const handleDateRangeChange = () => {
  if (filters.value.dateRange === 'custom') return
  emit('apply')
}

// Consolidated clear: a single entry point for removing one filter.
// `key` matches the original per-filter clear behavior:
//   - reset the filter field to its default (and custom dates for the custom range)
//   - then refetch via the parent's apply handler.
const clearFilter = (key) => {
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
