<template>
  <div class="p-6 space-y-8">
    <!-- Header -->
    <PageHeader
      title="Trials"
      subtitle="Run an AI model over your documents to extract structured data, then compare results across trials."
      :sticky="false"
      class="mb-6"
    >
      <template #actions>
        <Tooltip v-if="trialDisabled" :text="trialDisabledReason">
          <BaseButton
            variant="primary"
            :disabled="trialDisabled"
            type="button"
            @click="openCreateTrialModal"
            >Start New Trial</BaseButton
          >
        </Tooltip>
        <BaseButton
          v-else
          variant="primary"
          :disabled="trialDisabled"
          type="button"
          @click="openCreateTrialModal"
          >Start New Trial</BaseButton
        >
      </template>
    </PageHeader>

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
    <SkeletonTable v-if="isLoading" :columns="7" :rows="6" />

    <!-- Empty: no trials have ever been created -->
    <EmptyState
      v-else-if="trials.length === 0 && !hasActiveFilters"
      title="No trials yet"
      description="Run your first extraction trial to see results here."
      action-text="Start a Trial"
      :disabled="trialDisabled"
      :disabled-reason="trialDisabledReason"
      @action="openCreateTrialModal"
    >
      <template #icon>
        <ClipboardList class="h-12 w-12 text-content-subtle" />
      </template>
    </EmptyState>

    <!-- Empty: filters matched nothing -->
    <EmptyState
      v-else-if="trials.length === 0 && hasActiveFilters"
      title="No trials match your filters"
      description="Try adjusting or clearing your filters to see more trials."
    >
      <template #icon>
        <SearchX class="h-12 w-12 text-content-subtle" />
      </template>
      <template #action>
        <BaseButton variant="secondary" @click="clearFilters">Clear All Filters</BaseButton>
      </template>
    </EmptyState>

    <!-- Trials Table -->
    <div v-else class="space-y-4">
      <!-- Batch Actions -->
      <div class="flex justify-between items-center">
        <span class="text-sm text-content-muted">
          {{ totalTrials }} trial{{ totalTrials !== 1 ? 's' : '' }}
        </span>
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
        @retry="confirmRetryTrial"
        @download="openDownloadModal"
        @cancel="confirmCancelTrial"
        @view-results="viewTrialResults"
        @view-schema="viewTrialSchema"
        @view-prompt="viewTrialPrompt"
      />

      <!-- Floating Batch Toolbar -->
      <BatchActionBar
        :count="selectedTrials.length"
        count-label="trial"
        @clear="selectedTrials = []"
      >
        <BaseButton variant="danger" size="sm" @click="performBatchAction('delete')">
          <Trash2 class="w-4 h-4" />
          Delete
        </BaseButton>
      </BatchActionBar>
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
      :title="confirmAction.title"
      :message="confirmAction.message"
      :confirm-text="confirmAction.confirmText"
      :confirm-variant="confirmAction.variant"
      @confirm="confirmAction.handler()"
      @cancel="isConfirmDialogOpen = false"
    />
    <TrialResults
      v-if="showTrialResultsModal"
      :is-modal="true"
      :project-id="props.projectId"
      :trial-id="selectedTrialId ?? 0"
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
    <SchemaViewModal
      v-if="showSchemaModal"
      :open="showSchemaModal"
      :schema="selectedSchema"
      :is-snapshot="schemaIsSnapshot"
      @close="showSchemaModal = false"
    />
    <PromptViewModal
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

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, type PropType } from 'vue'
import { debounce } from 'perfect-debounce'
import { useToast } from '@/composables/useToast'
import { ClipboardList, SearchX, Trash2 } from '@lucide/vue'
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
import SchemaViewModal from '@/components/schemas/SchemaViewModal.vue'
import PromptViewModal from '@/components/schemas/PromptViewModal.vue'
import DownloadModal from '@/components/trials/DownloadModal.vue'
import SkeletonTable from '@/components/common/SkeletonTable.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BatchActionBar from '@/components/common/BatchActionBar.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { extractErrorMessage } from '@/utils/errors'
import type {
  DocumentListItem,
  DocumentSetSummary,
  Schema,
  Prompt,
  TrialSummary,
  TrialCreate,
} from '@/types'

interface ConfirmAction {
  title: string
  message: string
  confirmText: string
  variant: 'danger' | 'warning' | 'primary'
  handler: () => void
}

