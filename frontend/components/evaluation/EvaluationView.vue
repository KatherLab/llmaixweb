<template>
  <div class="evaluation-view p-4">
    <!-- Deep-linked analysis page: shown when an evaluationId query param is present -->
    <EvaluationAnalysisPage
      v-if="analysisEvaluationId"
      :project-id="projectId"
      :evaluation-id="analysisEvaluationId"
      :trial-name="analysisTrialName"
      :ground-truth-name="analysisGroundTruthName"
      @back="clearAnalysisView"
      @export="showExportModal = true"
    />
    <template v-else>
      <!-- Error Banner -->
      <ErrorBanner
        v-if="error"
        :message="errorMessage"
        dismissable
        :retry-text="lastFailedOperation ? (isRetrying ? 'Retrying...' : 'Retry') : ''"
        :retry-loading="isRetrying"
        @dismiss="clearError"
        @retry="retryLastOperation"
      />

      <div class="header flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Evaluation</h1>
          <p class="text-slate-600 dark:text-slate-400">
            Compare trial results against ground truth data
          </p>
        </div>
        <div class="flex gap-2">
          <BaseButton
            variant="secondary"
            :disabled="loadingStates.groundTruthFiles"
            @click="showUploadModal = true"
          >
            <Upload class="h-4 w-4" />
            Upload Ground Truth
          </BaseButton>
          <BaseButton
            v-if="evaluations.length > 0"
            variant="success"
            :disabled="loadingStates.evaluations"
            @click="showExportModal = true"
          >
            <Download class="h-4 w-4" />
            Export Results
          </BaseButton>
        </div>
      </div>

      <!-- Loading States -->
      <div v-if="loadingStates.groundTruthFiles" class="text-center py-8">
        <LoadingSpinner size="medium" />
        <p class="mt-2 text-slate-500 dark:text-slate-400">Loading ground truth files...</p>
      </div>

      <!-- No ground truth files yet -->
      <EmptyState
        v-else-if="groundTruthFiles.length === 0"
        title="No ground truth files yet"
        description="Upload ground truth data to evaluate your trial results"
        action-text="Upload Ground Truth"
        @action="showUploadModal = true"
      >
        <template #icon>
          <ClipboardList class="h-16 w-16 mx-auto text-slate-400" />
        </template>
      </EmptyState>

      <!-- Main evaluation interface -->
      <div v-else class="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <!-- Ground truth files panel -->
        <div class="bg-white dark:bg-slate-900 shadow-sm rounded-lg p-4">
          <div class="flex justify-between items-center mb-3">
            <h2 class="font-medium text-slate-900 dark:text-white">Ground Truth Files</h2>
            <button
              class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm"
              @click="showGroundTruthManager = true"
            >
              Manage
            </button>
          </div>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="(gt, index) in groundTruthFiles"
              :key="gt.id"
              class="border dark:border-slate-700 rounded-lg p-3 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors"
              :class="{
                'border-blue-500 bg-blue-50 dark:bg-blue-900/20': selectedGroundTruth?.id === gt.id,
              }"
              @click="selectGroundTruthWithValidation(gt)"
            >
              <div class="font-medium text-sm text-slate-900 dark:text-white">
                {{ gt.name || `Ground Truth #${index + 1}` }}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400">
                {{ gt.format?.toUpperCase() }} • {{ formatDate(gt.created_at) }}
              </div>
              <div
                v-if="gt.field_mappings?.length"
                class="text-xs text-green-600 dark:text-green-400 mt-1"
              >
                {{ gt.field_mappings.length }} field mappings configured
              </div>
              <div v-else class="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                No field mappings configured
              </div>
            </div>
          </div>
        </div>

        <!-- Trial selection and evaluation panel -->
        <div class="bg-white dark:bg-slate-900 shadow-sm rounded-lg p-4 xl:col-span-3">
          <div
            v-if="!selectedGroundTruth"
            class="text-center py-12 text-slate-500 dark:text-slate-400"
          >
            <ClipboardList class="h-16 w-16 mx-auto text-slate-400 mb-3 block" />
            <p class="text-slate-700 dark:text-slate-300">
              Select a ground truth file to start evaluation
            </p>
          </div>
          <div v-else>
            <div class="flex justify-between items-center mb-4">
              <div class="flex items-center gap-2">
                <h2 class="font-medium text-slate-900 dark:text-white">Evaluation Dashboard</h2>
                <button
                  class="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                  :title="showConcepts ? 'Hide the quick explainer' : 'Show how evaluation works'"
                  @click="showConcepts = !showConcepts"
                >
                  <HelpCircle class="h-3.5 w-3.5" />
                  {{ showConcepts ? 'Hide help' : 'How it works' }}
                </button>
              </div>
              <div class="flex gap-2">
                <BaseButton
                  size="sm"
                  :disabled="!canStartEvaluation"
                  @click="showTrialSelectorWithValidation"
                >
                  Evaluate Trial
                </BaseButton>
                <BaseButton
                  v-if="selectedGroundTruth"
                  variant="secondary"
                  size="sm"
                  @click="previewGroundTruth"
                >
                  {{ hasMappings ? 'Edit mappings' : 'Configure mappings' }}
                </BaseButton>
              </div>
            </div>

            <!-- Concepts explainer: auto-shown until mappings exist, then
                 recallable via the "How it works" link next to the heading. -->
            <div
              v-if="showConcepts"
              class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md text-sm relative"
            >
              <button
                class="absolute top-2 right-2 text-blue-400 hover:text-blue-700 dark:hover:text-blue-200"
                title="Hide"
                @click="showConcepts = false"
              >
                <X class="h-4 w-4" />
              </button>
              <h3 class="font-medium text-blue-900 dark:text-blue-300 mb-1">
                How evaluation works
              </h3>
              <dl class="space-y-1 text-blue-800 dark:text-blue-300 pr-6">
                <div>
                  <dt class="inline font-semibold">Ground truth</dt>
                  <dd class="inline">
                    — a file with the correct extracted values to compare trial results against.
                  </dd>
                </div>
                <div>
                  <dt class="inline font-semibold">Field mapping</dt>
                  <dd class="inline">
                    — links each ground-truth column to the matching schema field so values can be
                    compared.
                  </dd>
                </div>
                <div>
                  <dt class="inline font-semibold">ID field</dt>
                  <dd class="inline">
                    — the column that uniquely identifies each document, so each extraction is
                    matched to its correct row.
                  </dd>
                </div>
              </dl>
            </div>

            <!-- Prerequisites Warning -->
            <div
              v-if="!canStartEvaluation"
              class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md"
            >
              <div class="flex">
                <AlertTriangle class="h-5 w-5 text-yellow-400 flex-shrink-0" />
                <div class="ml-3 flex-1">
                  <h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                    Setup Required
                  </h3>
                  <p class="mt-1 text-sm text-yellow-700 dark:text-yellow-400">
                    {{ evaluationPrerequisiteMessage }}
                  </p>
                  <BaseButton
                    v-if="selectedGroundTruth && !hasMappings"
                    variant="warning"
                    size="sm"
                    class="mt-2"
                    @click="previewGroundTruth"
                  >
                    Configure mappings
                  </BaseButton>
                </div>
              </div>
            </div>

            <!-- Loading evaluations -->
            <div v-if="loadingStates.evaluations" class="text-center py-8">
              <LoadingSpinner size="medium" />
              <p class="mt-2 text-slate-500 dark:text-slate-400">Loading evaluations...</p>
            </div>

            <!-- Evaluation results table -->
            <EmptyState
              v-else-if="evaluations.length === 0"
              title="No evaluations yet. Select a trial to evaluate."
            >
              <template #icon>
                <BarChart3 class="h-12 w-12 mx-auto text-slate-400" />
              </template>
            </EmptyState>
            <div v-else class="overflow-x-auto">
              <table :class="t.table">
                <thead :class="t.thead">
                  <tr>
                    <th :class="t.th">Trial</th>
                    <th :class="t.th">Model</th>
                    <th :class="t.th">Overall Accuracy</th>
                    <th :class="t.th">Documents</th>
                    <th :class="t.th">Status</th>
                    <th :class="t.th">Actions</th>
                  </tr>
                </thead>
                <tbody :class="t.tbody">
                  <tr v-for="evaluation in evaluations" :key="evaluation.id" :class="t.tr">
                    <td class="px-4 py-3 whitespace-nowrap text-sm">
                      <div
                        class="font-medium text-slate-900 dark:text-white truncate"
                        :title="getTrialName(evaluation.trial_id)"
                      >
                        {{ getTrialName(evaluation.trial_id) }}
                      </div>
                      <div class="text-xs text-slate-500 dark:text-slate-400">
                        ID: {{ evaluation.trial_id }} • {{ formatDate(evaluation.created_at) }}
                      </div>
                    </td>

                    <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-white">
                      {{ getTrialModel(evaluation.trial_id) }}
                    </td>
                    <td class="px-4 py-3 whitespace-nowrap text-sm">
                      <div class="flex items-center">
                        <div class="mr-2 text-slate-900 dark:text-white">
                          {{ getAccuracyPercentage(evaluation) }}%
                        </div>
                        <div class="w-16 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                          <div
                            class="bg-blue-600 h-2 rounded-full"
                            :style="{ width: `${getAccuracyPercentage(evaluation)}%` }"
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-900 dark:text-white">
                      <div>{{ getDocumentCount(evaluation) }} docs</div>
                      <div
                        v-if="getUnmatchedDocCount(evaluation) > 0"
                        class="text-xs text-yellow-600 dark:text-yellow-400"
                        :title="`${getUnmatchedDocCount(evaluation)} document(s) could not be matched to ground truth and are excluded from the accuracy.`"
                      >
                        {{ getMatchedDocCount(evaluation) }} matched
                      </div>
                    </td>
                    <td class="px-4 py-3 whitespace-nowrap text-sm">
                      <StatusBadge
                        v-if="hasEvaluationErrors(evaluation)"
                        color="red"
                        class="py-1 font-medium"
                      >
                        Has Errors ({{ getErrorCount(evaluation) }})
                      </StatusBadge>
                      <StatusBadge v-else color="green" class="py-1 font-medium">
                        Scored
                      </StatusBadge>
                    </td>
                    <td class="px-4 py-3 whitespace-nowrap text-sm">
                      <div class="flex gap-2">
                        <button
                          class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm underline"
                          @click="viewEvaluationAnalysis(evaluation)"
                        >
                          Analysis
                        </button>
                        <button
                          class="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 text-sm underline"
                          title="Delete evaluation"
                          @click="confirmDeleteEvaluation(evaluation)"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Modals -->
    <GroundTruthUploadModal
      :open="showUploadModal"
      :project-id="projectId"
      @close="showUploadModal = false"
      @uploaded="onGroundTruthUploaded"
    />
    <GroundTruthManager
      :open="showGroundTruthManager"
      :project-id="projectId"
      :ground-truth-files="groundTruthFiles"
      @close="showGroundTruthManager = false"
      @updated="fetchGroundTruthFilesWithRetry"
    />
    <TrialSelectorModal
      :open="showTrialSelector"
      :project-id="projectId"
      :ground-truth="selectedGroundTruth!"
      @close="showTrialSelector = false"
      @evaluate="onTrialEvaluate"
    />

    <GroundTruthPreviewModal
      :open="showGroundTruthPreview"
      :project-id="projectId"
      :ground-truth="selectedGroundTruth"
      @close="showGroundTruthPreview = false"
      @configured="onMappingConfigured"
    />
    <MetricsExportModal
      :open="showExportModal"
      :project-id="projectId"
      :evaluations="evaluations"
      @close="showExportModal = false"
    />
    <ConfirmationDialog
      :open="!!evaluationToDelete"
      title="Delete evaluation?"
      :message="`This removes the computed metrics for Trial #${evaluationToDelete?.trial_id}. The trial and its results are kept; you can re-evaluate anytime.`"
      confirm-text="Delete"
      :loading="deletingEvaluation"
      @confirm="deleteEvaluation"
      @cancel="evaluationToDelete = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  BarChart3,
  ClipboardList,
  Download,
  HelpCircle,
  Upload,
  X,
} from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { groundtruthApi } from '@/services/groundtruthApi'
import { evaluationsApi } from '@/services/evaluationsApi'
import { formatDate } from '@/utils/formatters'
import { useToast } from '@/composables/useToast'
import {
  getEvaluationAccuracy,
  getEvaluationDocumentCount,
  getEvaluationDocuments,
} from '@/utils/evaluationHelpers'
import { extractErrorMessage } from '@/utils/errors'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import GroundTruthUploadModal from '@/components/groundtruth/GroundTruthUploadModal.vue'
import GroundTruthManager from '@/components/groundtruth/GroundTruthManager.vue'
import TrialSelectorModal from '@/components/trials/TrialSelectorModal.vue'
import GroundTruthPreviewModal from '@/components/groundtruth/GroundTruthPreviewModal.vue'
import MetricsExportModal from '@/components/evaluation/MetricsExportModal.vue'
import EvaluationAnalysisPage from '@/components/evaluation/EvaluationAnalysisPage.vue'
import { describeHttpError } from '@/utils/errors'
import { useTableClasses } from '@/composables/useTableClasses'
import type { GroundTruth, Evaluation, EvaluationSummary, DocumentEvaluationDetail } from '@/types'

