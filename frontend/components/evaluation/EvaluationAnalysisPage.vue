<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between gap-4 mb-4">
      <div class="min-w-0">
        <BaseButton variant="link" size="sm" tone="gray" class="-ml-1 mb-2" @click="$emit('back')">
          <ChevronLeft class="h-4 w-4" /> Back to evaluations
        </BaseButton>
        <h1 class="text-2xl font-bold text-content truncate">
          {{ trialName || loadedTrialName || `Trial #${evaluationDetail?.trial_id}` }}
        </h1>
        <p class="text-sm text-content-subtle mt-0.5">
          <span v-if="evaluationDetail?.model || loadedTrialModel">{{
            evaluationDetail?.model || loadedTrialModel
          }}</span>
          <span v-if="groundTruthName"> · {{ groundTruthName }}</span>
          <span v-if="createdDate"> · {{ createdDate }}</span>
        </p>
      </div>
      <BaseButton variant="secondary" @click="$emit('export')">
        <Download class="h-4 w-4" />
        Export
      </BaseButton>
    </div>

    <ErrorBanner v-if="loadError" :message="loadError" />

    <div v-if="loading" class="flex justify-center py-24">
      <LoadingSpinner size="large" />
    </div>

    <div v-else-if="evaluationDetail" class="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-0">
      <!-- Left rail: metrics + field list -->
      <aside class="lg:col-span-1 space-y-4">
        <!-- Overall metrics -->
        <div class="bg-surface shadow-sm rounded-card p-4">
          <div class="flex items-baseline justify-between mb-3">
            <h2 class="text-sm font-semibold text-content-muted">Overall Metrics</h2>
            <span
              v-if="matchedDocInfo"
              class="text-[11px] text-content-subtle"
              :title="
                errorDocCount > 0
                  ? 'Accuracy is computed over matched documents only. Unmatched documents are listed in the table below.'
                  : ''
              "
            >
              {{ matchedDocInfo }}
            </span>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div v-for="m in overallMetrics" :key="m.key" class="bg-surface-muted rounded-card p-3">
              <div class="flex items-center gap-1">
                <span class="text-xs text-content-subtle">{{ m.label }}</span>
                <Tooltip :text="m.tooltip" :title="m.tooltipTitle">
                  <Info class="h-3.5 w-3.5 text-content-subtle hover:text-content-muted" />
                </Tooltip>
              </div>
              <div class="text-lg font-bold text-content mt-0.5 tabular-nums">
                {{ m.value }}
              </div>
              <div v-if="m.sub" class="text-[10px] text-content-subtle mt-0.5 truncate">
                {{ m.sub }}
              </div>
            </div>
          </div>
          <div v-if="errorDocCount > 0" class="mt-3 text-xs text-yellow-600 dark:text-yellow-400">
            {{ errorDocCount }} of {{ totalDocCount }} document(s) could not be scored (no
            ground-truth match) and are excluded from the accuracy above.
          </div>
        </div>

        <!-- Field list -->
        <div class="bg-surface shadow-sm rounded-card p-4">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-semibold text-content-muted">Fields</h2>
            <div class="flex items-center gap-3">
              <button
                class="text-xs text-content-subtle hover:text-content-muted inline-flex items-center gap-1"
                :title="fieldSort === 'accuracy' ? 'Sorted worst-first' : 'Sorted alphabetically'"
                @click="toggleFieldSort"
              >
                <ArrowDownWideNarrow class="h-3.5 w-3.5" />
                {{ fieldSort === 'accuracy' ? 'Worst first' : 'A→Z' }}
              </button>
              <button
                v-if="selectedFieldFilter"
                class="text-xs text-primary hover:underline"
                @click="selectedFieldFilter = ''"
              >
                Clear filter
              </button>
            </div>
          </div>
          <ul class="space-y-1 max-h-[420px] overflow-y-auto">
            <li
              v-for="field in fieldList"
              :key="field.name"
              :class="[
                'flex items-center justify-between gap-2 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors',
                selectedFieldFilter === field.name
                  ? 'bg-primary-soft ring-1 ring-ring'
                  : 'hover:bg-surface-muted',
              ]"
              @click="toggleFieldFilter(field.name)"
            >
              <div class="min-w-0 flex items-center gap-2">
                <component :is="field.icon" class="h-3.5 w-3.5 shrink-0" :class="field.iconColor" />
                <span class="text-content-muted truncate">{{ field.label }}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span
                  v-if="field.isCategory"
                  class="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
                  title="Categorical field — select it to view its confusion matrix"
                >
                  <Tags class="h-2.5 w-2.5" />
                  CAT
                </span>
                <span
                  v-if="field.errorCount > 0"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                  >{{ field.errorCount }}</span
                >
                <span
                  class="text-xs font-medium tabular-nums"
                  :class="accuracyColor(field.accuracy)"
                  >{{ formatMetricPercent(field.accuracy) }}</span
                >
              </div>
            </li>
            <li v-if="!fieldList.length" class="text-xs text-content-subtle italic px-2 py-1">
              No fields.
            </li>
          </ul>
        </div>
      </aside>

      <!-- Main: filters + document table -->
      <section class="lg:col-span-3 flex flex-col min-h-0">
        <!-- Filter bar -->
        <div class="bg-surface shadow-sm rounded-card p-3 mb-4 flex flex-wrap items-center gap-3">
          <SearchInput
            v-model="search"
            placeholder="Search documents..."
            class="flex-1 min-w-[200px]"
          />
          <select v-model="statusFilter" :class="selectClass">
            <option value="all">All statuses</option>
            <option value="failed">Failed</option>
            <option value="incorrect">Has wrong values</option>
            <option value="missing">Has missing fields</option>
            <option value="perfect">High (≥90%)</option>
            <option value="low">Low (&lt;50%)</option>
          </select>
          <div v-if="selectedFieldFilter" class="flex items-center gap-1">
            <!-- Without a confusion-cell selection the field filter shows
                 errors-only, so say so; with one, the confusion chip is the
                 actual doc filter and this chip just names the field. -->
            <FilterChip
              :label="
                confusionFilter
                  ? `Field: ${prettifyField(selectedFieldFilter)}`
                  : `Errors in: ${prettifyField(selectedFieldFilter)}`
              "
              color="blue"
              @remove="selectedFieldFilter = ''"
            />
          </div>
          <div v-if="confusionFilter" class="flex items-center gap-1">
            <FilterChip
              :label="confusionFilterLabel"
              color="pink"
              @remove="confusionFilter = null"
            />
          </div>
        </div>

        <!-- Per-field metrics for the selected field -->
        <div v-if="selectedFieldMetrics" class="bg-surface shadow-sm rounded-card p-4 mb-4">
          <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 class="text-sm font-semibold text-content-muted">
              Field metrics — {{ prettifyField(selectedFieldFilter) }}
            </h3>
            <span class="text-xs text-content-subtle">
              {{ selectedFieldMetrics.correct_count }}/{{ selectedFieldMetrics.total_count }}
              correct
            </span>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div
              v-for="m in selectedFieldMetricCards"
              :key="m.key"
              class="bg-surface-muted rounded-card p-2.5"
            >
              <div class="flex items-center gap-1">
                <span class="text-[11px] text-content-subtle">{{ m.label }}</span>
                <Tooltip :text="m.tooltip" :title="m.tooltipTitle">
                  <Info class="h-3 w-3 text-content-subtle hover:text-content-muted" />
                </Tooltip>
              </div>
              <div class="text-base font-bold tabular-nums" :class="accuracyColor(m.value)">
                {{ formatMetricPercent(m.value) }}
              </div>
            </div>
          </div>
          <div
            v-if="Object.keys(selectedFieldMetrics.error_distribution).length"
            class="mt-3 flex flex-wrap items-center gap-1.5"
          >
            <span class="text-xs text-content-subtle mr-1">Errors:</span>
            <span
              v-for="(count, type) in selectedFieldMetrics.error_distribution"
              :key="type"
              :title="getErrorTypeDescription(type) + ' — ' + getErrorSuggestion(type)"
              class="text-[11px] px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 cursor-help"
            >
              {{ prettifyErrorType(type) }}: {{ count }}
            </span>
          </div>
        </div>

        <!-- Confusion matrix for the selected categorical field -->
        <div v-if="confusionMatrixForField" class="bg-surface shadow-sm rounded-card p-4 mb-4">
          <h3 class="text-sm font-semibold text-content-muted mb-2">
            Confusion matrix — {{ prettifyField(selectedFieldFilter) }}
          </h3>
          <ConfusionMatrix
            :matrix="confusionMatrixForField"
            :active-filter="confusionFilter"
            @filter="onConfusionFilter"
          />
        </div>

        <!-- Document table -->
        <div class="bg-surface shadow-sm rounded-card flex-1 min-h-0 overflow-hidden">
          <DataTable
            :columns="columns"
            :items="pagedDocs"
            row-key="document_id"
            row-clickable
            :highlighted-keys="selectedDocId ? [String(selectedDocId)] : []"
            :row-id-prefix="'eval-doc'"
            empty-title="No documents match your filters"
            @row-click="openDoc"
          >
            <template #cell-document_name="{ row }">
              <span class="text-sm font-medium text-content">
                {{ row.document_name || `Document #${row.document_id}` }}
              </span>
            </template>
            <template #cell-accuracy="{ row }">
              <span class="text-sm font-medium tabular-nums" :class="accuracyColor(row.accuracy)">{{
                formatMetricPercent(row.accuracy)
              }}</span>
            </template>
            <template #cell-incorrect_fields="{ row }">
              <span class="text-sm text-content-muted">
                {{ (row.incorrect_fields?.length || 0) + (row.missing_fields?.length || 0) }}
                <span class="text-content-muted">/ {{ row.total_fields }}</span>
              </span>
            </template>
            <template #cell-status="{ row }">
              <StatusBadge :color="documentStatusColor(row)">{{
                documentStatusLabel(row)
              }}</StatusBadge>
            </template>
          </DataTable>
          <PaginationControls
            v-if="totalPages > 1"
            v-model="currentPage"
            :total-pages="totalPages"
            :visible-pages="visiblePages"
            :total-items="filteredDocs.length"
            :page-size="pageSize"
          />
        </div>
      </section>
    </div>

    <!-- Failure drawer -->
    <FailureDetailDrawer
      :open="!!selectedDocId"
      :document-id="selectedDocId"
      :document-name="selectedDocName"
      :doc-eval="selectedDocEval"
      :trial-result="selectedDocResult"
      :loading-document="loadingDocDetail"
      :loading-result="loadingDocResult"
      :document-text="selectedDocText"
      :original-file="selectedOriginalFile"
      :original-file-url="selectedOriginalFileUrl"
      :original-file-type="selectedOriginalFileType"
      :has-prev="hasPrevDoc"
      :has-next="hasNextDoc"
      :doc-position="docPositionLabel"
      :documents="filteredDocs"
      :current-doc-index="currentDocIndex"
      :field-mappings="fieldMappings"
      @close="closeDrawer"
      @prev="moveDoc(-1)"
      @next="moveDoc(1)"
      @select-doc="openDocById"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ArrowDownWideNarrow, ChevronLeft, Download, Info, Tags } from '@lucide/vue'