interface ConfirmConfig {
  title: string
  message: string
  confirmText?: string
  variant?: 'danger' | 'warning' | 'primary'
  handler: () => void
}

interface RenamePayload {
  id: number
  name: string
  description: string
}

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

const props = defineProps({
  projectId: { type: [String, Number] as PropType<string | number>, required: true },
})

const toast = useToast()

const documents = ref<DocumentListItem[]>([])

const schemas = ref<Schema[]>([])
const prompts = ref<Prompt[]>([])
const documentGroups = ref<DocumentSetSummary[]>([])
const trials = ref<TrialSummary[]>([])
const totalTrials = ref(0)
const limit = ref(20)
const currentPage = ref(1)
const isLoading = ref(true)
const error = ref<string | null>(null)
const isModalOpen = ref(false)
const isConfirmDialogOpen = ref(false)
// Generic confirmation dialog: { title, message, confirmText, variant, handler }
const confirmAction = ref<ConfirmAction>({
  title: '',
  message: '',
  confirmText: 'Confirm',
  variant: 'danger',
  handler: () => {},
})
const openConfirm = (config: ConfirmConfig): void => {
  confirmAction.value = { confirmText: 'Confirm', variant: 'danger', ...config }
  isConfirmDialogOpen.value = true
}
const showRenameModal = ref(false)
const editingTrial = ref<TrialSummary | null>(null)
const selectedTrials = ref<number[]>([])
const showBatchModal = ref(false)
const batchAction = ref('')
const showTrialResultsModal = ref(false)
const selectedTrialId = ref<number | null>(null)
const showSchemaModal = ref(false)
const selectedSchema = ref<Schema | null>(null)
const schemaIsSnapshot = ref(false)
const showPromptModal = ref(false)
const selectedPrompt = ref<Prompt | null>(null)
const promptIsSnapshot = ref(false)
const showDownloadModal = ref(false)
const trialToDownload = ref<TrialSummary | null>(null)
const highlightedTrialId = ref<number | null>(null)

