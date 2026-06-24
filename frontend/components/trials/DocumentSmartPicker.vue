<template>
  <div class="mt-4 flex-1 flex flex-col gap-4">
    <div>
      <h4 class="text-sm font-medium text-gray-700 mb-2">Load from Previous Trial</h4>
      <select
        v-model="selectedTrialId"
        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        @change="emit('load-from-trial', selectedTrialId)"
      >
        <option value="">Select a previous trial...</option>
        <option v-for="trial in previousTrials" :key="trial.id" :value="trial.id">
          Trial #{{ trial.id }} - {{ formatDate(trial.created_at) }} ({{
            trial.document_ids.length
          }}
          docs)
        </option>
      </select>
    </div>

    <div>
      <h4 class="text-sm font-medium text-gray-700 mb-2">Filter by Date Range</h4>
      <div class="grid grid-cols-2 gap-2">
        <input
          v-model="dateRange.start"
          class="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          type="date"
        />
        <input
          v-model="dateRange.end"
          class="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          type="date"
        />
      </div>
    </div>

    <div class="flex flex-wrap gap-2 pt-2">
      <button
        class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
        @click="emit('select-recent', 7)"
      >
        Last 7 days
      </button>
      <button
        class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
        @click="emit('select-recent', 30)"
      >
        Last 30 days
      </button>
      <button
        class="px-3 py-1 bg-blue-600 text-white hover:bg-blue-700 text-sm rounded-md"
        :disabled="!dateRange.start && !dateRange.end"
        title="Apply explicit date range"
        @click="emit('apply-date-range', { start: dateRange.start, end: dateRange.end })"
      >
        Apply Date Range
      </button>
    </div>

    <div v-if="selectedIds.length > 0" class="mt-4 p-3 bg-blue-50 rounded-lg">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-blue-900">
          {{ selectedIds.length }} document{{ selectedIds.length > 1 ? 's' : '' }} selected
        </span>
        <div class="flex items-center gap-2">
          <button
            class="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
            type="button"
            @click="showSelectedDocs = !showSelectedDocs"
          >
            <span v-if="!showSelectedDocs">Show</span>
            <span v-else>Hide</span>
            <svg
              :class="{ 'rotate-180': showSelectedDocs }"
              class="w-4 h-4 transition-transform"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                d="M19 9l-7 7-7-7"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
              />
            </svg>
          </button>
          <button class="text-sm text-blue-600 hover:text-blue-800" @click="emit('clear')">
            Clear
          </button>
        </div>
      </div>
      <transition name="fade">
        <div
          v-show="showSelectedDocs"
          class="mt-2 bg-white rounded shadow p-2 max-h-40 overflow-y-auto border border-blue-100"
        >
          <ul class="text-xs text-gray-800 space-y-1">
            <li v-for="docId in selectedIds" :key="docId">
              {{ getDocLabel(docId) }}
            </li>
          </ul>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { formatDate } from '@/utils/formatters.js'

defineProps({
  previousTrials: {
    type: Array,
    default: () => [],
  },
  selectedIds: {
    type: Array,
    default: () => [],
  },
  getDocLabel: {
    type: Function,
    required: true,
  },
})

const emit = defineEmits(['load-from-trial', 'select-recent', 'apply-date-range', 'clear'])

// Local UI state (not reset by initializeForm in the original, so safe to localise)
const selectedTrialId = ref('')
const dateRange = ref({ start: '', end: '' })
const showSelectedDocs = ref(false)
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