import { evaluationsApi } from '@/services/evaluationsApi'
import { groundtruthApi } from '@/services/groundtruthApi'
import { trialsApi } from '@/services/trialsApi'
import { documentsApi } from '@/services/documentsApi'
import { schemasApi } from '@/services/schemasApi'
import { filesApi } from '@/services/filesApi'
import { formatDate } from '@/utils/formatters'
import {
  formatMetricPercent,
  getMetricTooltip,
  getErrorTypeDescription,
  getErrorSuggestion,
} from '@/utils/metricsDefinitions'
import {
  prettifyField,
  accuracyColor,
  prettifyErrorType,
  documentStatusLabel as _documentStatusLabel,
  documentStatusColor as _documentStatusColor,
  ACCURACY_THRESHOLDS,
} from '@/utils/evaluationHelpers'
import { getTypeIcon } from '@/utils/schemaTypeIcons'
import { computeVisiblePages } from '@/composables/usePagination'
import { selectClass } from '@/utils/formStyles'
import { describeHttpError } from '@/utils/errors'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import FilterChip from '@/components/common/FilterChip.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ConfusionMatrix from './ConfusionMatrix.vue'
import FailureDetailDrawer from './FailureDetailDrawer.vue'
import type {
  EvaluationDetail,
  DocumentEvaluationDetail,
  TrialResultItem,
  FieldEvaluationSummary,
  FieldMapping,
} from '@/types'