// Handle expand-trial event from ActivityBell
const handleExpandTrial = (event: Event): void => {
  const customEvent = event as CustomEvent<{ id?: string | number }>
  const trialId = customEvent.detail?.id
  if (!trialId) return

  highlightedTrialId.value = Number(trialId)

  // Try to scroll to the trial card, retrying if it's not found yet
  const tryScrollToTrial = (attempts = 0): void => {
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

// Distinguishes "project has no trials at all" from "filters matched nothing".
const hasActiveFilters = computed(() => {
  const f = filters.value
  return !!(
    f.search ||
    f.status ||
    f.schema_id ||
    f.prompt_id ||
    f.document_set_id ||
    f.llm_model ||
    (f.has_failures !== '' && f.has_failures !== null) ||
    f.dateRange ||
    customDateFrom.value ||
    customDateTo.value
  )
})

const filters = ref<TrialFilters>({
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
  const allModels = trials.value.map((t) => t.llm_model).filter((m): m is string => Boolean(m))
  return [...new Set(allModels)]
})

// Compute date bounds for date range filter
const getDateBounds = (range: string): { date_from?: string; date_to?: string } => {
  return getDateRangeBounds(range, customDateFrom.value, customDateTo.value)
}

function clearFilters(): void {
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
function clearFilter(key: string): void {
  if (key === 'customDateRange') {
    customDateFrom.value = ''
    customDateTo.value = ''
    filters.value.dateRange = ''
  } else {
    filters.value[key] = ''
  }
  applyFilters()
}

function paramsFromFilters(): Record<string, unknown> {
  const params: Record<string, unknown> = {}
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

async function fetchTrialsPage({
  limitParam,
  offsetParam,
}: {
  limitParam: number
  offsetParam: number
}) {
  const params = { ...paramsFromFilters(), limit: limitParam, offset: offsetParam }
  const res = await trialsApi.list(props.projectId, params)
  return res.data
}

async function fetchTrials({ silent = false }: { silent?: boolean } = {}): Promise<void> {
  try {
    // Background (WS-driven) refetches run silently: toggling `isLoading` swaps
    // the table for the skeleton, which unmounts <TrialsTable> and wipes its
    // local expanded-row state — collapsing any rows the user had open when a
    // trial finished. Only user-initiated loads show the skeleton.
    if (!silent) isLoading.value = true
    const offsetParam = (currentPage.value - 1) * limit.value
    const data = await fetchTrialsPage({ limitParam: limit.value, offsetParam })
    totalTrials.value = data.total || 0
    trials.value = data.items || []
  } catch (err) {
    error.value = extractErrorMessage(err, 'Failed to load trials')
  } finally {
    if (!silent) isLoading.value = false
  }
}

// Pagination object for the DataTable (shape: { page, page_size, total, total_pages })
const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: limit.value,
  total: totalTrials.value,
  total_pages: Math.max(1, Math.ceil(totalTrials.value / limit.value)),
}))

function handlePageChange(page: number): void {
  currentPage.value = page
  fetchTrials()
}

function handlePageSizeChange(size: number): void {
  limit.value = size
  currentPage.value = 1
  fetchTrials()
}

function resetAndFetch(): void {
  currentPage.value = 1
  fetchTrials()
}

// Background variant used by the WS subscription: same page reset, but without
// flipping `isLoading` (avoids unmounting the table / collapsing expanded rows).
function backgroundResetAndFetch(): void {
  currentPage.value = 1
  fetchTrials({ silent: true })
}

function applyFilters(): void {
  resetAndFetch()
}

function toggleSelectAll(): void {
  // Toggle by id membership (not selection-count vs page-size, which mis-fired
  // for cross-page selections): if every trial on this page is selected,
  // deselect just those; otherwise add this page's ids to the selection.
  const pageIds = trials.value.map((t) => t.id)
  const allOnPageSelected =
    pageIds.length > 0 && pageIds.every((id) => selectedTrials.value.includes(id))
  if (allOnPageSelected) {
    const pageSet = new Set(pageIds)
    selectedTrials.value = selectedTrials.value.filter((id) => !pageSet.has(id))
  } else {
    const merged = new Set(selectedTrials.value)
    pageIds.forEach((id) => merged.add(id))
    selectedTrials.value = [...merged]
  }
}

// Debounced fetch for search input
const debouncedFetchTrials = debounce(() => {
  applyFilters()
}, 300)

function openCreateTrialModal(): void {
  isModalOpen.value = true
}
async function handleCreateTrial(trialData: TrialCreate): Promise<void> {
  try {
    const response = await trialsApi.create(props.projectId, trialData)
    trials.value.unshift(response.data as unknown as TrialSummary)
    totalTrials.value += 1
    isModalOpen.value = false
    toast.success('Trial created')
  } catch {
    toast.error('Failed to create trial.')
  }
}

function openRenameModal(trial: TrialSummary): void {
  editingTrial.value = trial
  showRenameModal.value = true
}
async function submitRename({ id, name, description }: RenamePayload): Promise<void> {
  try {
    await trialsApi.update(props.projectId, id, { name, description })
    const idx = trials.value.findIndex((t) => t.id === id)
    const target = idx !== -1 ? trials.value[idx] : undefined
    if (target) {
      target.name = name
      target.description = description
    }
    toast.success('Trial renamed')
    showRenameModal.value = false
  } catch {
    toast.error('Failed to rename trial')
  }
}

function toggleTrialSelection(id: number): void {
  if (selectedTrials.value.includes(id))
    selectedTrials.value = selectedTrials.value.filter((tid) => tid !== id)
  else selectedTrials.value.push(id)
}

function performBatchAction(action: string): void {
  if (selectedTrials.value.length === 0) return
  batchAction.value = action
  showBatchModal.value = true
}

// After removing rows, clamp the current page if it now sits past the last
// page (deleting the last item(s) on the last page) and refetch so the page
// isn't left empty and out of range.
function clampPageAfterRemoval(): void {
  const lastPage = Math.max(1, Math.ceil(totalTrials.value / limit.value))
  if (currentPage.value > lastPage) {
    currentPage.value = lastPage
  }
  fetchTrials()
}

function handleTrialsDeleted(deletedIds: number[] = []): void {
  if (deletedIds.length === 0) return
  const idSet = new Set(deletedIds)
  trials.value = trials.value.filter((t) => !idSet.has(t.id))
  selectedTrials.value = selectedTrials.value.filter((id) => !idSet.has(id))
  totalTrials.value = Math.max(0, totalTrials.value - deletedIds.length)
  clampPageAfterRemoval()
}

function handleBatchActionComplete(): void {
  selectedTrials.value = []
  showBatchModal.value = false
}

async function cancelTrial(trial: TrialSummary): Promise<void> {
  try {
    await trialsApi.cancel(props.projectId, trial.id)
    const idx = trials.value.findIndex((t) => t.id === trial.id)
    const target = idx !== -1 ? trials.value[idx] : undefined
    if (target) {
      target.status = 'cancelled'
      ;(target as TrialSummary & { is_cancelled?: boolean }).is_cancelled = true
    }
    toast.success('Trial cancelled')
  } catch {
    toast.error('Failed to cancel trial')
  }
}

function confirmCancelTrial(trial: TrialSummary): void {
  openConfirm({
    title: 'Cancel Trial',
    message: 'Cancel this running trial? In-progress work will be discarded and cannot be resumed.',
    confirmText: 'Cancel Trial',
    variant: 'warning',
    handler: () => {
      isConfirmDialogOpen.value = false
      cancelTrial(trial)
    },
  })
}

function confirmDeleteTrial(trial: TrialSummary): void {
  openConfirm({
    title: 'Delete Trial',
    message:
      'Deleting this trial also removes its extraction results and any evaluations based on it. This action cannot be undone.',
    confirmText: 'Delete',
    variant: 'danger',
    handler: () => deleteTrial(trial),
  })
}
async function deleteTrial(trial: TrialSummary | null): Promise<void> {
  if (!trial) return
  try {
    await trialsApi.delete(props.projectId, trial.id)
    trials.value = trials.value.filter((t) => t.id !== trial.id)
    selectedTrials.value = selectedTrials.value.filter((id) => id !== trial.id)
    totalTrials.value = Math.max(0, totalTrials.value - 1)
    clampPageAfterRemoval()
    toast.success('Trial deleted')
  } catch {
    toast.error('Failed to delete trial')
  } finally {
    isConfirmDialogOpen.value = false
  }
}

async function retryTrial(trial: TrialSummary): Promise<void> {
  try {
    // Clone server-side so the original's custom endpoint, API key, document
    // set, name and description are preserved (the client can't resend the key
    // or base URL — they're never returned in API responses).
    const response = await trialsApi.retry(props.projectId, trial.id)
    trials.value.unshift(response.data as unknown as TrialSummary)
    totalTrials.value += 1
    toast.success('Trial restarted')
  } catch (err) {
    toast.error(extractErrorMessage(err, 'Failed to restart trial'))
  }
}

function confirmRetryTrial(trial: TrialSummary): void {
  openConfirm({
    title: 'Retry Trial',
    message:
      'Start a new trial run with the same configuration? This will consume LLM credits and process all documents again.',
    confirmText: 'Retry Trial',
    variant: 'primary',
    handler: () => {
      isConfirmDialogOpen.value = false
      retryTrial(trial)
    },
  })
}
function openDownloadModal(trial: TrialSummary): void {
  trialToDownload.value = trial
  showDownloadModal.value = true
}

function viewTrialResults(trial: TrialSummary): void {
  selectedTrialId.value = trial.id
  showTrialResultsModal.value = true
}
function viewTrialSchema(trial: TrialSummary): void {
  // Prefer the frozen snapshot captured at trial run; fall back to the live
  // schema for trials created before snapshots existed.
  selectedSchema.value =
    (trial.schema_snapshot as Schema | null) ||
    schemas.value.find((s) => s.id === trial.schema_id) ||
    null
  schemaIsSnapshot.value = !!trial.schema_snapshot
  showSchemaModal.value = true
}
function viewTrialPrompt(trial: TrialSummary): void {
  selectedPrompt.value =
    (trial.prompt_snapshot as Prompt | null) ||
    prompts.value.find((p) => p.id === trial.prompt_id) ||
    null
  promptIsSnapshot.value = !!trial.prompt_snapshot
  showPromptModal.value = true
}

// WebSocket subscription for trial updates (extracted into useTrialUpdates)
const { start: startWebSocket, stop: stopWebSocket } = useTrialUpdates({
  projectId: computed(() => props.projectId),
  trials,
  resetAndFetch: backgroundResetAndFetch,
  isFirstPage: () => currentPage.value === 1,
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
  document.addEventListener('expand-trial', handleExpandTrial as EventListener)
})
onUnmounted(() => {
  stopWebSocket()
  document.removeEventListener('expand-trial', handleExpandTrial as EventListener)
})
</script>
