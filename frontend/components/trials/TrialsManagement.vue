<template>
  <div class="p-6 space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Trials</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">
          Run and manage information extraction trials
        </p>
      </div>
      <div class="flex items-center gap-4">
        <Tooltip v-if="trialDisabled" :text="trialDisabledReason">
          <BaseButton
            variant="primary"
            size="lg"
            class="font-semibold shadow dark:hover:bg-blue-800"
            :disabled="trialDisabled"
            type="button"
            @click="openCreateTrialModal"
            >Start New Trial</BaseButton
          >
        </Tooltip>
        <BaseButton
          v-else
          variant="primary"
          size="lg"
          class="font-semibold shadow dark:hover:bg-blue-800"
          :disabled="trialDisabled"
          type="button"
          @click="openCreateTrialModal"
          >Start New Trial</BaseButton
        >
      </div>
    </div>

    <!-- Filter Panel -->
    <TrialFiltersPanel
      v-model:filters="filters"
      v-model:custom-date-from="customDateFrom"
      v-model:custom-date-to="customDateTo"
      :schemas="schemas"
      :prompts="prompts"
      :document-groups="documentGroups"
      :available-trial-models="availableTrialModels"
      :total-trials="totalTrials"
      @apply="applyFilters"
      @input="debouncedFetchTrials"
      @clear-all="clearFilters"
      @clear-filter="(key) => clearFilter(key)"
    />

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
        <ClipboardList class="h-12 w-12 text-slate-400 dark:text-slate-500" />
      </template>
    </EmptyState>

    <!-- Trials Table -->
    <div v-else class="space-y-4">
      <!-- Batch Actions -->
      <div class="flex justify-between items-center">
        <div class="flex items-center space-x-3">
          <span class="text-sm text-slate-500 dark:text-slate-400">
            {{ totalTrials }} trial{{ totalTrials !== 1 ? 's' : '' }}
          </span>

          <div v-if="selectedTrials.length > 0" class="flex items-center space-x-2">
            <span class="text-sm text-slate-700 dark:text-slate-300">
              {{ selectedTrials.length }} selected
            </span>
            <BaseButton
              variant="link"
              tone="red"
              class="text-sm font-medium"
              @click="performBatchAction('delete')"
            >
              Delete
            </BaseButton>
            <BaseButton
              variant="link"
              tone="gray"
              class="text-sm font-medium"
              @click="selectedTrials = []"
            >
              Clear
            </BaseButton>
          </div>
        </div>
      </div>

      <TrialsTable
        :trials="trials"
        :schemas="schemas"
        :prompts="prompts"
        :selected-trials="selectedTrials"
        :highlighted-trial-id="highlightedTrialId"
        :pagination="tablePagination"
        @toggle-selection="toggleTrialSelection"
        @toggle-all="toggleSelectAll"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        @rename="openRenameModal"
        @delete="confirmDeleteTrial"
        @retry="retryTrial"
        @download="openDownloadModal"
        @cancel="cancelTrial"
        @view-results="viewTrialResults"
        @view-schema="viewTrialSchema"
        @view-prompt="viewTrialPrompt"
      />
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
      :open="showBatchModal"
      mode="trials"
      :action="batchAction"
      :documents="selectedTrials"
      :project-id="props.projectId"
      @close="showBatchModal = false"
      @complete="handleBatchActionComplete"
      @deleted="handleTrialsDeleted"
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
import { useToast } from '@/composables/useToast'
import { ClipboardList } from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { documentsApi } from '@/services/documentsApi'
import { schemasApi } from '@/services/schemasApi'
import { promptsApi } from '@/services/promptsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { getDateRangeBounds } from '@/utils/dateRange'
import { useTrialUpdates } from '@/composables/useTrialUpdates'
import CreateTrialModal from '@/components/trials/CreateTrialModal.vue'
import TrialsTable from '@/components/trials/TrialsTable.vue'
import TrialFiltersPanel from '@/components/trials/TrialFiltersPanel.vue'
import BatchActionsModal from '@/components/documents/BatchActionsModal.vue'
import RenameTrialModal from '@/components/trials/RenameTrialModal.vue'
import TrialResults from '@/components/trials/TrialResults.vue'
import TrialSchemaModal from '@/components/trials/TrialSchemaModal.vue'
import TrialPromptModal from '@/components/trials/TrialPromptModal.vue'
import DownloadModal from '@/components/trials/DownloadModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { extractErrorMessage } from '@/utils/errors'

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
const currentPage = ref(1)
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