/** Trial cache entry — either a TrialSummary (list) or full Trial (get). */
type TrialLike = {
  id: number
  name?: string | null
  llm_model?: string | null
  results?: unknown
}

/** Evaluation-like row used by the table (Evaluation or the optimistic row). */
type EvaluationRow = Evaluation & {
  overall_metrics?: Record<string, unknown>
  document_summaries?: DocumentEvaluationDetail[]
}

/** Described HTTP error shape produced by describeHttpError (string or object). */
type DescribedError =
  | string
  | {
      message: string
      errors?: string[]
      suggestions?: string[]
    }

interface Props {
  projectId: string | number
}

const props = defineProps<Props>()

const t = useTableClasses()

const toast = useToast()
const route = useRoute()
const router = useRouter()

// Deep-linked analysis view: ?tab=evaluation&evaluationId=42 shows the full
// failure-examiner page instead of the list. Matches the existing query-param
// sub-view pattern used for expandTrial/expandTask in ProjectDetail.
const analysisEvaluationId = computed(() => (route.query.evaluationId as string) || null)
const analysisTrialName = computed(() => (route.query.trialName as string) || '')
const analysisGroundTruthName = computed(() => (route.query.gtName as string) || '')

const clearAnalysisView = (): void => {
  const query = { ...route.query }
  delete query.evaluationId
  delete query.trialName
  delete query.gtName
  router.replace({ query })
}

