<template>
  <div class="p-6 space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Trials</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">
          Run and manage information extraction trials
        </p>
      </div>
      <div class="flex items-center gap-4">
        <Tooltip v-if="trialDisabled" :text="trialDisabledReason">
          <button
            class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 dark:hover:bg-blue-800 transition disabled:bg-blue-300 disabled:cursor-not-allowed"
            :disabled="trialDisabled"
            type="button"
            @click="openCreateTrialModal"
          >
            Start New Trial
          </button>
        </Tooltip>
        <button
          v-else
          class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 dark:hover:bg-blue-800 transition"
          :disabled="trialDisabled"
          type="button"
          @click="openCreateTrialModal"
        >
          Start New Trial
        </button>
      </div>
    </div>

    <!-- Filter Panel -->
    <div
      class="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700"
    >
      <!-- Top row: Search + Filters -->
      <div class="flex flex-wrap items-center gap-3">
        <!-- Search -->
        <div class="relative flex-1 max-w-sm min-w-[200px]">
          <input
            v-model="filters.search"
            type="text"
            placeholder="Search trials..."
            class="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            @input="debouncedFetchTrials"
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

        <!-- Status -->
        <select
          v-model="filters.status"
          class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          @change="applyFilters"
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
          @change="applyFilters"
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
          @change="applyFilters"
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
          @change="applyFilters"
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
          @change="applyFilters"
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
          @change="applyFilters"
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
          @click="clearFilters"
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
            @change="applyCustomDateRange"
          />
        </div>
        <div class="flex items-center gap-2">
          <label class="text-sm text-gray-600 dark:text-gray-300">To:</label>
          <input
            v-model="customDateTo"
            type="date"
            class="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            @change="applyCustomDateRange"
          />
        </div>
        <button
          class="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
          @click="applyCustomDateRange"
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
        <span
          v-if="filters.search"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full"
        >
          Search: "{{ filters.search }}"
          <button class="hover:text-red-600" @click="clearSearchFilter">
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
          v-if="filters.status"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full"
        >
          Status: {{ statusLabel(filters.status) }}
          <button class="hover:text-red-600" @click="clearStatusFilter">
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
          v-if="filters.schema_id"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full"
        >
          Schema: {{ schemaName(filters.schema_id) }}
          <button class="hover:text-red-600" @click="clearSchemaFilter">
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
          v-if="filters.prompt_id"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 rounded-full"
        >
          Prompt: {{ promptName(filters.prompt_id) }}
          <button class="hover:text-red-600" @click="clearPromptFilter">
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
          v-if="filters.document_set_id"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 rounded-full"
        >
          Group: {{ groupName(filters.document_set_id) }}
          <button class="hover:text-red-600" @click="clearDocumentSetFilter">
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
          v-if="filters.llm_model"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full"
        >
          Model: {{ filters.llm_model }}
          <button class="hover:text-red-600" @click="clearLlmModelFilter">
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
          v-if="filters.has_failures !== '' && filters.has_failures !== null"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-full"
        >
          Errors: {{ filters.has_failures ? 'Has errors' : 'No errors' }}
          <button class="hover:text-red-600" @click="clearHasFailuresFilter">
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
          v-if="filters.dateRange && filters.dateRange !== 'custom'"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full"
        >
          Date: {{ dateRangeLabel(filters.dateRange) }}
          <button class="hover:text-red-600" @click="clearDateRangeFilter">
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
          v-if="filters.dateRange === 'custom' && customDateFrom"
          class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full"
        >
          Date: {{ customDateFrom }} → {{ customDateTo || 'present' }}
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

    <!-- Error / Loading -->
    <ErrorBanner v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading" />

    <!-- Empty -->
    <EmptyState
      v-else-if="trials.length === 0"
      title="No trials found"
      description="Try changing your filters or create a new trial."
      action-text="Start a Trial"
      :disabled="trialDisabled"
      :disabled-reason="trialDisabledReason"
      @action="openCreateTrialModal"
    >
      <template #icon>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-12 w-12 text-gray-400 dark:text-gray-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
      </template>
    </EmptyState>

    <!-- Trials Grid -->
    <div v-else class="space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <TrialCard
          v-for="trial in trials"
          :key="trial.id"
          :trial="trial"
          :schemas="schemas"
          :prompts="prompts"
          :selected="selectedTrials.includes(trial.id)"
          :highlighted="highlightedTrialId === trial.id"
          @select="toggleTrialSelection(trial.id)"
          @rename="openRenameModal(trial)"
          @delete="confirmDeleteTrial(trial)"
          @retry="retryTrial(trial)"
          @download="openDownloadModal(trial)"
          @cancel="cancelTrial"
          @view-results="viewTrialResults(trial)"
          @view-schema="viewTrialSchema(trial)"
          @view-prompt="viewTrialPrompt(trial)"
        />
      </div>

      <!-- Pagination -->
      <div v-if="trials.length < totalTrials" class="flex justify-center">
        <button
          class="px-4 py-2 rounded-lg text-sm font-semibold bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 border border-gray-200 dark:border-slate-700"
          @click="loadMore"
        >
          Load more ({{ trials.length }}/{{ totalTrials }})
        </button>
      </div>
    </div>

    <!-- Modals -->
    <CreateTrialModal
      v-if="isModalOpen"
      :open="isModalOpen"
      :documents="documents"
      :schemas="schemas"
      :prompts="prompts"
      :project-id="props.projectId"
      @close="isModalOpen = false"
      @create="handleCreateTrial"
    />
    <ConfirmationDialog
      v-if="isConfirmDialogOpen"
      :open="isConfirmDialogOpen"
      title="Delete Trial"
      message="Are you sure you want to delete this trial? This action cannot be undone."
      @confirm="deleteTrial"
      @cancel="isConfirmDialogOpen = false"
    />
    <TrialResults
      v-if="showTrialResultsModal"
      :is-modal="true"
      :project-id="props.projectId"
      :trial-id="selectedTrialId"
      @close="showTrialResultsModal = false"
    />
    <RenameTrialModal
      v-if="showRenameModal"
      :open="showRenameModal"
      :trial="editingTrial"
      @close="showRenameModal = false"
      @rename="submitRename"
    />
    <BatchActionsModal
      v-if="showBatchModal"
      :action="batchAction"
      :trials="selectedTrials"
      :project-id="props.projectId"
      @close="showBatchModal = false"
      @complete="handleBatchActionComplete"
    />
    <TrialSchemaModal
      v-if="showSchemaModal"
      :open="showSchemaModal"
      :schema="selectedSchema"
      :is-snapshot="schemaIsSnapshot"
      @close="showSchemaModal = false"
    />
    <TrialPromptModal
      v-if="showPromptModal"
      :open="showPromptModal"
      :prompt="selectedPrompt"
      :is-snapshot="promptIsSnapshot"
      @close="showPromptModal = false"
    />
    <DownloadModal
      v-if="showDownloadModal"
      :open="showDownloadModal"
      :trial="trialToDownload"
      :project-id="props.projectId"
      @close="showDownloadModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { debounce } from 'perfect-debounce'
