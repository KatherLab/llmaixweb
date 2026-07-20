<template>
  <BaseModal
    :open="open"
    size="lg"
    title="Evaluate Trial"
    body-class="p-0 flex flex-col min-h-0"
    @close="handleClose"
  >
    <!-- Error Display -->
    <ErrorBanner
      v-if="error"
      :message="error"
      dismissable
      :retry-text="lastFailedOperation ? 'Retry' : ''"
      :retry-loading="isRetrying"
      class="mx-6 mt-4"
      @dismiss="clearError"
      @retry="retryLastOperation"
    >
      <h4 class="text-sm font-medium text-red-800 dark:text-red-300">Evaluation Error</h4>
      <p class="mt-1 text-sm text-red-700 dark:text-red-200">{{ error }}</p>
    </ErrorBanner>

    <div class="flex-1 overflow-y-auto p-6">
      <!-- Prerequisites Warning -->
      <Callout variant="warning" class="mb-4" title="Schema-specific field mappings required">
        <p class="mt-1">
          Each trial requires field mappings for its specific schema. Trials without mappings will
          be grayed out.
          <button class="underline hover:no-underline" @click="showMappingModal = true">
            Configure mappings
          </button>
        </p>
      </Callout>

      <!-- Loading State -->
      <div v-if="loadingStates.trials" class="text-center py-8">
        <LoadingSpinner size="medium" />
        <p class="mt-2 text-content-muted">Loading trials and checking mappings...</p>
      </div>

      <!-- No Trials State -->
      <EmptyState
        v-else-if="trials.items.length === 0"
        title="No completed trials available for evaluation"
        description="Run some trials first to evaluate them against ground truth"
      />

      <!-- Trials List -->
      <div v-else>
        <div class="mb-4">
          <h4 class="font-medium text-content mb-2">Select a trial to evaluate</h4>
          <p class="text-sm text-content-muted">
            Choose from completed trials to compare against your ground truth data.
          </p>
          <div class="mt-3 flex gap-4 text-sm">
            <span class="text-content-muted">
              Total trials: <span class="font-medium">{{ trials.total }}</span>
            </span>
            <span class="text-green-600 dark:text-green-400">
              Ready for evaluation:
              <span class="font-medium">{{
                availableTrials.filter((t) => t.hasMappings).length
              }}</span>
            </span>
            <span class="text-red-600 dark:text-red-400">
              Missing mappings:
              <span class="font-medium">{{
                availableTrials.filter((t) => !t.hasMappings).length
              }}</span>
            </span>
          </div>
        </div>

        <!-- Mapping Status Loading -->
        <div v-if="loadingStates.mappings" class="text-center py-4">
          <LoadingSpinner size="small" />
          <p class="mt-2 text-sm text-content-muted">Checking field mappings...</p>
        </div>

        <div class="space-y-3">
          <div
            v-for="trial in availableTrials"
            :key="trial.id"
            class="border rounded-card p-4 transition-colors"
            :class="{
              'border-primary bg-primary-soft cursor-pointer hover:bg-primary-soft':
                trial.hasMappings && selectedTrial?.id === trial.id,
              'border-strong cursor-pointer hover:bg-surface-muted':
                trial.hasMappings && selectedTrial?.id !== trial.id,
              'border-default bg-surface-muted cursor-not-allowed opacity-60': !trial.hasMappings,
            }"
            @click="trial.hasMappings ? selectTrial(trial) : showMappingRequiredTooltip(trial)"
          >
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <h5 class="font-medium text-content truncate" :title="trialDisplayName(trial)">
                    {{ trialDisplayName(trial) }}
                  </h5>
                  <div class="text-xs text-content-muted">ID: {{ trial.id }}</div>
                  <StatusBadge :status="trial.status" class="px-2 py-1 font-medium" />
                  <StatusBadge
                    v-if="trial.hasMappings"
                    color="blue"
                    label="✓ Mappings Ready"
                    class="px-2 py-1 font-medium"
                  />
                  <StatusBadge
                    v-else-if="trial.mappingStatus === 'loading'"
                    color="gray"
                    label="Checking..."
                    class="px-2 py-1 font-medium"
                  />
                  <StatusBadge
                    v-else
                    color="red"
                    label="⚠ No Mappings"
                    class="px-2 py-1 font-medium"
                  />
                </div>
                <div class="text-sm text-content-muted grid grid-cols-2 gap-y-1 gap-x-4">
                  <div><span class="font-medium">Model:</span> {{ trial.llm_model }}</div>
                  <div>
                    <span class="font-medium">Schema:</span>
                    {{ getSchemaName(trial.schema_id) }}
                  </div>
                  <div><span class="font-medium">Documents:</span> {{ trial.documents_count }}</div>
                  <div><span class="font-medium">Results:</span> {{ trial.results_count }}</div>
                  <div>
                    <span class="font-medium">Created:</span>
                    {{ formatDate(trial.created_at) }}
                  </div>
                  <div>
                    <span class="font-medium">Last result:</span>
                    {{ trial.last_result_at ? formatDate(trial.last_result_at) : '—' }}
                  </div>
                  <div
                    v-if="trial.has_failures !== null && trial.has_failures !== undefined"
                    class="col-span-2"
                  >
                    <StatusBadge v-if="trial.has_failures" color="red" class="font-medium">
                      Errors: {{ trial.error_count || 0 }}
                    </StatusBadge>
                    <StatusBadge v-else color="green" label="No Errors" class="font-medium" />
                  </div>
                </div>
                <div
                  v-if="!trial.hasMappings && trial.mappingStatus !== 'loading'"
                  class="mt-2 text-xs text-red-600 dark:text-red-400"
                >
                  Configure field mappings for "{{ getSchemaName(trial.schema_id) }}" schema to
                  enable evaluation
                </div>
              </div>
              <div class="flex flex-col items-end gap-2">
                <div
                  v-if="isAlreadyEvaluated(trial)"
                  class="text-xs text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-2 py-1 rounded-card"
                >
                  Already evaluated
                </div>
                <div class="text-xs text-content-muted">{{ trial.results_count }} results</div>
              </div>
            </div>
          </div>

          <!-- Pagination -->
          <PaginationControls
            v-if="totalPages > 1"
            :model-value="trials.page"
            :total-pages="totalPages"
            :visible-pages="visiblePages"
            :total-items="trials.total"
            :page-size="trials.limit"
            item-label="trials"
            class="-mx-4 sm:-mx-0 rounded-none border-t border-default sm:rounded-card mt-2"
            @update:model-value="goToPage"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <BaseButton variant="secondary" type="button" @click="handleClose">Cancel</BaseButton>
      <BaseButton
        variant="primary"
        class="shadow-sm"
        :loading="isEvaluating"
        :disabled="!canEvaluate"
        @click="evaluateTrialWithValidation"
      >
        {{
          isEvaluating
            ? 'Evaluating...'
            : selectedTrial
              ? `Evaluate ${trialDisplayName(selectedTrial)}`
              : 'Select Trial First'
        }}
      </BaseButton>
    </template>
  </BaseModal>

  <!-- Field Mapping Modal -->
  <GroundTruthPreviewModal
    :open="showMappingModal"
    :project-id="projectId"
    :ground-truth="groundTruth"
    @close="showMappingModal = false"
    @configured="onMappingConfigured"
  />

  <!-- Re-evaluation confirmation (re-evaluating creates another evaluation) -->
  <ConfirmationDialog
    :open="showReEvaluateConfirm"
    title="Trial already evaluated"
    :message="reEvaluateMessage"
    confirm-text="Create another evaluation"
    confirm-variant="primary"
    @confirm="confirmReEvaluate"
    @cancel="showReEvaluateConfirm = false"
  />