// Loading states
const loadingStates = ref({
  groundTruthFiles: false,
  evaluations: false,
  trials: false,
})

// Error handling
const error = ref<DescribedError | null>(null)
const lastFailedOperation = ref<(() => Promise<void>) | null>(null)
const isRetrying = ref(false)

// Data
const groundTruthFiles = ref<GroundTruth[]>([])
const selectedGroundTruth = ref<GroundTruth | null>(null)
const evaluations = ref<EvaluationRow[]>([])

// Trials pagination + cache for model lookup
const trials = ref<{
  items: TrialLike[]
  total: number
  limit: number
  offset: number
}>({
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
})
const trialCache = ref<Record<number, TrialLike>>({}) // { [id]: TrialSummary | Trial (full) }
const pendingTrialFetches = new Set<number>()

// Modal states
const showUploadModal = ref(false)
const showGroundTruthManager = ref(false)
const showTrialSelector = ref(false)
const showGroundTruthPreview = ref(false)
const showExportModal = ref(false)
// "How evaluation works" explainer. Auto-shown until mappings exist (see the
// watcher below), then recallable via the help link next to the heading.
const showConcepts = ref(false)

// Delete-evaluation flow
const evaluationToDelete = ref<EvaluationRow | null>(null)
const deletingEvaluation = ref(false)