interface Props {
  projectId: string | number
  evaluationId: string | number
  trialName?: string
  groundTruthName?: string
}

const props = withDefaults(defineProps<Props>(), {
  trialName: '',
  groundTruthName: '',
})

defineEmits<{ back: []; export: [] }>()

// ---- Shared inner types ----
/** A field-level metrics summary as found in EvaluationDetail.fields. */
type FieldMetrics = Partial<FieldEvaluationSummary> & {
  accuracy?: number | null
  precision?: number | null
  recall?: number | null
  f1_score?: number | null
  total_count?: number | null
  correct_count?: number | null
  error_count?: number | null
  error_distribution?: Record<string, number>
}

/** Confusion-matrix filter state (field is the dot-path the cell belongs to). */
interface ConfusionFilterState {
  groundTruth: string
  predicted: string
  field: string
}

/** Original file attached to a document (subset used here). */
interface OriginalFile {
  id?: number
  file_type?: string
  [key: string]: unknown
}

// ---- Top-level data ----
const evaluationDetail = ref<EvaluationDetail | null>(null)
const loading = ref(true)
const loadError = ref('')
// Trial name/model fetched in loadAll — used as a fallback for deep links
// that arrive without a ?trialName query param (e.g. a shared/bookmarked URL).
const loadedTrialName = ref('')
const loadedTrialModel = ref('')