</template>

<script setup lang="ts">
import { ref, computed, watch, type PropType } from 'vue'
import { trialsApi } from '@/services/trialsApi'
import { schemasApi } from '@/services/schemasApi'
import { evaluationsApi } from '@/services/evaluationsApi'
import { groundtruthApi } from '@/services/groundtruthApi'
import { formatDate } from '@/utils/formatters'
import { trialLabel } from '@/utils/trialLabel'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import Callout from '@/components/common/Callout.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import GroundTruthPreviewModal from '@/components/groundtruth/GroundTruthPreviewModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { describeHttpError, extractErrorMessage } from '@/utils/errors'
import type { GroundTruth, Schema, TrialSummary, Evaluation } from '@/types'

interface LoadingStates {
  trials: boolean
  mappings: boolean
  evaluation: boolean
}

interface TrialsState {
  items: TrialSummary[]
  total: number
  limit: number
  page: number
}

interface AvailableTrial extends TrialSummary {
  hasMappings: boolean
  mappingStatus: 'loading' | 'loaded'
}

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: [String, Number] as PropType<string | number>,
    required: true,
  },
  groundTruth: {
    type: Object as PropType<GroundTruth>,
    required: true,
  },
})

const emit = defineEmits<{
  close: []
  evaluate: [evaluation: Evaluation]
}>()