// Computed properties
const canStartEvaluation = computed(() => {
  return (
    !!selectedGroundTruth.value &&
    (selectedGroundTruth.value.field_mappings?.length || 0) > 0 &&
    !loadingStates.value.groundTruthFiles &&
    !loadingStates.value.evaluations &&
    !error.value
  )
})

const hasMappings = computed(() => {
  return (selectedGroundTruth.value?.field_mappings?.length || 0) > 0
})

// Auto-show the concepts explainer while mappings are still missing (the
// onboarding state); once mappings exist, leave it to the user to recall via
// the "How it works" link. We only drive the auto-open direction so a user
// who dismisses it post-mapping isn't forced back in.
watch(
  hasMappings,
  (has) => {
    if (!has) showConcepts.value = true
  },
  { immediate: true },
)

const evaluationPrerequisiteMessage = computed(() => {
  if (!selectedGroundTruth.value) {
    return 'Please select a ground truth file first.'
  }
  if (!selectedGroundTruth.value.field_mappings?.length) {
    return 'Configure field mappings for the selected ground truth file to enable evaluation.'
  }
  if (error.value) {
    return 'Resolve the current error before starting evaluation.'
  }
  return ''
})

// Flatten error (string or object) into a single message for ErrorBanner
const errorMessage = computed(() => {
  if (!error.value) return ''
  if (typeof error.value === 'string') return error.value
  const parts = [error.value.message].filter(Boolean)
  if (error.value.errors?.length) {
    parts.push('Details: ' + error.value.errors.join('; '))
  }
  if (error.value.suggestions?.length) {
    parts.push('Suggestions: ' + error.value.suggestions.join('; '))
  }
  return parts.join(' — ')
})