import { useToast } from 'vue-toastification'
import { api } from '@/services/api'
import { websocketService } from '@/services/websocket.js'
import CreateTrialModal from '@/components/trials/CreateTrialModal.vue'
import TrialCard from '@/components/trials/TrialCard.vue'
import BatchActionsModal from '@/components/documents/BatchActionsModal.vue'
import RenameTrialModal from '@/components/trials/RenameTrialModal.vue'
import TrialResults from '@/components/trials/TrialResults.vue'
import TrialSchemaModal from '@/components/trials/TrialSchemaModal.vue'
import TrialPromptModal from '@/components/trials/TrialPromptModal.vue'
import DownloadModal from '@/components/trials/DownloadModal.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import EmptyState from '@/components/EmptyState.vue'
import ConfirmationDialog from '@/components/ConfirmationDialog.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import Tooltip from '@/components/Tooltip.vue'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
})

const toast = useToast()

const documents = ref([])
const schemas = ref([])
const prompts = ref([])
const documentGroups = ref([])
const trials = ref([])
const totalTrials = ref(0)
const limit = ref(20)
const offset = ref(0)
const isLoading = ref(true)
const error = ref(null)
const isModalOpen = ref(false)
const isConfirmDialogOpen = ref(false)
const trialToDelete = ref(null)
const showRenameModal = ref(false)
const editingTrial = ref(null)
const selectedTrials = ref([])
const showBatchModal = ref(false)
const batchAction = ref('')
const showTrialResultsModal = ref(false)
const selectedTrialId = ref(null)
const showSchemaModal = ref(false)
const selectedSchema = ref(null)
const schemaIsSnapshot = ref(false)
const showPromptModal = ref(false)
const selectedPrompt = ref(null)
const promptIsSnapshot = ref(false)
const showDownloadModal = ref(false)
const trialToDownload = ref(null)
const highlightedTrialId = ref(null)

