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
        :retry-text="
          lastFailedOperation
            ? isRetrying
              ? $t('evaluation.view.retrying')
              : $t('evaluation.view.retry')
            : ''
        "
        :retry-loading="isRetrying"
        @dismiss="clearError"
        @retry="retryLastOperation"
      />

      <PageHeader
        :title="$t('evaluation.view.title')"
        :subtitle="$t('evaluation.view.subtitle')"
        :sticky="false"
        class="mb-6"
      >
        <template #actions>
          <BaseButton
            variant="secondary"
            :disabled="loadingStates.groundTruthFiles"
            @click="showUploadModal = true"
          >
            <Upload class="h-4 w-4" />
            {{ $t('evaluation.view.upload_ground_truth') }}
          </BaseButton>
          <BaseButton
            v-if="evaluations.length > 0"
            variant="success"
            :disabled="loadingStates.evaluations"
            @click="showExportModal = true"
          >
            <Download class="h-4 w-4" />
            {{ $t('evaluation.view.export_results') }}
          </BaseButton>
        </template>
      </PageHeader>

      <!-- Loading States -->
      <div v-if="loadingStates.groundTruthFiles" class="text-center py-8">
        <LoadingSpinner size="medium" />
        <p class="mt-2 text-content-subtle">{{ $t('evaluation.view.loading_ground_truth') }}</p>
      </div>

      <!-- No ground truth files yet -->
      <EmptyState
        v-else-if="groundTruthFiles.length === 0"
        :title="$t('evaluation.view.empty_gt_title')"
        :description="$t('evaluation.view.empty_gt_description')"
        :action-text="$t('evaluation.view.upload_ground_truth')"
        @action="showUploadModal = true"
      >
        <template #icon>
          <ClipboardList class="h-16 w-16 mx-auto text-content-subtle" />
        </template>
      </EmptyState>

      <!-- Main evaluation interface -->
      <div v-else class="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <!-- Ground truth files panel -->
        <div class="bg-surface shadow-sm rounded-card p-4">
          <div class="flex justify-between items-center mb-3">
            <h2 class="font-medium text-content">{{ $t('evaluation.view.ground_truth_files') }}</h2>
            <button
              class="text-primary hover:text-primary-hover text-sm"
              @click="showGroundTruthManager = true"
            >
              {{ $t('evaluation.view.manage') }}
            </button>
          </div>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <div
              v-for="(gt, index) in groundTruthFiles"
              :key="gt.id"
              class="border border-default rounded-card p-3 hover:bg-surface-muted cursor-pointer transition-colors"
              :class="{
                'border-primary bg-primary-soft': selectedGroundTruth?.id === gt.id,
              }"
              @click="selectGroundTruthWithValidation(gt)"
            >
              <div class="font-medium text-sm text-content">
                {{ gt.name || $t('evaluation.view.ground_truth_number', { number: index + 1 }) }}
              </div>
              <div class="text-xs text-content-subtle">
                {{ gt.format?.toUpperCase() }} • {{ formatDate(gt.created_at) }}
              </div>
              <div
                v-if="gt.field_mappings?.length"
                class="text-xs text-green-600 dark:text-green-400 mt-1"
              >
                {{
                  $t(
                    'evaluation.view.field_mappings_configured',
                    { count: gt.field_mappings.length },
                    gt.field_mappings.length,
                  )
                }}
              </div>
              <div v-else class="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                {{ $t('evaluation.view.no_field_mappings') }}
              </div>
            </div>
          </div>
        </div>

        <!-- Trial selection and evaluation panel -->
        <div class="bg-surface shadow-sm rounded-card p-4 xl:col-span-3">
          <div v-if="!selectedGroundTruth" class="text-center py-12 text-content-subtle">
            <ClipboardList class="h-16 w-16 mx-auto text-content-subtle mb-3 block" />
            <p class="text-content-muted">{{ $t('evaluation.view.select_gt_prompt') }}</p>
          </div>
          <div v-else>
            <div class="flex justify-between items-center mb-4">
              <div class="flex items-center gap-2">
                <h2 class="font-medium text-content">{{ $t('evaluation.view.dashboard') }}</h2>
                <button
                  class="inline-flex items-center gap-1 text-xs text-content-subtle hover:text-content-muted"
                  :title="
                    showConcepts
                      ? $t('evaluation.view.hide_explainer')
                      : $t('evaluation.view.show_explainer')
                  "
                  @click="showConcepts = !showConcepts"
                >
                  <HelpCircle class="h-3.5 w-3.5" />
                  {{
                    showConcepts
                      ? $t('evaluation.view.hide_help')
                      : $t('evaluation.view.how_it_works')
                  }}
                </button>
              </div>
              <div class="flex gap-2">
                <BaseButton
                  size="sm"
                  :disabled="!canStartEvaluation"
                  @click="showTrialSelectorWithValidation"
                >
                  {{ $t('evaluation.view.evaluate_trial') }}
                </BaseButton>
                <BaseButton
                  v-if="selectedGroundTruth"
                  variant="secondary"
                  size="sm"
                  @click="previewGroundTruth"
                >
                  {{
                    hasMappings
                      ? $t('evaluation.view.edit_mappings')
                      : $t('evaluation.view.configure_mappings')
                  }}
                </BaseButton>
              </div>
            </div>

            <!-- Concepts explainer: auto-shown until mappings exist, then
                 recallable via the "How it works" link next to the heading. -->
            <Callout v-if="showConcepts" variant="info" class="mb-4 relative">
              <button
                class="absolute top-2 right-2 text-primary hover:text-primary-hover"
                :title="$t('evaluation.view.hide')"
                @click="showConcepts = false"
              >
                <X class="h-4 w-4" />
              </button>
              <h3 class="font-medium mb-1">{{ $t('evaluation.concepts.title') }}</h3>
              <dl class="space-y-1 pr-6">
                <div>
                  <dt class="inline font-semibold">
                    {{ $t('evaluation.concepts.ground_truth_term') }}
                  </dt>
                  <dd class="inline">{{ $t('evaluation.concepts.ground_truth_desc') }}</dd>
                </div>
                <div>
                  <dt class="inline font-semibold">
                    {{ $t('evaluation.concepts.field_mapping_term') }}
                  </dt>
                  <dd class="inline">{{ $t('evaluation.concepts.field_mapping_desc') }}</dd>
                </div>
                <div>
                  <dt class="inline font-semibold">
                    {{ $t('evaluation.concepts.id_field_term') }}
                  </dt>
                  <dd class="inline">{{ $t('evaluation.concepts.id_field_desc') }}</dd>
                </div>
              </dl>
            </Callout>

            <!-- Prerequisites Warning -->
            <Callout
              v-if="!canStartEvaluation"
              variant="warning"
              :title="$t('evaluation.view.setup_required')"
              class="mb-4"
            >
              <p class="mt-1">
                {{ evaluationPrerequisiteMessage }}
              </p>
              <BaseButton
                v-if="selectedGroundTruth && !hasMappings"
                variant="warning"
                size="sm"
                class="mt-2"
                @click="previewGroundTruth"
              >
                {{ $t('evaluation.view.configure_mappings') }}
              </BaseButton>
            </Callout>

            <!-- Loading evaluations -->
            <SkeletonTable v-if="loadingStates.evaluations" :columns="columns.length" :rows="4" />

            <!-- Evaluation results table -->
            <EmptyState
              v-else-if="evaluations.length === 0"
              :title="$t('evaluation.view.no_evaluations')"
            >
              <template #icon>
                <BarChart3 class="h-12 w-12 mx-auto text-content-subtle" />
              </template>
            </EmptyState>
            <div v-else class="overflow-x-auto">
              <DataTable
                :columns="columns"
                :items="pagedEvaluations"
                row-key="id"
                :pagination="tablePagination"
                :item-label="$t('evaluation.view.item_label')"
                :empty-title="$t('evaluation.view.no_evaluations')"
                @page-change="onPageChange"
                @page-size-change="onPageSizeChange"
              >
                <template #cell-trial="{ row: evaluation }">
                  <div
                    class="font-medium text-content truncate"
                    :title="getTrialName(evaluation.trial_id)"
                  >
                    {{ getTrialName(evaluation.trial_id) }}
                  </div>
                  <div class="text-xs text-content-subtle">
                    {{ $t('evaluation.list.trial_id', { id: evaluation.trial_id }) }} •
                    {{ formatDate(evaluation.created_at) }}
                  </div>
                </template>
                <template #cell-model="{ row: evaluation }">
                  <span class="text-sm text-content">
                    {{ getTrialModel(evaluation.trial_id) }}
                  </span>
                </template>
                <template #cell-accuracy="{ row: evaluation }">
                  <div class="flex items-center">
                    <div class="mr-2 text-content tabular-nums">
                      {{ getAccuracyPercentage(evaluation) }}%
                    </div>
                    <div class="w-16 bg-surface-sunken rounded-full h-2">
                      <div
                        class="h-2 rounded-full"
                        :class="accuracyBarColor(getEvaluationAccuracy(evaluation))"
                        :style="{ width: `${getAccuracyPercentage(evaluation)}%` }"
                      ></div>
                    </div>
                  </div>
                </template>
                <template #cell-documents="{ row: evaluation }">
                  <div class="text-sm text-content">
                    {{
                      $t(
                        'evaluation.list.doc_count',
                        { count: getDocumentCount(evaluation) },
                        getDocumentCount(evaluation),
                      )
                    }}
                  </div>
                  <div
                    v-if="getUnmatchedDocCount(evaluation) > 0"
                    class="text-xs text-yellow-600 dark:text-yellow-400"
                    :title="
                      $t('evaluation.list.unmatched_tooltip', {
                        count: getUnmatchedDocCount(evaluation),
                      })
                    "
                  >
                    {{ $t('evaluation.list.matched', { count: getMatchedDocCount(evaluation) }) }}
                  </div>
                </template>
                <template #cell-status="{ row: evaluation }">
                  <StatusBadge
                    v-if="hasEvaluationErrors(evaluation)"
                    color="red"
                    class="py-1 font-medium"
                  >
                    {{ $t('evaluation.list.has_errors', { count: getErrorCount(evaluation) }) }}
                  </StatusBadge>
                  <StatusBadge v-else color="green" class="py-1 font-medium">
                    {{ $t('evaluation.list.scored') }}
                  </StatusBadge>
                </template>
                <template #row-actions="{ row: evaluation }">
                  <button
                    class="text-primary hover:text-primary-hover text-sm underline"
                    @click.stop="viewEvaluationAnalysis(evaluation)"
                  >
                    {{ $t('evaluation.list.analysis') }}
                  </button>
                  <button
                    class="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 text-sm underline"
                    :title="$t('evaluation.list.delete_tooltip')"
                    @click.stop="confirmDeleteEvaluation(evaluation)"
                  >
                    {{ $t('evaluation.list.delete') }}
                  </button>
                </template>
              </DataTable>
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
      :preselected-ids="exportPreselectedIds"
      :ground-truth-name="selectedGroundTruth?.name || ''"
      @close="showExportModal = false"
    />
    <ConfirmationDialog
      :open="!!evaluationToDelete"
      :title="$t('evaluation.delete.title')"
      :message="
        $t('evaluation.delete.message', {
          trial: getTrialName(evaluationToDelete?.trial_id ?? 0),
        })
      "
      :confirm-text="$t('evaluation.delete.confirm')"
      :loading="deletingEvaluation"
      @confirm="deleteEvaluation"
      @cancel="evaluationToDelete = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { BarChart3, ClipboardList, Download, HelpCircle, Upload, X } from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { groundtruthApi } from '@/services/groundtruthApi'
