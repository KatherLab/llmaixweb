<template>
  <div class="evaluation-view p-4">
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
        <button
          class="px-4 py-2 rounded-md font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed dark:bg-blue-700 dark:hover:bg-blue-600 dark:disabled:bg-blue-900"
          :disabled="loadingStates.groundTruthFiles"
          @click="showUploadModal = true"
        >
          Upload Ground Truth
        </button>
        <button
          v-if="evaluations.length > 0"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-green-600 text-white hover:bg-green-700 disabled:bg-green-300 disabled:cursor-not-allowed dark:bg-green-700 dark:hover:bg-green-600 dark:disabled:bg-green-900"
          :disabled="loadingStates.evaluations"
          @click="showExportModal = true"
        >
          <span class="flex items-center">
            <Download class="mr-1 h-4 w-4" />
            Export Results
          </span>
        </button>
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
            <h2 class="font-medium text-slate-900 dark:text-white">Evaluation Dashboard</h2>
            <div class="flex gap-2">
              <button
                class="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-md text-sm hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:cursor-not-allowed"
                :disabled="!canStartEvaluation"
                @click="showTrialSelectorWithValidation"
              >
                Evaluate Trial
              </button>
              <button
                v-if="selectedGroundTruth && !selectedGroundTruth.field_mappings?.length"
                class="px-3 py-1.5 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 rounded-md text-sm hover:bg-yellow-100 dark:hover:bg-yellow-900/30 transition-colors"
                @click="previewGroundTruth"
              >
                Preview & Configure
              </button>
            </div>
          </div>

          <!-- Prerequisites Warning -->
          <div
            v-if="!canStartEvaluation"
            class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md"
          >
            <div class="flex">
              <AlertTriangle class="h-5 w-5 text-yellow-400 flex-shrink-0" />
              <div class="ml-3">
                <h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                  Setup Required
                </h3>
                <p class="mt-1 text-sm text-yellow-700 dark:text-yellow-400">
                  {{ evaluationPrerequisiteMessage }}
                </p>
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
                    {{ getDocumentCount(evaluation) }}
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
                      Complete
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
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- (Optional) Trials pagination controls just for caching models -->
          <PaginationControls
            v-if="trialsTotalPages > 1"
            v-model="trialsCurrentPage"
            :total-pages="trialsTotalPages"
            :visible-pages="trialsVisiblePages"
            :total-items="trials.total"
            :page-size="trials.limit"
          />
        </div>
      </div>
    </div>

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
      :ground-truth="selectedGroundTruth"
      @close="showTrialSelector = false"
      @evaluate="onTrialEvaluate"
    />

    <EvaluationAnalysisModal
      :open="showEvaluationAnalysis"
      :project-id="projectId"
      :evaluation="selectedEvaluation"
      @close="showEvaluationAnalysis = false"
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
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { AlertTriangle, BarChart3, ClipboardList, Download } from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { groundtruthApi } from '@/services/groundtruthApi'
import { evaluationsApi } from '@/services/evaluationsApi'
import { formatDate } from '@/utils/formatters'
import { computeVisiblePages } from '@/composables/usePagination'
import { useToast } from 'vue-toastification'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import GroundTruthUploadModal from '@/components/groundtruth/GroundTruthUploadModal.vue'
import GroundTruthManager from '@/components/groundtruth/GroundTruthManager.vue'
import TrialSelectorModal from '@/components/trials/TrialSelectorModal.vue'
import GroundTruthPreviewModal from '@/components/groundtruth/GroundTruthPreviewModal.vue'
import MetricsExportModal from '@/components/evaluation/MetricsExportModal.vue'
import EvaluationAnalysisModal from '@/components/evaluation/EvaluationAnalysisModal.vue'
import { describeHttpError } from '@/utils/errors'
import { useTableClasses } from '@/composables/useTableClasses'

const t = useTableClasses()

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
})

const toast = useToast()

// Loading states
const loadingStates = ref({
  groundTruthFiles: false,
  evaluations: false,
  trials: false,
})

// Error handling
const error = ref(null)
const lastFailedOperation = ref(null)
const isRetrying = ref(false)

// Data
const groundTruthFiles = ref([])
const selectedGroundTruth = ref(null)
const evaluations = ref([])