// Handle expand-trial event from ActivityBell
const handleExpandTrial = (event) => {
  const trialId = event.detail?.id
  if (!trialId) return

  highlightedTrialId.value = Number(trialId)

  // Try to scroll to the trial card, retrying if it's not found yet
  const tryScrollToTrial = (attempts = 0) => {
    const card = document.getElementById(`trial-card-${trialId}`)
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else if (attempts < 5) {
      // Retry after a short delay if card isn't found yet
      setTimeout(() => tryScrollToTrial(attempts + 1), 200)
    }
  }
  setTimeout(() => tryScrollToTrial(), 100)
}

const trialDisabled = computed(
  () =>
    isLoading.value ||
    schemas.value.length === 0 ||
    documents.value.length === 0 ||
    prompts.value.length === 0,
)

const trialDisabledReason = computed(() => {
  if (isLoading.value) return 'Loading project resources…'
  if (schemas.value.length === 0) return 'You need at least one schema to start a trial.'
  if (documents.value.length === 0)
    return 'You need to upload at least one document to start a trial.'
  if (prompts.value.length === 0) return 'You need to create at least one prompt to start a trial.'
  return ''
})

const filters = ref({
  search: '',
  status: '',
  schema_id: '',
  prompt_id: '',
  document_set_id: '',
  llm_model: '',
  has_failures: '',
  dateRange: '',
})

// Custom date range state
const customDateFrom = ref('')
const customDateTo = ref('')

// Label maps for chips
const dateRangeLabels = {
  today: 'Today',
  yesterday: 'Yesterday',
  week: 'Last 7 Days',
  month: 'Last 30 Days',
  custom: 'Custom Range',
}

const statusLabels = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

const dateRangeLabel = (range) => dateRangeLabels[range] || range
const statusLabel = (status) => statusLabels[status] || status
const schemaName = (id) => schemas.value.find((s) => s.id === id)?.schema_name || `#${id}`
const promptName = (id) => prompts.value.find((p) => p.id === id)?.name || `#${id}`
const groupName = (id) => documentGroups.value.find((g) => g.id === id)?.name || `#${id}`

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

// Compute date bounds for date range filter
const getDateBounds = (range) => {
  const now = new Date()
  const start = new Date(now)

  if (range === 'today') {
    start.setHours(0, 0, 0, 0)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  } else if (range === 'yesterday') {
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    yesterday.setHours(0, 0, 0, 0)
    start.setHours(23, 59, 59, 999)
    return { date_from: yesterday.toISOString(), date_to: start.toISOString() }
  } else if (range === 'week') {
    start.setDate(now.getDate() - 7)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  } else if (range === 'month') {
    start.setDate(now.getDate() - 30)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  } else if (range === 'custom' && customDateFrom.value) {
    const from = new Date(customDateFrom.value)
    from.setHours(0, 0, 0, 0)
    const to = customDateTo.value ? new Date(customDateTo.value) : now
    to.setHours(23, 59, 59, 999)
    return { date_from: from.toISOString(), date_to: to.toISOString() }
  }
  return {}
}

// Handle date range change
const handleDateRangeChange = () => {
  // Don't fetch yet when "Custom Range" is selected — wait for date inputs
  if (filters.value.dateRange === 'custom') return
  applyFilters()
}

const applyCustomDateRange = () => {
  applyFilters()
}

const clearCustomDateRange = () => {
  customDateFrom.value = ''
  customDateTo.value = ''
  filters.value.dateRange = ''
  applyFilters()
}

const availableTrialModels = computed(() => {
  const allModels = trials.value.map((t) => t.llm_model).filter(Boolean)
  return [...new Set(allModels)]
})

function clearFilters() {
  filters.value = {
    search: '',
    status: '',
    schema_id: '',
    prompt_id: '',
    document_set_id: '',
    llm_model: '',
    has_failures: '',
    dateRange: '',
  }
  customDateFrom.value = ''
  customDateTo.value = ''
  applyFilters()
}