// Utility functions
const clearError = (): void => {
  error.value = null
  lastFailedOperation.value = null
}

const handleApiError = (err: unknown, operation: string): void => {
  console.error(`${operation} failed:`, err)

  // Surface in the ErrorBanner (which has a retry action). Don't also fire a
  // toast — that would duplicate the message for every error in this view.
  error.value = describeHttpError(err, operation)
}

const retryLastOperation = async (): Promise<void> => {
  if (!lastFailedOperation.value) return

  isRetrying.value = true
  error.value = null

  try {
    await lastFailedOperation.value()
    toast.success('Operation completed successfully')
    lastFailedOperation.value = null
  } catch (err) {
    handleApiError(err, 'Retry')
  } finally {
    isRetrying.value = false
  }
}

// Data fetching functions
const fetchGroundTruthFiles = async (): Promise<void> => {
  lastFailedOperation.value = fetchGroundTruthFiles
  loadingStates.value.groundTruthFiles = true
  error.value = null

  try {
    const response = await groundtruthApi.list(props.projectId)
    groundTruthFiles.value = response.data as GroundTruth[]

    if (groundTruthFiles.value.length > 0 && !selectedGroundTruth.value) {
      await selectGroundTruth(groundTruthFiles.value[0])
    }

    lastFailedOperation.value = null
  } catch (err) {
    handleApiError(err, 'Loading ground truth files')
  } finally {
    loadingStates.value.groundTruthFiles = false
  }
}

const fetchGroundTruthFilesWithRetry = async (): Promise<void> => {
  lastFailedOperation.value = fetchGroundTruthFiles
  await fetchGroundTruthFiles()
}

// Paginated trial summaries
const fetchTrials = async (
  opts: { limit?: number; offset?: number; [k: string]: unknown } = {},
): Promise<void> => {
  lastFailedOperation.value = () => fetchTrials(opts)
  loadingStates.value.trials = true

  try {
    const { limit = trials.value.limit, offset = trials.value.offset, ...filters } = opts
    const { data } = await trialsApi.list(props.projectId, { limit, offset, ...filters })

    trials.value.items = (data.items || []) as TrialLike[]
    trials.value.total = data.total || 0
    trials.value.limit = limit
    trials.value.offset = offset

    for (const tr of trials.value.items) trialCache.value[tr.id] = tr

    lastFailedOperation.value = null
  } catch (err) {
    console.error('Failed to load trials:', err)
  } finally {
    loadingStates.value.trials = false
  }
}

// Lazy fetch full trial (only if a view ever needs more than the summary)
const fetchTrialIfMissing = async (id: number): Promise<void> => {
  if (trialCache.value[id]?.results || pendingTrialFetches.has(id)) return
  pendingTrialFetches.add(id)
  try {
    const { data } = await trialsApi.get(props.projectId, id)
    trialCache.value[id] = data as TrialLike
  } catch {
    /* no-op */
  } finally {
    pendingTrialFetches.delete(id)
  }
}

// Utility functions for evaluation display
const getTrialModel = (trialId: number): string => {
  const tr = trialCache.value[trialId]
  if (tr?.llm_model) return tr.llm_model
  fetchTrialIfMissing(trialId)
  return 'Unknown'
}