const availableTrialModels = computed(() => {
  const allModels = trials.value.map((t) => t.llm_model).filter(Boolean)
  return [...new Set(allModels)]
})

// Compute date bounds for date range filter
const getDateBounds = (range) => {
  return getDateRangeBounds(range, customDateFrom.value, customDateTo.value)
}

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

// Consolidated single-filter clear. Each `key` reproduces the exact behavior of
// the original clearXFilter(): reset the field (and custom dates for the
// custom-range case), then refetch. The panel owns the chip wiring and emits
// `clear-filter(key)`; the parent still owns the refetch so page-reset is
// consistent with the originals.
function clearFilter(key) {
  if (key === 'customDateRange') {
    customDateFrom.value = ''
    customDateTo.value = ''
    filters.value.dateRange = ''
  } else {
    filters.value[key] = ''
  }
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
  const res = await trialsApi.list(props.projectId, params)
  return res.data
}

async function fetchTrials() {
  try {
    isLoading.value = true
    const offsetParam = (currentPage.value - 1) * limit.value
    const data = await fetchTrialsPage({ limitParam: limit.value, offsetParam })
    totalTrials.value = data.total || 0
    trials.value = data.items || []
  } catch (err) {
    error.value = extractErrorMessage(err, 'Failed to load trials')
  } finally {
    isLoading.value = false
  }
}

// Pagination object for the DataTable (shape: { page, page_size, total, total_pages })
const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: limit.value,
  total: totalTrials.value,
  total_pages: Math.max(1, Math.ceil(totalTrials.value / limit.value)),
}))

function handlePageChange(page) {
  currentPage.value = page
  fetchTrials()
}

function handlePageSizeChange(size) {
  limit.value = size
  currentPage.value = 1
  fetchTrials()
}

function resetAndFetch() {
  currentPage.value = 1
  fetchTrials()
}

function applyFilters() {
  resetAndFetch()
}

function toggleSelectAll() {
  if (selectedTrials.value.length > 0 && selectedTrials.value.length >= trials.value.length) {
    // Deselect all on current page
    const pageIds = trials.value.map((t) => t.id)
    selectedTrials.value = selectedTrials.value.filter((id) => !pageIds.includes(id))
  } else {
    // Select all on current page
    const pageIds = trials.value.map((t) => t.id)
    const newIds = pageIds.filter((id) => !selectedTrials.value.includes(id))
    selectedTrials.value = [...selectedTrials.value, ...newIds]
  }
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
    const response = await trialsApi.create(props.projectId, trialData)
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
    await trialsApi.update(props.projectId, id, { name, description })
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

function performBatchAction(action) {
  if (selectedTrials.value.length === 0) return
  batchAction.value = action
  showBatchModal.value = true
}

function handleTrialsDeleted(deletedIds = []) {
  if (deletedIds.length === 0) return
  const idSet = new Set(deletedIds)
  trials.value = trials.value.filter((t) => !idSet.has(t.id))
  totalTrials.value = Math.max(0, totalTrials.value - deletedIds.length)
}

function handleBatchActionComplete() {
  selectedTrials.value = []
  showBatchModal.value = false
}

async function cancelTrial(trial) {
  try {
    await trialsApi.cancel(props.projectId, trial.id)
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
    await trialsApi.delete(props.projectId, trialToDelete.value.id)
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
    const response = await trialsApi.create(props.projectId, data)
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

// WebSocket subscription for trial updates (extracted into useTrialUpdates)
const { start: startWebSocket, stop: stopWebSocket } = useTrialUpdates({
  projectId: computed(() => props.projectId),
  trials,
  resetAndFetch,
})

onMounted(async () => {
  try {
    const [documentsResponse, schemasResponse, promptsResponse, groupsResponse] = await Promise.all(
      [
        documentsApi.list(props.projectId),
        schemasApi.list(props.projectId),
        promptsApi.list(props.projectId),
        documentSetsApi.list(props.projectId, { include_auto_generated: true }),
      ],
    )
    documents.value = Array.isArray(documentsResponse.data)
      ? documentsResponse.data
      : documentsResponse.data?.items || []
    schemas.value = schemasResponse.data
    prompts.value = promptsResponse.data
    // Document-set listing is paginated ({ items, total, page, page_size });
    // extract `.items` so the filter dropdown iterates real sets, not the
    // wrapper object (which renders as empty/white <option>s).
    documentGroups.value = Array.isArray(groupsResponse.data)
      ? groupsResponse.data
      : groupsResponse.data?.items || []
    await resetAndFetch()
  } catch (err) {
    error.value = extractErrorMessage(err, 'Failed to load')
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