const clearSearchFilter = () => {
  filters.value.search = ''
  applyFilters()
}
const clearStatusFilter = () => {
  filters.value.status = ''
  applyFilters()
}
const clearSchemaFilter = () => {
  filters.value.schema_id = ''
  applyFilters()
}
const clearPromptFilter = () => {
  filters.value.prompt_id = ''
  applyFilters()
}
const clearDocumentSetFilter = () => {
  filters.value.document_set_id = ''
  applyFilters()
}
const clearLlmModelFilter = () => {
  filters.value.llm_model = ''
  applyFilters()
}
const clearHasFailuresFilter = () => {
  filters.value.has_failures = ''
  applyFilters()
}
const clearDateRangeFilter = () => {
  filters.value.dateRange = ''
  applyFilters()
}

function paramsFromFilters() {
  const params = {}
  if (filters.value.search) params.search = filters.value.search
  if (filters.value.status) params.status = filters.value.status
  if (filters.value.schema_id) params.schema_id = filters.value.schema_id
  if (filters.value.prompt_id) params.prompt_id = filters.value.prompt_id
  if (filters.value.document_set_id) params.document_set_id = filters.value.document_set_id
  if (filters.value.llm_model) params.llm_model = filters.value.llm_model
  if (filters.value.has_failures !== '' && filters.value.has_failures !== null)
    params.has_failures = filters.value.has_failures
  const { date_from, date_to } = getDateBounds(filters.value.dateRange)
  if (date_from) params.date_from = date_from
  if (date_to) params.date_to = date_to
  return params
}

async function fetchTrialsPage({ limitParam, offsetParam }) {
  const params = { ...paramsFromFilters(), limit: limitParam, offset: offsetParam }
  const res = await api.get(`/project/${props.projectId}/trial`, { params })
  return res.data
}

async function fetchTrials({ reset = false } = {}) {
  try {
    if (reset) isLoading.value = true
    const data = await fetchTrialsPage({ limitParam: limit.value, offsetParam: offset.value })
    totalTrials.value = data.total || 0
    const items = data.items || []
    trials.value = reset ? items : [...trials.value, ...items]
  } catch (err) {
    error.value = err?.message || 'Failed to load trials'
  } finally {
    isLoading.value = false
  }
}

function loadMore() {
  offset.value += limit.value
  fetchTrials({ reset: false })
}

function resetAndFetch() {
  offset.value = 0
  fetchTrials({ reset: true })
}

function applyFilters() {
  resetAndFetch()
}

// Debounced fetch for search input
const debouncedFetchTrials = debounce(() => {
  applyFilters()
}, 300)

function openCreateTrialModal() {
  isModalOpen.value = true
}
async function handleCreateTrial(trialData) {
  try {
    const response = await api.post(`/project/${props.projectId}/trial`, trialData)
    trials.value.unshift(response.data)
    totalTrials.value += 1
    isModalOpen.value = false
    toast.success('Trial created!')
  } catch {
    toast.error('Failed to create trial.')
  }
}

function openRenameModal(trial) {
  editingTrial.value = trial
  showRenameModal.value = true
}
async function submitRename({ id, name, description }) {
  try {
    await api.patch(`/project/${props.projectId}/trial/${id}`, { name, description })
    const idx = trials.value.findIndex((t) => t.id === id)
    if (idx !== -1) {
      trials.value[idx].name = name
      trials.value[idx].description = description
    }
    toast.success('Trial renamed')
    showRenameModal.value = false
  } catch {
    toast.error('Failed to rename trial')
  }
}

function toggleTrialSelection(id) {
  if (selectedTrials.value.includes(id))
    selectedTrials.value = selectedTrials.value.filter((tid) => tid !== id)
  else selectedTrials.value.push(id)
}
function openBatchModal(action) {
  batchAction.value = action
  showBatchModal.value = true
}
function handleBatchActionComplete(updated = false) {
  selectedTrials.value = []
  showBatchModal.value = false
  if (updated) {
    resetAndFetch()
  }
}

async function cancelTrial(trial) {
  try {
    await api.post(`/project/${props.projectId}/trial/${trial.id}/cancel`)
    const idx = trials.value.findIndex((t) => t.id === trial.id)
    if (idx !== -1) {
      trials.value[idx].status = 'cancelled'
      trials.value[idx].is_cancelled = true
    }
    toast.success('Trial cancelled')
  } catch {
    toast.error('Failed to cancel trial')
  }
}