// Field types: { dot_path: 'category' | 'string' | ... }
const fieldTypes = ref<Record<string, string>>({})
// Ground-truth field mappings keyed by schema field path — lets the failure
// drawer show which comparison method (+ threshold/tolerance) judged a field.
const fieldMappings = ref<Record<string, FieldMapping>>({})
// Trial results keyed by document_id (source of reasoning + result)
const resultMap = ref<Record<number, TrialResultItem>>({})
const resultsLoaded = ref(false)

// ---- Filters ----
const search = ref('')
const statusFilter = ref('all')
const selectedFieldFilter = ref('')
const confusionFilter = ref<ConfusionFilterState | null>(null)
// Field-list ordering: 'accuracy' (worst-first, default — surfaces problem
// fields) or 'alpha' (alphabetical).
const fieldSort = ref<'accuracy' | 'alpha'>('accuracy')

// ---- Pagination ----
const currentPage = ref(1)
const pageSize = 25

// ---- Drawer state ----
const selectedDocId = ref<number | null>(null)
const selectedDocEval = ref<DocumentEvaluationDetail | null>(null)
const selectedDocResult = ref<TrialResultItem | null>(null)
const selectedDocText = ref('')
const selectedOriginalFile = ref<OriginalFile | null>(null)
const selectedOriginalFileUrl = ref('')
const selectedOriginalFileType = ref('')
const loadingDocDetail = ref(false)
const loadingDocResult = ref(false)
let currentObjectUrl = ''