const toast = useToast()

// Loading states
const loadingStates = ref<LoadingStates>({
  trials: false,
  mappings: false,
  evaluation: false,
})

// Paginated trials data (summaries)
const trials = ref<TrialsState>({
  items: [],
  total: 0,
  limit: 20,
  page: 1,
})

const schemas = ref<Schema[]>([])
const selectedTrial = ref<AvailableTrial | null>(null)
const existingEvaluations = ref<Evaluation[]>([])
const trialMappingStatus = ref<Record<number, boolean>>({})
const showMappingModal = ref(false)

// Error handling
const error = ref<string | null>(null)
const lastFailedOperation = ref<(() => Promise<void>) | null>(null)
const isRetrying = ref(false)

// Computed properties
const isEvaluating = computed(() => loadingStates.value.evaluation)

const canEvaluate = computed(() => {
  return (
    !!selectedTrial.value &&
    !!selectedTrial.value.hasMappings &&
    (selectedTrial.value.results_count || 0) > 0 &&
    !isEvaluating.value &&
    !loadingStates.value.trials &&
    !error.value
  )
})

// Only completed trials are shown in this selector
const availableTrials = computed<AvailableTrial[]>(() => {
  return trials.value.items
    .filter((trial) => trial.status === 'completed')
    .map((trial) => ({
      ...trial,
      hasMappings: trialMappingStatus.value[trial.id] || false,
      mappingStatus: trialMappingStatus.value[trial.id] === undefined ? 'loading' : 'loaded',
    }))
})

// Server-side pagination
const totalPages = computed(() => Math.max(1, Math.ceil(trials.value.total / trials.value.limit)))

// Compact page list with ellipses for PaginationControls
const visiblePages = computed<(number | '...')[]>(() => {
  const total = totalPages.value
  const current = trials.value.page
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | '...')[] = [1]
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  if (start > 2) pages.push('...')
  for (let p = start; p <= end; p++) pages.push(p)
  if (end < total - 1) pages.push('...')
  pages.push(total)
  return pages
})

const goToPage = async (page: number | string): Promise<void> => {
  if (page === '...' || page === trials.value.page) return
  const pageNum = Number(page)
  if (pageNum < 1 || pageNum > totalPages.value) return
  trials.value.page = pageNum
  await fetchTrials()
}

// Utility functions
const isAlreadyEvaluated = (trial: AvailableTrial): boolean => {
  return existingEvaluations.value.some((evaluation) => evaluation.trial_id === trial.id)
}

/** ISO date of the most recent existing evaluation for a trial (null if none). */
const lastEvaluationDate = (trialId: number): string | null => {
  let latest: string | null = null
  for (const evaluation of existingEvaluations.value) {
    if (evaluation.trial_id !== trialId) continue
    if (!latest || new Date(evaluation.created_at) > new Date(latest)) {
      latest = evaluation.created_at
    }
  }
  return latest
}

const getSchemaName = (schemaId: number): string => {
  const schema = schemas.value.find((s) => s.id === schemaId)
  return schema?.schema_name || `Schema ${schemaId}`
}