function confirmDeleteTrial(trial) {
  trialToDelete.value = trial
  isConfirmDialogOpen.value = true
}
async function deleteTrial() {
  if (!trialToDelete.value) return
  try {
    await api.delete(`/project/${props.projectId}/trial/${trialToDelete.value.id}`)
    trials.value = trials.value.filter((t) => t.id !== trialToDelete.value.id)
    totalTrials.value = Math.max(0, totalTrials.value - 1)
    toast.success('Trial deleted')
  } catch {
    toast.error('Failed to delete trial')
  } finally {
    isConfirmDialogOpen.value = false
    trialToDelete.value = null
  }
}

async function retryTrial(trial) {
  try {
    const data = {
      schema_id: trial.schema_id,
      prompt_id: trial.prompt_id,
      document_ids: trial.document_ids,
      llm_model: trial.llm_model,
      api_key: trial.api_key,
      base_url: trial.base_url,
      advanced_options: trial.advanced_options || {},
    }
    const response = await api.post(`/project/${props.projectId}/trial`, data)
    trials.value.unshift(response.data)
    totalTrials.value += 1
    toast.success('Trial restarted')
  } catch {
    toast.error('Failed to restart trial')
  }
}
function openDownloadModal(trial) {
  trialToDownload.value = trial
  showDownloadModal.value = true
}

function viewTrialResults(trial) {
  selectedTrialId.value = trial.id
  showTrialResultsModal.value = true
}
function viewTrialSchema(trial) {
  // Prefer the frozen snapshot captured at trial run; fall back to the live
  // schema for trials created before snapshots existed.
  selectedSchema.value =
    trial.schema_snapshot || schemas.value.find((s) => s.id === trial.schema_id) || null
  schemaIsSnapshot.value = !!trial.schema_snapshot
  showSchemaModal.value = true
}
function viewTrialPrompt(trial) {
  selectedPrompt.value =
    trial.prompt_snapshot || prompts.value.find((p) => p.id === trial.prompt_id) || null
  promptIsSnapshot.value = !!trial.prompt_snapshot
  showPromptModal.value = true
}

function getActiveTrialIds() {
  return trials.value
    .filter((t) => t.status === 'pending' || t.status === 'processing')
    .map((t) => t.id)
}

// WebSocket subscription for trial updates
let wsTrialUnsubscribe = null

const startWebSocket = () => {
  wsTrialUnsubscribe = websocketService.onTrialUpdate((data) => {
    // Only update if the trial belongs to this project
    if (String(data.project_id) !== String(props.projectId)) return

    // Update the trial in the list
    const idx = trials.value.findIndex((t) => t.id === data.trial_id)
    if (idx !== -1) {
      const existingTrial = trials.value[idx]
      const updatedTrial = {
        ...existingTrial,
        ...data,
        id: data.trial_id,
        trial_id: undefined,
      }

      // Preserve and merge meta object
      if (data.meta) {
        updatedTrial.meta = { ...(existingTrial.meta || {}), ...data.meta }
      }

      // Trigger reactivity
      trials.value[idx] = updatedTrial
      trials.value = [...trials.value]
    } else {
      // New trial - fetch full list
      resetAndFetch()
    }
  })
}

const stopWebSocket = () => {
  if (wsTrialUnsubscribe) {
    wsTrialUnsubscribe()
    wsTrialUnsubscribe = null
  }
}

onMounted(async () => {
  try {
    const [documentsResponse, schemasResponse, promptsResponse, groupsResponse] = await Promise.all(
      [
        api.get(`/project/${props.projectId}/document`),
        api.get(`/project/${props.projectId}/schema`),
        api.get(`/project/${props.projectId}/prompt`),
        api.get(`/project/${props.projectId}/document-set`, {
          params: { include_auto_generated: true },
        }),
      ],
    )
    documents.value = Array.isArray(documentsResponse.data)
      ? documentsResponse.data
      : documentsResponse.data?.items || []
    schemas.value = schemasResponse.data
    prompts.value = promptsResponse.data
    documentGroups.value = groupsResponse.data
    await resetAndFetch()
  } catch (err) {
    error.value = err?.message || 'Failed to load'
  } finally {
    isLoading.value = false
    startWebSocket()
  }
  // Listen for expand event from ActivityBell
  document.addEventListener('expand-trial', handleExpandTrial)
})
onUnmounted(() => {
  stopWebSocket()
  document.removeEventListener('expand-trial', handleExpandTrial)
})
</script>