// ---- Computed: metrics ----
const overallMetrics = computed(() => {
  const m = (evaluationDetail.value?.metrics || {}) as Record<string, number | null>
  return [
    {
      key: 'accuracy',
      label: 'Accuracy',
      value: formatMetricPercent(m.accuracy),
      sub:
        m.total_fields != null && m.correct_fields != null
          ? `${m.correct_fields}/${m.total_fields} fields`
          : '',
      tooltipTitle: 'Accuracy',
      tooltip: getMetricTooltip('accuracy'),
    },
    {
      key: 'precision',
      label: 'Precision',
      value: formatMetricPercent(m.precision),
      // No "docs matched" sub here — that info belongs to the header/footnote,
      // and under the Precision tile it reads as part of the precision metric.
      sub: '',
      tooltipTitle: 'Precision',
      tooltip: getMetricTooltip('precision'),
    },
    {
      key: 'recall',
      label: 'Recall',
      value: formatMetricPercent(m.recall),
      sub: '',
      tooltipTitle: 'Recall',
      tooltip: getMetricTooltip('recall'),
    },
    {
      key: 'f1_score',
      label: 'F1',
      value: formatMetricPercent(m.f1_score),
      sub: '',
      tooltipTitle: 'F1 Score',
      tooltip: getMetricTooltip('f1_score'),
    },
  ]
})

const errorDocCount = computed(
  () => (evaluationDetail.value?.metrics?.error_document_count as number | undefined) || 0,
)
const totalDocCount = computed(
  () => (evaluationDetail.value?.metrics?.total_documents as number | undefined) || 0,
)
const matchedDocCount = computed(
  () => (evaluationDetail.value?.metrics?.matched_document_count as number | undefined) || 0,
)
// "X / Y documents matched" — surfaces that accuracy is over matched docs only.
const matchedDocInfo = computed(() => {
  if (!totalDocCount.value) return ''
  if (errorDocCount.value > 0) {
    return `${matchedDocCount.value}/${totalDocCount.value} docs matched`
  }
  return `${totalDocCount.value} doc${totalDocCount.value === 1 ? '' : 's'}`
})
const createdDate = computed(() =>
  evaluationDetail.value?.created_at ? formatDate(evaluationDetail.value.created_at) : '',
)

// ---- Computed: field list ----
const fieldList = computed(() => {
  const fields = (evaluationDetail.value?.fields || {}) as Record<string, FieldMetrics>
  const list = Object.entries(fields).map(([name, m]) => {
    const type = fieldTypes.value[name] || 'string'
    return {
      name,
      label: prettifyField(name),
      accuracy: m.accuracy ?? 0,
      errorCount:
        m.error_count ??
        (m.total_count != null && m.correct_count != null ? m.total_count - m.correct_count : 0),
      isCategory: type === 'category',
      icon: getTypeIcon(type === 'category' ? 'string' : type),
      iconColor: iconTextColor(type),
    }
  })
  if (fieldSort.value === 'accuracy') {
    // Worst accuracy first (ties broken by most errors), so problem fields
    // surface without scanning the whole list.
    list.sort((a, b) => a.accuracy - b.accuracy || b.errorCount - a.errorCount)
  } else {
    list.sort((a, b) => a.label.localeCompare(b.label))
  }
  return list
})

const toggleFieldSort = (): void => {
  fieldSort.value = fieldSort.value === 'accuracy' ? 'alpha' : 'accuracy'
}

const iconTextColor = (type: string): string => {
  const map: Record<string, string> = {
    string: 'text-green-600 dark:text-green-400',
    number: 'text-primary',
    boolean: 'text-purple-600 dark:text-purple-400',
    date: 'text-amber-600 dark:text-amber-400',
    category: 'text-purple-600 dark:text-purple-400',
    object: 'text-orange-600 dark:text-orange-400',
    array: 'text-pink-600 dark:text-pink-400',
  }
  return map[type] || 'text-content-subtle'
}

// ---- Computed: confusion matrix for the selected categorical field ----
const confusionMatrixForField = computed(() => {
  if (!selectedFieldFilter.value) return null
  const matrices = (evaluationDetail.value?.confusion_matrices || {}) as Record<
    string,
    Record<string, Record<string, number>>
  >
  return matrices[selectedFieldFilter.value] || null
})

// ---- Computed: per-field metrics for the selected field ----
const selectedFieldMetrics = computed(() => {
  if (!selectedFieldFilter.value) return null
  const fields = (evaluationDetail.value?.fields || {}) as Record<string, FieldMetrics>
  const m = fields[selectedFieldFilter.value]
  if (!m) return null
  const errorDistribution = m.error_distribution || {}
  return {
    accuracy: m.accuracy ?? 0,
    precision: m.precision,
    recall: m.recall,
    f1_score: m.f1_score,
    total_count: m.total_count ?? 0,
    correct_count: m.correct_count ?? 0,
    error_count:
      m.error_count ??
      (m.total_count != null && m.correct_count != null ? m.total_count - m.correct_count : 0),
    error_distribution: errorDistribution,
  }
})