import { evaluationsApi } from '@/services/evaluationsApi'
import { formatDate } from '@/utils/formatters'
import { useToast } from '@/composables/useToast'
import {
  accuracyBarColor,
  getEvaluationAccuracy,
  getEvaluationDocumentCount,
  getEvaluationDocuments,
} from '@/utils/evaluationHelpers'
import { extractErrorMessage } from '@/utils/errors'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import Callout from '@/components/common/Callout.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import SkeletonTable from '@/components/common/SkeletonTable.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import GroundTruthUploadModal from '@/components/groundtruth/GroundTruthUploadModal.vue'
import GroundTruthManager from '@/components/groundtruth/GroundTruthManager.vue'
import TrialSelectorModal from '@/components/trials/TrialSelectorModal.vue'
import GroundTruthPreviewModal from '@/components/groundtruth/GroundTruthPreviewModal.vue'
import MetricsExportModal from '@/components/evaluation/MetricsExportModal.vue'
import EvaluationAnalysisPage from '@/components/evaluation/EvaluationAnalysisPage.vue'
import { describeHttpError } from '@/utils/errors'
import { trialLabel } from '@/utils/trialLabel'
import type { GroundTruth, Evaluation, EvaluationSummary, DocumentEvaluationDetail } from '@/types'

/** Trial cache entry — either a TrialSummary (list) or full Trial (get). */
type TrialLike = {
  id: number
  name?: string | null
  project_trial_number?: number | null
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

const { t } = useI18n({ useScope: 'global' })

// Client-side pagination state for the evaluations list (the API returns all
// evaluations for the selected ground truth in one shot).
const currentPage = ref(1)
const pageSize = ref(25)

const toast = useToast()
const route = useRoute()
const router = useRouter()

// Deep-linked analysis view: ?tab=evaluation&evaluationId=42 shows the full
// failure-examiner page instead of the list. Matches the existing query-param
// sub-view pattern used for expandTrial/expandTask in ProjectDetail.
const analysisEvaluationId = computed(() => (route.query.evaluationId as string) || null)
const analysisTrialName = computed(() => (route.query.trialName as string) || '')
const analysisGroundTruthName = computed(() => (route.query.gtName as string) || '')

// When Export is opened from an evaluation's analysis page, pre-check that
// evaluation in the export modal (nothing was preselected before, which read
// as "export is broken" from that context).
const exportPreselectedIds = computed<number[]>(() =>
  analysisEvaluationId.value ? [Number(analysisEvaluationId.value)] : [],
)

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

// DataTable columns for the evaluations list. Cell content for trial, model,
// accuracy, documents and status is rendered via #cell-<key> slots; the Actions
// column is rendered via the #row-actions slot.
const columns = computed<DataTableColumn[]>(() => [
  { key: 'trial', label: t('evaluation.columns.trial') },
  { key: 'model', label: t('evaluation.columns.model') },
  { key: 'accuracy', label: t('evaluation.columns.overall_accuracy') },
  { key: 'documents', label: t('evaluation.columns.documents') },
  { key: 'status', label: t('evaluation.columns.status') },
])

// Client-side pagination of the evaluations list.
const totalEvaluationPages = computed(() =>
  Math.max(1, Math.ceil(evaluations.value.length / pageSize.value)),
)

const pagedEvaluations = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return evaluations.value.slice(start, start + pageSize.value)
})