// Error handling functions
const clearError = (): void => {
  error.value = null
  lastFailedOperation.value = null
}

const trialDisplayName = (trial: AvailableTrial | null): string => trialLabel(trial, trial?.id)

const handleApiError = (err: unknown, operation: string): void => {
  console.error(`${operation} failed:`, err)

  const errorMessage = describeHttpError(err, operation)

  error.value = errorMessage
  toast.error(errorMessage)
}

const retryLastOperation = async (): Promise<void> => {
  if (!lastFailedOperation.value) return

  isRetrying.value = true
  error.value = null

  try {
    await lastFailedOperation.value()
    toast.success('Operation completed')
    lastFailedOperation.value = null
  } catch (err) {
    handleApiError(err, 'Retry')
  } finally {
    isRetrying.value = false
  }
}

// Data fetching functions
const fetchTrials = async (): Promise<void> => {
  lastFailedOperation.value = fetchTrials
  loadingStates.value.trials = true

  try {
    const { limit, page } = trials.value
    const offset = (page - 1) * limit
    // Filter to completed to avoid extra client-side filtering volume
    const { data } = await trialsApi.list(props.projectId, {
      limit,
      offset,
      status: 'completed',
    })

    trials.value.items = data.items || []
    trials.value.total = data.total || trials.value.items.length

    // Once a page is loaded, check mapping statuses for those trials
    await loadMappingStatusesFor(trials.value.items)

    lastFailedOperation.value = null
  } catch (err) {
    handleApiError(err, 'Loading trial data')
  } finally {
    loadingStates.value.trials = false
  }
}

// Fetch schemas and existing evaluations for this ground truth
const fetchSchemasAndEvaluations = async (): Promise<void> => {
  const [schemasResponse, evaluationsResponse] = await Promise.all([
    schemasApi.list(props.projectId),
    evaluationsApi.list(props.projectId, { groundtruth_id: props.groundTruth.id }),
  ])
  schemas.value = schemasResponse.data
  existingEvaluations.value = evaluationsResponse.data
}

const fetchData = async (): Promise<void> => {
  lastFailedOperation.value = fetchData
  error.value = null

  try {
    // Reset paging for fresh open
    trials.value.limit = 20
    trials.value.page = 1

    await Promise.all([fetchSchemasAndEvaluations(), fetchTrials()])

    lastFailedOperation.value = null
  } catch (err) {
    handleApiError(err, 'Loading trial data')
  }
}

// Mapping checks
const checkMappingStatus = async (trial: TrialSummary): Promise<boolean> => {
  try {
    const response = await groundtruthApi.getMappingStatus(
      props.projectId,
      props.groundTruth.id,
      trial.schema_id,
    )
    return response.data.has_mappings || false
  } catch (err) {
    console.error(`Failed to check mapping status for trial ${trial.id}:`, err)
    return false
  }
}

const loadMappingStatusesFor = async (trialList: TrialSummary[]): Promise<void> => {
  const completed = trialList.filter((t) => t.status === 'completed')
  if (!completed.length) return

  loadingStates.value.mappings = true
  try {
    const checks = completed.map(async (trial) => {
      const hasMapping = await checkMappingStatus(trial)
      trialMappingStatus.value[trial.id] = hasMapping
    })
    await Promise.all(checks)
  } catch (err) {
    console.error('Error loading mapping statuses:', err)
  } finally {
    loadingStates.value.mappings = false
  }
}

// Trial selection
const selectTrial = (trial: AvailableTrial): void => {
  if (trial.hasMappings) {
    selectedTrial.value = trial
    error.value = null
  }
}

const showMappingRequiredTooltip = (trial: AvailableTrial): void => {
  toast.warning(`Configure field mappings for "${getSchemaName(trial.schema_id)}" schema first`)
}