const selectedFieldMetricCards = computed(() => {
  const m = selectedFieldMetrics.value
  if (!m) return []
  return [
    {
      key: 'accuracy',
      label: 'Accuracy',
      value: m.accuracy,
      tooltipTitle: 'Accuracy',
      tooltip: getMetricTooltip('accuracy'),
    },
    {
      key: 'precision',
      label: 'Precision',
      value: m.precision,
      tooltipTitle: 'Precision',
      tooltip: getMetricTooltip('precision'),
    },
    {
      key: 'recall',
      label: 'Recall',
      value: m.recall,
      tooltipTitle: 'Recall',
      tooltip: getMetricTooltip('recall'),
    },
    {
      key: 'f1_score',
      label: 'F1',
      value: m.f1_score,
      tooltipTitle: 'F1 Score',
      tooltip: getMetricTooltip('f1_score'),
    },
  ]
})

const confusionFilterLabel = computed(() => {
  if (!confusionFilter.value) return ''
  return `${confusionFilter.value.groundTruth} → ${confusionFilter.value.predicted}`
})

// ---- Computed: filtered + paginated documents ----
const filteredDocs = computed(() => {
  let docs = (evaluationDetail.value?.documents || []) as unknown as DocumentEvaluationDetail[]
  const q = search.value.trim().toLowerCase()
  if (q) {
    docs = docs.filter((d) =>
      (d.document_name || `Document #${d.document_id}`).toLowerCase().includes(q),
    )
  }
  if (selectedFieldFilter.value && !confusionFilter.value) {
    // Filter to documents where this field is wrong — but only when no
    // confusion-matrix cell is selected. A confusion cell is the more
    // specific filter (and may target CORRECT predictions, e.g. a green
    // diagonal cell), so it must take precedence; otherwise correct docs
    // are filtered out here before the confusion filter can match them.
    docs = docs.filter(
      (d) =>
        d.incorrect_fields?.includes(selectedFieldFilter.value) ||
        d.missing_fields?.includes(selectedFieldFilter.value),
    )
  }
  if (confusionFilter.value) {
    docs = docs.filter((d) => {
      const detail = d.field_details?.[confusionFilter.value!.field]
      if (!detail) return false
      return (
        String(detail.ground_truth_value) === confusionFilter.value!.groundTruth &&
        String(detail.predicted_value) === confusionFilter.value!.predicted
      )
    })
  }
  if (statusFilter.value !== 'all') {
    docs = docs.filter((d) => {
      switch (statusFilter.value) {
        case 'failed':
          return d.has_error
        case 'incorrect':
          return (d.incorrect_fields?.length || 0) > 0
        case 'missing':
          return (d.missing_fields?.length || 0) > 0
        case 'perfect':
          return !d.has_error && d.accuracy >= ACCURACY_THRESHOLDS.HIGH
        case 'low':
          return !d.has_error && d.accuracy < ACCURACY_THRESHOLDS.LOW
        default:
          return true
      }
    })
  }
  return docs
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredDocs.value.length / pageSize)))
const visiblePages = computed(() => computeVisiblePages(currentPage.value, totalPages.value))
const pagedDocs = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredDocs.value.slice(start, start + pageSize)
})

// reset to first page when filters change
watch([search, statusFilter, selectedFieldFilter, confusionFilter], () => {
  currentPage.value = 1
})

// ---- Drawer navigation ----
const selectedDocName = computed(() => {
  const d = filteredDocs.value.find((x) => String(x.document_id) === String(selectedDocId.value))
  return d?.document_name || ''
})