const getTrialName = (trialId: number): string => {
  const tr = trialCache.value[trialId]
  if (tr && typeof tr.name === 'string' && tr.name.trim().length > 0) {
    return tr.name
  }

  // If not in the current page cache, try to warm it with the full Trial.
  // (This may update reactively; until then, show a deterministic fallback.)
  if (!tr) fetchTrialIfMissing(trialId)

  return `Trial #${trialId}`
}

// Returns the bare numeric percentage (0–100, rounded to 1 decimal); callers
// append the `%` sign themselves. Using getEvaluationAccuracyPct here would
// double the `%`.
const getAccuracyPercentage = (evaluation: EvaluationRow): number =>
  Math.round(getEvaluationAccuracy(evaluation) * 1000) / 10

const getDocumentCount = (evaluation: EvaluationRow): number =>
  getEvaluationDocumentCount(evaluation)

// Matched vs total documents. Accuracy is computed over matched docs only,
// so when some documents couldn't be matched to ground truth we surface it
// in the list row — otherwise a half-unmatched trial hides behind a number
// computed only over the surviving half.
const getOverallMetrics = (evaluation: EvaluationRow): Record<string, number | null> =>
  (evaluation?.overall_metrics as Record<string, number | null>) ||
  (evaluation?.metrics as Record<string, number | null>) ||
  {}

const getMatchedDocCount = (evaluation: EvaluationRow): number => {
  const m = getOverallMetrics(evaluation)
  return m.matched_document_count ?? m.total_documents ?? getDocumentCount(evaluation)
}

const getUnmatchedDocCount = (evaluation: EvaluationRow): number => {
  const m = getOverallMetrics(evaluation)
  if (m.error_document_count != null) return m.error_document_count
  // Fall back to total - matched when the backend didn't split it out.
  if (m.total_documents != null && m.matched_document_count != null) {
    return Math.max(0, m.total_documents - m.matched_document_count)
  }
  return 0
}

const hasEvaluationErrors = (evaluation: EvaluationRow): boolean => {
  return getEvaluationDocuments(evaluation).some((doc) => !!doc.error || doc.has_error)
}

const getErrorCount = (evaluation: EvaluationRow): number => {
  return getEvaluationDocuments(evaluation).filter((doc) => !!doc.error || doc.has_error).length
}

// Validation functions
const validateEvaluationPrerequisites = (): string[] => {
  const errors: string[] = []

  if (!selectedGroundTruth.value) {
    errors.push('Please select a ground truth file')
  }

  if (selectedGroundTruth.value && !selectedGroundTruth.value.field_mappings?.length) {
    errors.push('Ground truth file has no field mappings configured')
  }

  return errors
}

const showTrialSelectorWithValidation = (): void => {
  const validationErrors = validateEvaluationPrerequisites()

  if (validationErrors.length > 0) {
    toast.error(`Cannot start evaluation: ${validationErrors.join(', ')}`)
    return
  }

  showTrialSelector.value = true
}

// Event handlers
const selectGroundTruth = async (groundTruth: GroundTruth): Promise<void> => {
  try {
    error.value = null
    selectedGroundTruth.value = groundTruth
    await fetchEvaluations()
  } catch (err) {
    handleApiError(err, 'Selecting ground truth')
  }
}

const selectGroundTruthWithValidation = async (groundTruth: GroundTruth | null): Promise<void> => {
  if (!groundTruth) {
    error.value = 'Invalid ground truth file selected'
    return
  }
  await selectGroundTruth(groundTruth)
}

const fetchEvaluations = async (): Promise<void> => {
  if (!selectedGroundTruth.value) return

  lastFailedOperation.value = fetchEvaluations
  loadingStates.value.evaluations = true
  error.value = null

  try {
    const { data } = await evaluationsApi.list(props.projectId, {
      groundtruth_id: selectedGroundTruth.value.id,
    })

    // 1) store the evaluations
    const list = data as Evaluation[] | { items?: Evaluation[] }
    evaluations.value = (Array.isArray(list) ? list : (list.items ?? [])) as EvaluationRow[]

    // 2) warm trial names/models for rows we’ll render
    for (const ev of evaluations.value) {
      if (!trialCache.value[ev.trial_id]) {
        fetchTrialIfMissing(ev.trial_id)
      }
    }

    lastFailedOperation.value = null
  } catch (err) {
    handleApiError(err, 'Loading evaluations')
  } finally {
    loadingStates.value.evaluations = false
  }
}