const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: pageSize.value,
  total: evaluations.value.length,
  total_pages: totalEvaluationPages.value,
}))

const onPageChange = (page: number): void => {
  currentPage.value = page
}

const onPageSizeChange = (size: number): void => {
  pageSize.value = size
  currentPage.value = 1
}

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
    return t('evaluation.prerequisites.select_gt')
  }
  if (!selectedGroundTruth.value.field_mappings?.length) {
    return t('evaluation.prerequisites.configure_mappings')
  }
  if (error.value) {
    return t('evaluation.prerequisites.resolve_error')
  }
  return ''
})

// Flatten error (string or object) into a single message for ErrorBanner
const errorMessage = computed(() => {
  if (!error.value) return ''
  if (typeof error.value === 'string') return error.value
  const parts = [error.value.message].filter(Boolean)
  if (error.value.errors?.length) {
    parts.push(t('evaluation.errors.details', { details: error.value.errors.join('; ') }))
  }
  if (error.value.suggestions?.length) {
    parts.push(
      t('evaluation.errors.suggestions', { suggestions: error.value.suggestions.join('; ') }),
    )
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
    toast.success(t('evaluation.toast.operation_completed'))
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
      const first = groundTruthFiles.value[0]
      if (first) await selectGroundTruth(first)
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
  if (!id) return
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
  return t('evaluation.list.unknown_model')
}

const getTrialName = (trialId: number): string => {
  const tr = trialCache.value[trialId]

  // If not in the current page cache, try to warm it with the full Trial.
  // (This may update reactively; until then, show a deterministic fallback.)
  if (!tr) fetchTrialIfMissing(trialId)

  return trialLabel(tr, trialId)
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
    errors.push(t('evaluation.validation.select_gt'))
  }

  if (selectedGroundTruth.value && !selectedGroundTruth.value.field_mappings?.length) {
    errors.push(t('evaluation.validation.no_mappings'))
  }

  return errors
}

const showTrialSelectorWithValidation = (): void => {
  const validationErrors = validateEvaluationPrerequisites()

  if (validationErrors.length > 0) {
    toast.error(t('evaluation.validation.cannot_start', { errors: validationErrors.join(', ') }))
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
    error.value = t('evaluation.errors.invalid_gt')
    return
  }
  await selectGroundTruth(groundTruth)
}

const fetchEvaluations = async (): Promise<void> => {
  if (!selectedGroundTruth.value) return

  // Capture the ground truth this request is for so a slow response can't be
  // applied after the user has switched to a different ground truth (which
  // would render GT-A's evaluations under GT-B's selection).
  const requestedGtId = selectedGroundTruth.value.id

  lastFailedOperation.value = fetchEvaluations
  loadingStates.value.evaluations = true
  error.value = null

  try {
    const { data } = await evaluationsApi.list(props.projectId, {
      groundtruth_id: requestedGtId,
    })

    // Ignore a stale response if the selected ground truth changed mid-flight.
    if (selectedGroundTruth.value?.id !== requestedGtId) return

    // 1) store the evaluations
    const list = data as Evaluation[] | { items?: Evaluation[] }
    evaluations.value = (Array.isArray(list) ? list : (list.items ?? [])) as EvaluationRow[]
    // Reset to the first page whenever the list is (re)loaded.
    currentPage.value = 1

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
    toast.success(t('evaluation.toast.gt_uploaded'))
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
    toast.success(
      t('evaluation.toast.evaluation_completed', {
        trial: getTrialName(evaluationSummary.trial_id),
      }),
    )
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

    toast.success(t('evaluation.toast.mappings_configured'))
  } catch (err) {
    handleApiError(err, 'Refreshing after mapping configuration')
  }
}

// Modal actions
const previewGroundTruth = (): void => {
  if (!selectedGroundTruth.value) {
    error.value = t('evaluation.errors.no_gt_selected')
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
    toast.success(
      t('evaluation.toast.evaluation_deleted', { trial: getTrialName(evaluation.trial_id) }),
    )
  } catch (err) {
    toast.error(t('evaluation.toast.delete_failed', { error: extractErrorMessage(err) }))
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