const currentDocIndex = computed(() =>
  filteredDocs.value.findIndex((x) => String(x.document_id) === String(selectedDocId.value)),
)
const hasPrevDoc = computed(() => currentDocIndex.value > 0)
const hasNextDoc = computed(
  () => currentDocIndex.value >= 0 && currentDocIndex.value < filteredDocs.value.length - 1,
)
// "x / y" position label for the drawer header (blank when no doc is open).
const docPositionLabel = computed(() => {
  if (currentDocIndex.value < 0) return ''
  return `${currentDocIndex.value + 1} / ${filteredDocs.value.length}`
})

const openDoc = (row: DocumentEvaluationDetail): void => {
  selectedDocId.value = row.document_id
  loadDocDetail(row.document_id)
}

// Rail click in the drawer — load a specific doc by id.
const openDocById = (documentId: number): void => {
  selectedDocId.value = documentId
  loadDocDetail(documentId)
}

const closeDrawer = (): void => {
  // Invalidate any in-flight loadDocDetail so it can't repopulate the drawer
  // state (or create an object URL) after close.
  docLoadSeq++
  selectedDocId.value = null
  selectedDocEval.value = null
  selectedDocResult.value = null
  selectedDocText.value = ''
  selectedOriginalFile.value = null
  selectedOriginalFileType.value = ''
  revokeObjectUrl()
}

const moveDoc = (delta: number): void => {
  const next = currentDocIndex.value + delta
  if (next < 0 || next >= filteredDocs.value.length) return
  const doc = filteredDocs.value[next]
  if (!doc) return
  selectedDocId.value = doc.document_id
  loadDocDetail(doc.document_id)
}

// ---- Data loading ----
const loadAll = async (): Promise<void> => {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await evaluationsApi.get(props.projectId, props.evaluationId)
    evaluationDetail.value = data as EvaluationDetail
    // Schema field types (for category detection / icons)
    const trial = await trialsApi.get(props.projectId, data.trial_id, { include_results: false })
    if (trial.data?.name) loadedTrialName.value = trial.data.name
    if (trial.data?.llm_model) loadedTrialModel.value = trial.data.llm_model
    if (trial.data?.schema_id) {
      try {
        const ft = await schemasApi.getFieldTypes(props.projectId, trial.data.schema_id)
        fieldTypes.value = (ft.data as Record<string, string>) || {}
      } catch {
        /* field types optional */
      }
      // Field mappings (comparison method + options per schema field) for the
      // failure drawer's per-field method chips — best-effort.
      try {
        const fm = await groundtruthApi.getMappings(
          props.projectId,
          data.groundtruth_id,
          trial.data.schema_id,
        )
        const map: Record<string, FieldMapping> = {}
        for (const m of fm.data || []) map[m.schema_field] = m
        fieldMappings.value = map
      } catch {
        /* mappings optional */
      }
    }
    // Load trial results (paginated) to build a {document_id → result} map.
    await loadAllResults(data.trial_id)
  } catch (err) {
    loadError.value = describeHttpError(err, 'Loading evaluation')
  } finally {
    loading.value = false
  }
}

const loadAllResults = async (trialId: number): Promise<void> => {
  resultMap.value = {}
  resultsLoaded.value = false
  const limit = 200
  let offset = 0
  try {
    while (true) {
      const { data } = await trialsApi.listResults(props.projectId, trialId, { limit, offset })
      for (const item of (data.items || []) as TrialResultItem[]) {
        resultMap.value[item.document_id] = item
      }
      const total = data.total || 0
      offset += limit
      if (offset >= total || !(data.items || []).length) break
    }
  } catch {
    /* reasoning is best-effort */
  } finally {
    resultsLoaded.value = true
  }
}

// Monotonic load counter: rapid prev/next in the drawer fires loadDocDetail
// again before earlier responses land; a stale response must not overwrite
// the newer document's state (or create an object URL nothing revokes).
let docLoadSeq = 0