// Trials pagination + cache for model lookup
const trials = ref({
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
})
const trialCache = ref({}) // { [id]: TrialSummary | Trial (full) }
const pendingTrialFetches = new Set()

// Modal states
const showUploadModal = ref(false)
const showGroundTruthManager = ref(false)
const showTrialSelector = ref(false)
const showGroundTruthPreview = ref(false)
const showExportModal = ref(false)
const showEvaluationAnalysis = ref(false)

// Selected items
const selectedEvaluation = ref(null)

// Computed properties
const canStartEvaluation = computed(() => {
  return (
    selectedGroundTruth.value &&
    selectedGroundTruth.value.field_mappings?.length > 0 &&
    !loadingStates.value.groundTruthFiles &&
    !loadingStates.value.evaluations &&
    !error.value
  )
})

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
const clearError = () => {
  error.value = null
  lastFailedOperation.value = null
}

const handleApiError = (err, operation) => {
  console.error(`${operation} failed:`, err)

  const errorMessage = describeHttpError(err, operation)

  error.value = errorMessage
  toast.error(errorMessage)
}

const retryLastOperation = async () => {
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
const fetchGroundTruthFiles = async () => {
  lastFailedOperation.value = fetchGroundTruthFiles
  loadingStates.value.groundTruthFiles = true
  error.value = null

  try {
    const response = await groundtruthApi.list(props.projectId)
    groundTruthFiles.value = response.data

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

const fetchGroundTruthFilesWithRetry = async () => {
  lastFailedOperation.value = fetchGroundTruthFiles
  await fetchGroundTruthFiles()
}

// Paginated trial summaries
const fetchTrials = async (opts = {}) => {
  lastFailedOperation.value = () => fetchTrials(opts)
  loadingStates.value.trials = true

  try {
    const { limit = trials.value.limit, offset = trials.value.offset, ...filters } = opts
    const { data } = await trialsApi.list(props.projectId, { limit, offset, ...filters })

    trials.value.items = data.items || []
    trials.value.total = data.total || 0
    trials.value.limit = limit
    trials.value.offset = offset

    for (const t of trials.value.items) trialCache.value[t.id] = t

    lastFailedOperation.value = null
  } catch (err) {
    console.error('Failed to load trials:', err)
  } finally {
    loadingStates.value.trials = false
  }
}

// Page-based view over the offset-based trials pagination (for PaginationControls)
const trialsTotalPages = computed(() =>
  trials.value.limit ? Math.max(1, Math.ceil(trials.value.total / trials.value.limit)) : 1,
)
const trialsCurrentPage = computed({
  get: () => (trials.value.limit ? Math.floor(trials.value.offset / trials.value.limit) + 1 : 1),
  set: (newPage) => {
    if (loadingStates.value.trials) return
    const newOffset = (newPage - 1) * trials.value.limit
    if (newOffset === trials.value.offset) return
    fetchTrials({ offset: newOffset, limit: trials.value.limit })
  },
})
const trialsVisiblePages = computed(() =>
  computeVisiblePages(trialsCurrentPage.value, trialsTotalPages.value),
)

// Lazy fetch full trial (only if a view ever needs more than the summary)
const fetchTrialIfMissing = async (id) => {
  if (trialCache.value[id]?.results || pendingTrialFetches.has(id)) return
  pendingTrialFetches.add(id)
  try {
    const { data } = await trialsApi.get(props.projectId, id)
    trialCache.value[id] = data
  } catch {
    /* no-op */
  } finally {
    pendingTrialFetches.delete(id)
  }
}

// Utility functions for evaluation display
const getTrialModel = (trialId) => {
  const t = trialCache.value[trialId]
  if (t?.llm_model) return t.llm_model
  fetchTrialIfMissing(trialId)
  return 'Unknown'
}

const getTrialName = (trialId) => {
  const t = trialCache.value[trialId]
  if (t && typeof t.name === 'string' && t.name.trim().length > 0) {
    return t.name
  }

  // If not in the current page cache, try to warm it with the full Trial.
  // (This may update reactively; until then, show a deterministic fallback.)
  if (!t) fetchTrialIfMissing(trialId)

  return `Trial #${trialId}`
}

const getAccuracyPercentage = (evaluation) => {
  const accuracy = evaluation.overall_metrics?.accuracy || evaluation.metrics?.accuracy || 0
  return (accuracy * 100).toFixed(1)
}

const getDocumentCount = (evaluation) => {
  return evaluation.document_summaries?.length || evaluation.document_metrics?.length || 0
}

const hasEvaluationErrors = (evaluation) => {
  const documents = evaluation.document_summaries || evaluation.document_metrics || []
  return documents.some((doc) => doc.error || doc.has_error)
}

const getErrorCount = (evaluation) => {
  const documents = evaluation.document_summaries || evaluation.document_metrics || []
  return documents.filter((doc) => doc.error || doc.has_error).length
}

// Validation functions
const validateEvaluationPrerequisites = () => {
  const errors = []

  if (!selectedGroundTruth.value) {
    errors.push('Please select a ground truth file')
  }

  if (selectedGroundTruth.value && !selectedGroundTruth.value.field_mappings?.length) {
    errors.push('Ground truth file has no field mappings configured')
  }

  return errors
}

const showTrialSelectorWithValidation = () => {
  const validationErrors = validateEvaluationPrerequisites()

  if (validationErrors.length > 0) {
    error.value = `Cannot start evaluation: ${validationErrors.join(', ')}`
    toast.error(error.value)
    return
  }

  showTrialSelector.value = true
}

// Event handlers
const selectGroundTruth = async (groundTruth) => {
  try {
    error.value = null
    selectedGroundTruth.value = groundTruth
    await fetchEvaluations()
  } catch (err) {
    handleApiError(err, 'Selecting ground truth')
  }
}

const selectGroundTruthWithValidation = async (groundTruth) => {
  if (!groundTruth) {
    error.value = 'Invalid ground truth file selected'
    return
  }
  await selectGroundTruth(groundTruth)
}

const fetchEvaluations = async () => {
  if (!selectedGroundTruth.value) return

  lastFailedOperation.value = fetchEvaluations
  loadingStates.value.evaluations = true
  error.value = null

  try {
    const { data } = await evaluationsApi.list(props.projectId, {
      groundtruth_id: selectedGroundTruth.value.id,
    })

    // 1) store the evaluations
    evaluations.value = Array.isArray(data) ? data : (data?.items ?? [])

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

const onGroundTruthUploaded = async (groundTruth) => {
  try {
    groundTruthFiles.value.push(groundTruth)
    await selectGroundTruth(groundTruth)
    showUploadModal.value = false
    toast.success('Ground truth uploaded successfully')
  } catch (err) {
    handleApiError(err, 'Processing uploaded ground truth')
  }
}

const onTrialEvaluate = async (evaluationSummary) => {
  try {
    // Normalize to evaluation-like object for table
    const evaluation = {
      id: evaluationSummary.id,
      trial_id: evaluationSummary.trial_id,
      groundtruth_id: evaluationSummary.groundtruth_id,
      metrics: evaluationSummary.overall_metrics,
      overall_metrics: evaluationSummary.overall_metrics,
      field_metrics: {},
      document_metrics: evaluationSummary.document_summaries || [],
      document_summaries: evaluationSummary.document_summaries,
      created_at: evaluationSummary.created_at,
    }

    evaluations.value.push(evaluation)
    showTrialSelector.value = false
    toast.success(`Trial #${evaluationSummary.trial_id} evaluation completed successfully`)
  } catch (err) {
    handleApiError(err, 'Processing evaluation result')
  }
}

const onMappingConfigured = async () => {
  try {
    showGroundTruthPreview.value = false
    await fetchGroundTruthFiles()

    if (selectedGroundTruth.value) {
      const updatedGroundTruth = groundTruthFiles.value.find(
        (gt) => gt.id === selectedGroundTruth.value.id,
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
const previewGroundTruth = () => {
  if (!selectedGroundTruth.value) {
    error.value = 'No ground truth file selected'
    return
  }
  showGroundTruthPreview.value = true
}

const viewEvaluationAnalysis = (evaluation) => {
  selectedEvaluation.value = evaluation
  showEvaluationAnalysis.value = true
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