const onGroundTruthUploaded = async (groundTruth: GroundTruth): Promise<void> => {
  try {
    groundTruthFiles.value.push(groundTruth)
    await selectGroundTruth(groundTruth)
    showUploadModal.value = false
    toast.success('Ground truth uploaded successfully')
    // Land the user directly in the next step: configure field mappings.
    showGroundTruthPreview.value = true
  } catch (err) {
    handleApiError(err, 'Processing uploaded ground truth')
  }
}

const onTrialEvaluate = async (evaluation: Evaluation): Promise<void> => {
  try {
    // The backend's evaluate endpoint actually returns an EvaluationSummary;
    // TrialSelectorModal's emit is typed as Evaluation, so cast at the boundary.
    const evaluationSummary = evaluation as unknown as EvaluationSummary
    // Normalize to evaluation-like object for table
    const row: EvaluationRow = {
      id: evaluationSummary.id,
      trial_id: evaluationSummary.trial_id,
      groundtruth_id: evaluationSummary.groundtruth_id,
      metrics: evaluationSummary.overall_metrics,
      overall_metrics: evaluationSummary.overall_metrics,
      field_metrics: {},
      document_metrics: (evaluationSummary.document_summaries || []) as unknown as Record<
        string,
        unknown
      >[],
      document_summaries: evaluationSummary.document_summaries,
      created_at: evaluationSummary.created_at,
    }

    evaluations.value.push(row)
    showTrialSelector.value = false
    toast.success(`Trial #${evaluationSummary.trial_id} evaluation completed successfully`)
    // Surface non-blocking validation warnings (e.g. low document↔GT match
    // rate) so the researcher knows some documents could not be matched.
    const warnings = evaluationSummary.warnings
    if (Array.isArray(warnings) && warnings.length) {
      toast.warning(warnings.join(' — '), { timeout: 12000 })
    }
  } catch (err) {
    handleApiError(err, 'Processing evaluation result')
  }
}

const onMappingConfigured = async (): Promise<void> => {
  try {
    showGroundTruthPreview.value = false
    await fetchGroundTruthFiles()

    if (selectedGroundTruth.value) {
      const updatedGroundTruth = groundTruthFiles.value.find(
        (gt) => gt.id === selectedGroundTruth.value!.id,
      )
      if (updatedGroundTruth) {
        selectedGroundTruth.value = updatedGroundTruth
      }
    }

    toast.success('Field mappings configured successfully')
  } catch (err) {
    handleApiError(err, 'Refreshing after mapping configuration')
  }
}

// Modal actions
const previewGroundTruth = (): void => {
  if (!selectedGroundTruth.value) {
    error.value = 'No ground truth file selected'
    return
  }
  showGroundTruthPreview.value = true
}

const viewEvaluationAnalysis = (evaluation: EvaluationRow): void => {
  // Navigate into the deep-linked analysis page via query params.
  const query = {
    ...route.query,
    tab: 'evaluation',
    evaluationId: evaluation.id,
    trialName: getTrialName(evaluation.trial_id),
    gtName: selectedGroundTruth.value?.name || '',
  }
  router.push({ query })
}

const confirmDeleteEvaluation = (evaluation: EvaluationRow): void => {
  evaluationToDelete.value = evaluation
}

const deleteEvaluation = async (): Promise<void> => {
  const evaluation = evaluationToDelete.value
  if (!evaluation) return
  deletingEvaluation.value = true
  try {
    await evaluationsApi.delete(props.projectId, evaluation.id)
    evaluations.value = evaluations.value.filter((e) => e.id !== evaluation.id)
    evaluationToDelete.value = null
    toast.success(`Deleted evaluation for Trial #${evaluation.trial_id}`)
  } catch (err) {
    toast.error(`Failed to delete evaluation: ${extractErrorMessage(err)}`)
  } finally {
    deletingEvaluation.value = false
  }
}

// Initialize component
onMounted(async () => {
  loadingStates.value.groundTruthFiles = true
  try {
    await Promise.all([
      fetchGroundTruthFiles(),
      fetchTrials(), // just to warm the cache for model lookups
    ])
  } catch (err) {
    handleApiError(err, 'Initializing evaluation view')
  } finally {
    loadingStates.value.groundTruthFiles = false
  }
})
</script>