const loadDocDetail = async (docId: number): Promise<void> => {
  const seq = ++docLoadSeq
  selectedDocEval.value = null
  selectedDocResult.value = null
  selectedDocText.value = ''
  selectedOriginalFile.value = null
  selectedOriginalFileType.value = ''
  revokeObjectUrl()

  loadingDocDetail.value = true
  loadingDocResult.value = true

  // Per-document field details (GT vs predicted)
  try {
    const { data } = await evaluationsApi.getDocument(props.projectId, props.evaluationId, docId)
    if (seq !== docLoadSeq) return // superseded by a newer selection
    selectedDocEval.value = data as DocumentEvaluationDetail
  } catch {
    if (seq !== docLoadSeq) return
    selectedDocEval.value = null
  } finally {
    if (seq === docLoadSeq) loadingDocDetail.value = false
  }

  // Trial result (result + reasoning) — from the pre-built map
  selectedDocResult.value = resultMap.value[docId] || null
  loadingDocResult.value = false

  // Document text + original file
  try {
    const { data: doc } = await documentsApi.get(props.projectId, docId)
    if (seq !== docLoadSeq) return
    selectedDocText.value = (doc.text as string) || ''
    selectedOriginalFile.value = (doc.original_file as unknown as OriginalFile) || null
    const fileType: string = (doc.original_file?.file_type as string) || ''
    if (fileType.includes('pdf')) selectedOriginalFileType.value = 'pdf'
    else if (fileType.includes('image')) selectedOriginalFileType.value = 'image'
    else selectedOriginalFileType.value = 'other'

    if (selectedOriginalFileType.value !== 'other' && doc.original_file?.id) {
      const resp = await filesApi.getContent(props.projectId, doc.original_file.id, {
        preview: true,
      })
      // Bail BEFORE creating the object URL — creating it and then dropping
      // the reference would leak one full-file blob per superseded load.
      if (seq !== docLoadSeq) return
      currentObjectUrl = window.URL.createObjectURL(resp.data as Blob)
      selectedOriginalFileUrl.value = currentObjectUrl
    }
  } catch {
    /* best-effort preview */
  }
}

const revokeObjectUrl = (): void => {
  if (currentObjectUrl) {
    window.URL.revokeObjectURL(currentObjectUrl)
    currentObjectUrl = ''
    selectedOriginalFileUrl.value = ''
  }
}

// ---- Confusion-matrix filter ----
const onConfusionFilter = ({
  groundTruth,
  predicted,
}: {
  groundTruth: string
  predicted: string
}): void => {
  confusionFilter.value = { groundTruth, predicted, field: selectedFieldFilter.value }
}

const toggleFieldFilter = (name: string): void => {
  selectedFieldFilter.value = selectedFieldFilter.value === name ? '' : name
  confusionFilter.value = null
}

// ---- Helpers ----
// DataTable slot `row` is typed as `Record<string, any>` (its generic
// constraint), so wrap the status helpers to accept the slot row and cast.
const documentStatusLabel = (row: unknown): string =>
  _documentStatusLabel(row as DocumentEvaluationDetail | null | undefined)
const documentStatusColor = (row: unknown): 'red' | 'green' | 'yellow' =>
  _documentStatusColor(row as DocumentEvaluationDetail | null | undefined)

const columns: DataTableColumn[] = [
  { key: 'document_name', label: 'Document', sortable: true },
  { key: 'accuracy', label: 'Accuracy', sortable: true, align: 'right' },
  { key: 'incorrect_fields', label: 'Wrong of Total', align: 'right' },
  { key: 'status', label: 'Status' },
]

// ---- Keyboard nav (←/→ or J/K) ----
const onKeydown = (e: KeyboardEvent): void => {
  if (!selectedDocId.value) return
  const tag = ((e.target as HTMLElement | null)?.tagName || '').toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return
  if (e.key === 'ArrowRight' || e.key === 'j') {
    e.preventDefault()
    moveDoc(1)
  } else if (e.key === 'ArrowLeft' || e.key === 'k') {
    e.preventDefault()
    moveDoc(-1)
  } else if (e.key === 'Escape') {
    closeDrawer()
  }
}

watch(
  () => props.evaluationId,
  () => {
    if (props.evaluationId) loadAll()
  },
)

onMounted(() => {
  loadAll()
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  docLoadSeq++
  revokeObjectUrl()
})
</script>
