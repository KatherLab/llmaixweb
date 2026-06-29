<template>
  <div
    class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-700 mb-4"
  >
    <!-- Top row: Search + Filters -->
    <div class="flex items-center gap-3">
      <!-- Search -->
      <SearchInput v-model="search" placeholder="Search documents..." class="flex-1 max-w-sm" />

      <!-- OCR Engine Filter -->
      <select v-model="ocrEngine" :class="selectClass" @change="emit('fetch')">
        <option value="">All OCR Engines</option>
        <option value="pypdf">Embedded Text (pypdf)</option>
        <option value="tesseract">Local OCR (Tesseract)</option>
        <option value="mistral_ocr">Mistral OCR</option>
        <option value="llm_vision">Vision LLM</option>
      </select>

      <!-- Date Range Filter -->
      <select v-model="dateRange" :class="selectClass" @change="emit('date-range-change')">
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

      <div class="ml-auto text-sm text-slate-500 dark:text-slate-400">
        {{ totalCount }} documents
      </div>
    </div>

    <!-- Custom Date Range Picker (shown when "Custom Range" is selected) -->
    <div
      v-if="dateRange === 'custom'"
      class="flex items-center gap-3 mt-3 pt-3 border-t border-slate-200 dark:border-slate-600"
    >
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
        @remove="emit('clear-filter', 'search')"
      />
      <FilterChip
        v-if="ocrEngine"
        :label="`OCR: ${getOcrEngineLabel(ocrEngine)}`"
        color="purple"
        @remove="emit('clear-filter', 'ocrEngine')"
      />
      <FilterChip
        v-if="dateRange && dateRange !== 'custom'"
        :label="`Date: ${getDateRangeLabel(dateRange)}`"
        color="orange"
        @remove="emit('clear-filter', 'dateRange')"
      />
      <FilterChip
        v-if="dateRange === 'custom' && customDateFrom"
        :label="`Date: ${customDateFrom} → ${customDateTo || 'present'}`"
        color="orange"
        @remove="emit('clear-filter', 'customDate')"
      />
      <FilterChip
        v-if="includeArchived"
        label="Archived"
        color="gray"
        @remove="emit('clear-filter', 'includeArchived')"
      />
    </div>

    <!-- Archived Toggle (inline with other filters) -->
    <div class="flex items-center gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-600">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          v-model="includeArchived"
          type="checkbox"
          class="rounded text-blue-600 focus:ring-blue-500"
          @change="emit('fetch')"
        />
        <span class="text-sm text-slate-700 dark:text-slate-300">
          Include archived versions
          <span v-if="includeArchived" class="text-xs text-slate-500 ml-1">
            (showing document history)
          </span>
        </span>
      </label>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { X } from '@lucide/vue'
import SearchInput from '@/components/common/SearchInput.vue'
import FilterChip from '@/components/common/FilterChip.vue'
import { getDateRangeLabel } from '@/utils/dateRange'
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'

defineProps({
  totalCount: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits([
  'fetch',
  'date-range-change',
  'apply-custom-range',
  'clear-filters',
  'clear-filter',
])

// Filter state — each is a v-model on the parent so fetchDocuments/watchers can read it.
const search = defineModel('search', { type: String, default: '' })
const ocrEngine = defineModel('ocrEngine', { type: String, default: '' })
const dateRange = defineModel('dateRange', { type: String, default: '' })
const includeArchived = defineModel('includeArchived', { type: Boolean, default: false })
const customDateFrom = defineModel('customDateFrom', { type: String, default: '' })
const customDateTo = defineModel('customDateTo', { type: String, default: '' })

// OCR engine labels mapping (for filter chip display)
const ocrEngineLabels = {
  pypdf: 'Embedded Text',
  tesseract: 'Local OCR',
  mistral_ocr: 'Mistral OCR',
  llm_vision: 'Vision LLM',
}

const getOcrEngineLabel = (engine) => ocrEngineLabels[engine] || engine

// Matches the original hasActiveFilters computed (includes custom date + archived)
const hasActiveFilters = computed(
  () =>
    search.value ||
    dateRange.value ||
    ocrEngine.value ||
    (dateRange.value === 'custom' && customDateFrom.value) ||
    includeArchived.value,
)
</script>