// Validation (uses summary fields)
const validateEvaluationPrerequisites = (): string[] => {
  const errors: string[] = []

  if (!selectedTrial.value) {
    errors.push('Please select a trial to evaluate')
  }

  if (selectedTrial.value && !selectedTrial.value.hasMappings) {
    errors.push(
      `${trialLabel(selectedTrial.value, selectedTrial.value.id)} requires field mappings for schema "${getSchemaName(selectedTrial.value.schema_id)}"`,
    )
  }

  if (!props.groundTruth) {
    errors.push('Ground truth file is required')
  }

  if (selectedTrial.value && (selectedTrial.value.results_count || 0) === 0) {
    errors.push('Selected trial has no results to evaluate')
  }

  return errors
}

// Re-evaluation confirmation: re-evaluating a trial is allowed but creates
// another, near-indistinguishable evaluation row — so confirm it first.
const showReEvaluateConfirm = ref(false)

const reEvaluateMessage = computed(() => {
  const trial = selectedTrial.value
  if (!trial) return ''
  const date = lastEvaluationDate(trial.id)
  const when = date ? ` on ${formatDate(date)}` : ''
  return `This trial was already evaluated${when} against this ground truth. Create another evaluation?`
})

const confirmReEvaluate = async (): Promise<void> => {
  showReEvaluateConfirm.value = false
  await runEvaluation()
}

// Evaluate
const evaluateTrialWithValidation = async (): Promise<void> => {
  const validationErrors = validateEvaluationPrerequisites()
  if (validationErrors.length > 0) {
    error.value = `Cannot evaluate trial: ${validationErrors.join(', ')}`
    toast.error(error.value)
    return
  }

  if (selectedTrial.value && isAlreadyEvaluated(selectedTrial.value)) {
    showReEvaluateConfirm.value = true
    return
  }

  await runEvaluation()
}

const runEvaluation = async (): Promise<void> => {
  lastFailedOperation.value = runEvaluation
  loadingStates.value.evaluation = true
  error.value = null

  try {
    // Re-check mapping before posting
    const mappingStatus = await checkMappingStatus(selectedTrial.value!)
    if (!mappingStatus) {
      throw new Error(
        `Field mappings for schema "${getSchemaName(selectedTrial.value!.schema_id)}" are not configured or have been removed`,
      )
    }

    const response = await trialsApi.evaluate(
      props.projectId,
      selectedTrial.value!.id,
      props.groundTruth.id,
    )

    // The evaluate endpoint returns an EvaluationSummary; the emit is typed as
    // Evaluation to match the parent (EvaluationView) which casts at the boundary.
    emit('evaluate', response.data as unknown as Evaluation)
    toast.success(`${trialDisplayName(selectedTrial.value)} evaluation completed`)
    lastFailedOperation.value = null
  } catch (err) {
    if ((err as { response?: { status?: number } })?.response?.status === 400) {
      const detail = extractErrorMessage(err)
      if (detail.includes('No field mapping found')) {
        error.value = `Field mappings missing: ${detail}`
        toast.error('Field mappings are required but not found. Please configure them first.')
      } else if (detail.includes('No results found')) {
        error.value = 'Trial has no results to evaluate. Please run the trial first.'
        toast.error(error.value)
      } else if (
        detail.includes('Document not found') ||
        detail.includes('No ground truth found')
      ) {
        error.value =
          'Data consistency issue detected. Some documents or ground truth entries are missing.'
        toast.error(error.value)
      } else {
        error.value = `Evaluation failed: ${detail}`
        toast.error(error.value)
      }
    } else {
      handleApiError(err, 'Trial evaluation')
    }
  } finally {
    loadingStates.value.evaluation = false
  }
}

// Mapping configured
const onMappingConfigured = async (): Promise<void> => {
  showMappingModal.value = false
  try {
    await loadMappingStatusesFor(trials.value.items)
    toast.success('Field mappings configured')
  } catch (err) {
    handleApiError(err, 'Refreshing mapping status')
  }
}

const handleClose = (): void => {
  emit('close')
}

// Fetch data whenever the modal opens (component stays mounted to enable the
// close transition). Immediate so the first open also fetches.
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) fetchData()
  },
  { immediate: true },
)
</script>
