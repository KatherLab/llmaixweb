<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between gap-4 mb-4">
      <div class="min-w-0">
        <button
          class="text-sm text-blue-600 dark:text-blue-400 hover:underline mb-1 flex items-center gap-1"
          @click="$emit('back')"
        >
          <ChevronLeft class="h-4 w-4" /> Back to evaluations
        </button>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white truncate">
          {{ trialName || `Trial #${evaluationDetail?.trial_id}` }}
        </h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          <span v-if="evaluationDetail?.model">{{ evaluationDetail.model }}</span>
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
        <div class="bg-white dark:bg-slate-900 shadow-sm rounded-lg p-4">
          <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">
            Overall Metrics
          </h2>
          <div class="grid grid-cols-2 gap-3">
            <div
              v-for="m in overallMetrics"
              :key="m.key"
              class="bg-slate-50 dark:bg-slate-800 rounded-lg p-3"
            >
              <div class="flex items-center gap-1">
                <span class="text-xs text-slate-500 dark:text-slate-400">{{ m.label }}</span>
                <Tooltip :text="m.tooltip">
                  <Info
                    class="h-3.5 w-3.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  />
                </Tooltip>
              </div>
              <div class="text-lg font-bold text-slate-900 dark:text-white mt-0.5">
                {{ m.value }}
              </div>
            </div>
          </div>
          <div v-if="errorDocCount > 0" class="mt-3 text-xs text-yellow-600 dark:text-yellow-400">
            {{ errorDocCount }} document(s) could not be scored (no ground-truth match).
          </div>
        </div>

        <!-- Field list -->
        <div class="bg-white dark:bg-slate-900 shadow-sm rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-200">Fields</h2>
            <button
              v-if="selectedFieldFilter"
              class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              @click="selectedFieldFilter = ''"
            >
              Clear filter
            </button>
          </div>
          <ul class="space-y-1 max-h-[420px] overflow-y-auto">
            <li
              v-for="field in fieldList"
              :key="field.name"
              :class="[
                'flex items-center justify-between gap-2 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors',
                selectedFieldFilter === field.name
                  ? 'bg-blue-50 dark:bg-blue-900/30 ring-1 ring-blue-300'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800',
              ]"
              @click="toggleFieldFilter(field.name)"
            >
              <div class="min-w-0 flex items-center gap-2">
                <component :is="field.icon" class="h-3.5 w-3.5 shrink-0" :class="field.iconColor" />
                <span class="text-slate-800 dark:text-slate-200 truncate">{{ field.label }}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span
                  v-if="field.isCategory"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
                  >cat</span
                >
                <span
                  v-if="field.errorCount > 0"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                  >{{ field.errorCount }}</span
                >
                <span class="text-xs font-medium" :class="accuracyColor(field.accuracy)">{{
                  formatMetricPercent(field.accuracy)
                }}</span>
              </div>
            </li>
            <li
              v-if="!fieldList.length"
              class="text-xs text-slate-500 dark:text-slate-400 italic px-2 py-1"
            >
              No fields.
            </li>
          </ul>
        </div>
      </aside>

      <!-- Main: filters + document table -->
      <section class="lg:col-span-3 flex flex-col min-h-0">
        <!-- Filter bar -->
        <div
          class="bg-white dark:bg-slate-900 shadow-sm rounded-lg p-3 mb-4 flex flex-wrap items-center gap-3"
        >
          <SearchInput
            v-model="search"
            placeholder="Search documents..."
            class="flex-1 min-w-[200px]"
          />
          <select
            v-model="statusFilter"
            class="border border-slate-300 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200 rounded-md px-2 py-1.5 text-sm"
          >
            <option value="all">All statuses</option>
            <option value="failed">Failed</option>
            <option value="incorrect">Has wrong values</option>
            <option value="missing">Has missing fields</option>
            <option value="perfect">Perfect (≥90%)</option>
            <option value="low">Low (&lt;50%)</option>
          </select>
          <div v-if="selectedFieldFilter" class="flex items-center gap-1">
            <FilterChip
              :label="`Field: ${prettifyField(selectedFieldFilter)}`"
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

        <!-- Confusion matrix for the selected categorical field -->
        <div
          v-if="confusionMatrixForField"
          class="bg-white dark:bg-slate-900 shadow-sm rounded-lg p-4 mb-4"
        >
          <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">
            Confusion matrix — {{ prettifyField(selectedFieldFilter) }}
          </h3>
          <ConfusionMatrix :matrix="confusionMatrixForField" @filter="onConfusionFilter" />
        </div>

        <!-- Document table -->
        <div class="bg-white dark:bg-slate-900 shadow-sm rounded-lg flex-1 min-h-0 overflow-hidden">
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
              <span class="text-sm font-medium text-slate-900 dark:text-white">
                {{ row.document_name || `Document #${row.document_id}` }}
              </span>
            </template>
            <template #cell-accuracy="{ row }">
              <span class="text-sm font-medium" :class="accuracyColor(row.accuracy)">{{
                formatMetricPercent(row.accuracy)
              }}</span>
            </template>
            <template #cell-incorrect_fields="{ row }">
              <span class="text-sm text-slate-700 dark:text-slate-300">
                {{ (row.incorrect_fields?.length || 0) + (row.missing_fields?.length || 0) }}
                <span class="text-slate-400">/ {{ row.total_fields }}</span>
              </span>
            </template>
            <template #cell-status="{ row }">
              <StatusBadge v-if="row.has_error" color="red">Error</StatusBadge>
              <StatusBadge v-else-if="row.accuracy >= 0.9" color="green">OK</StatusBadge>
              <StatusBadge v-else-if="row.accuracy < 0.5" color="red">Low</StatusBadge>
              <StatusBadge v-else color="yellow">Partial</StatusBadge>
            </template>
          </DataTable>
          <PaginationControls
            v-if="totalPages > 1"
            v-model="currentPage"
            :total-pages="totalPages"
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
      @close="closeDrawer"
      @prev="moveDoc(-1)"
      @next="moveDoc(1)"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ChevronLeft, Download, Info } from '@lucide/vue'
import { evaluationsApi } from '@/services/evaluationsApi'
import { trialsApi } from '@/services/trialsApi'
import { documentsApi } from '@/services/documentsApi'
import { schemasApi } from '@/services/schemasApi'
import { filesApi } from '@/services/filesApi'
import { formatDate } from '@/utils/formatters'
import { formatMetricPercent, getMetricTooltip } from '@/utils/metricsDefinitions'
import { getTypeIcon } from '@/utils/schemaTypeIcons'
import { describeHttpError } from '@/utils/errors'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import DataTable from '@/components/common/DataTable.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import FilterChip from '@/components/common/FilterChip.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ConfusionMatrix from './ConfusionMatrix.vue'
import FailureDetailDrawer from './FailureDetailDrawer.vue'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
  evaluationId: { type: [String, Number], required: true },
  trialName: { type: String, default: '' },
  groundTruthName: { type: String, default: '' },
})

defineEmits(['back', 'export'])

// ---- Top-level data ----
const evaluationDetail = ref(null)
const loading = ref(true)
const loadError = ref('')

// Field types: { dot_path: 'category' | 'string' | ... }
const fieldTypes = ref({})
// Trial results keyed by document_id (source of reasoning + result)
const resultMap = ref({})
const resultsLoaded = ref(false)

// ---- Filters ----
const search = ref('')
const statusFilter = ref('all')
const selectedFieldFilter = ref('')
const confusionFilter = ref(null) // { groundTruth, predicted, field }

// ---- Pagination ----
const currentPage = ref(1)
const pageSize = 25

// ---- Drawer state ----
const selectedDocId = ref(null)
const selectedDocEval = ref(null)
const selectedDocResult = ref(null)
const selectedDocText = ref('')
const selectedOriginalFile = ref(null)
const selectedOriginalFileUrl = ref('')
const selectedOriginalFileType = ref('')
const loadingDocDetail = ref(false)
const loadingDocResult = ref(false)
let currentObjectUrl = ''

// ---- Computed: metrics ----
const overallMetrics = computed(() => {
  const m = evaluationDetail.value?.metrics || {}
  return [
    {
      key: 'accuracy',
      label: 'Accuracy',
      value: formatMetricPercent(m.accuracy),
      tooltip: getMetricTooltip('accuracy'),
    },
    {
      key: 'precision',
      label: 'Precision',
      value: formatMetricPercent(m.precision),
      tooltip: getMetricTooltip('precision'),
    },
    {
      key: 'recall',
      label: 'Recall',
      value: formatMetricPercent(m.recall),
      tooltip: getMetricTooltip('recall'),
    },
    {
      key: 'f1_score',
      label: 'F1',
      value: formatMetricPercent(m.f1_score),
      tooltip: getMetricTooltip('f1_score'),
    },
  ]
})

const errorDocCount = computed(() => evaluationDetail.value?.metrics?.error_document_count || 0)
const createdDate = computed(() =>
  evaluationDetail.value?.created_at ? formatDate(evaluationDetail.value.created_at) : '',
)

// ---- Computed: field list ----
const fieldList = computed(() => {
  const fields = evaluationDetail.value?.fields || {}
  return Object.entries(fields).map(([name, m]) => {
    const type = fieldTypes.value[name] || 'string'
    return {
      name,
      label: prettifyField(name),
      accuracy: m.accuracy ?? 0,
      errorCount: m.error_count ?? m.total_count - m.correct_count,
      isCategory: type === 'category',
      icon: getTypeIcon(type === 'category' ? 'string' : type),
      iconColor: iconTextColor(type),
    }
  })
})

const iconTextColor = (type) => {
  const map = {
    string: 'text-green-600 dark:text-green-400',
    number: 'text-blue-600 dark:text-blue-400',
    boolean: 'text-purple-600 dark:text-purple-400',
    date: 'text-amber-600 dark:text-amber-400',
    category: 'text-purple-600 dark:text-purple-400',
    object: 'text-orange-600 dark:text-orange-400',
    array: 'text-pink-600 dark:text-pink-400',
  }
  return map[type] || 'text-slate-500 dark:text-slate-400'
}

// ---- Computed: confusion matrix for the selected categorical field ----
const confusionMatrixForField = computed(() => {
  if (!selectedFieldFilter.value) return null
  const matrices = evaluationDetail.value?.confusion_matrices || {}
  return matrices[selectedFieldFilter.value] || null
})

const confusionFilterLabel = computed(() => {
  if (!confusionFilter.value) return ''
  return `${confusionFilter.value.groundTruth} → ${confusionFilter.value.predicted}`
})

// ---- Computed: filtered + paginated documents ----
const filteredDocs = computed(() => {
  let docs = evaluationDetail.value?.documents || []
  const q = search.value.trim().toLowerCase()
  if (q) {
    docs = docs.filter((d) =>
      (d.document_name || `Document #${d.document_id}`).toLowerCase().includes(q),
    )
  }
  if (selectedFieldFilter.value) {
    docs = docs.filter(
      (d) =>
        d.incorrect_fields?.includes(selectedFieldFilter.value) ||
        d.missing_fields?.includes(selectedFieldFilter.value),
    )
  }
  if (confusionFilter.value) {
    docs = docs.filter((d) => {
      const detail = d.field_details?.[confusionFilter.value.field]
      if (!detail) return false
      return (
        String(detail.ground_truth_value) === confusionFilter.value.groundTruth &&
        String(detail.predicted_value) === confusionFilter.value.predicted
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
          return !d.has_error && d.accuracy >= 0.9
        case 'low':
          return !d.has_error && d.accuracy < 0.5
        default:
          return true
      }
    })
  }
  return docs
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredDocs.value.length / pageSize)))
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

const openDoc = (row) => {
  selectedDocId.value = row.document_id
  loadDocDetail(row.document_id)
}

const closeDrawer = () => {
  selectedDocId.value = null
  selectedDocEval.value = null
  selectedDocResult.value = null
  selectedDocText.value = ''
  selectedOriginalFile.value = null
  selectedOriginalFileType.value = ''
  revokeObjectUrl()
}

const moveDoc = (delta) => {
  const next = currentDocIndex.value + delta
  if (next < 0 || next >= filteredDocs.value.length) return
  const doc = filteredDocs.value[next]
  selectedDocId.value = doc.document_id
  loadDocDetail(doc.document_id)
}

// ---- Data loading ----
const loadAll = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await evaluationsApi.get(props.projectId, props.evaluationId)
    evaluationDetail.value = data
    // Schema field types (for category detection / icons)
    const trial = await trialsApi.get(props.projectId, data.trial_id, { include_results: false })
    if (trial.data?.schema_id) {
      try {
        const ft = await schemasApi.getFieldTypes(props.projectId, trial.data.schema_id)
        fieldTypes.value = ft.data || {}
      } catch {
        /* field types optional */
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

const loadAllResults = async (trialId) => {
  resultMap.value = {}
  resultsLoaded.value = false
  const limit = 200
  let offset = 0
  try {
    while (true) {
      const { data } = await trialsApi.listResults(props.projectId, trialId, { limit, offset })
      for (const item of data.items || []) {
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

const loadDocDetail = async (docId) => {
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
    selectedDocEval.value = data
  } catch {
    selectedDocEval.value = null
  } finally {
    loadingDocDetail.value = false
  }

  // Trial result (result + reasoning) — from the pre-built map
  selectedDocResult.value = resultMap.value[docId] || null
  loadingDocResult.value = false

  // Document text + original file
  try {
    const { data: doc } = await documentsApi.get(props.projectId, docId)
    selectedDocText.value = doc.text || ''
    selectedOriginalFile.value = doc.original_file || null
    const fileType = doc.original_file?.file_type || ''
    if (fileType.includes('pdf')) selectedOriginalFileType.value = 'pdf'
    else if (fileType.includes('image')) selectedOriginalFileType.value = 'image'
    else selectedOriginalFileType.value = 'other'

    if (selectedOriginalFileType.value !== 'other' && doc.original_file?.id) {
      const resp = await filesApi.getContent(props.projectId, doc.original_file.id, {
        preview: true,
      })
      currentObjectUrl = window.URL.createObjectURL(resp.data)
      selectedOriginalFileUrl.value = currentObjectUrl
    }
  } catch {
    /* best-effort preview */
  }
}

const revokeObjectUrl = () => {
  if (currentObjectUrl) {
    window.URL.revokeObjectURL(currentObjectUrl)
    currentObjectUrl = ''
    selectedOriginalFileUrl.value = ''
  }
}

// ---- Confusion-matrix filter ----
const onConfusionFilter = ({ groundTruth, predicted }) => {
  confusionFilter.value = { groundTruth, predicted, field: selectedFieldFilter.value }
}

const toggleFieldFilter = (name) => {
  selectedFieldFilter.value = selectedFieldFilter.value === name ? '' : name
  confusionFilter.value = null
}

// ---- Helpers ----
const accuracyColor = (acc) => {
  if (acc === null || acc === undefined) return 'text-slate-400'
  if (acc >= 0.9) return 'text-green-600 dark:text-green-400'
  if (acc < 0.5) return 'text-red-600 dark:text-red-400'
  return 'text-yellow-600 dark:text-yellow-400'
}

const prettifyField = (key) => {
  if (!key) return ''
  const last =
    String(key)
      .split(/[.[\]]/)
      .filter(Boolean)
      .pop() || key
  return last
    .replace(/[_-]+/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

const columns = [
  { key: 'document_name', label: 'Document', sortable: true },
  { key: 'accuracy', label: 'Accuracy', sortable: true, align: 'right' },
  { key: 'incorrect_fields', label: 'Wrong / Total', align: 'right' },
  { key: 'status', label: 'Status' },
]

// ---- Keyboard nav (J/K) ----
const onKeydown = (e) => {
  if (!selectedDocId.value) return
  const tag = (e.target?.tagName || '').toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return
  if (e.key === 'j') {
    e.preventDefault()
    moveDoc(1)
  } else if (e.key === 'k') {
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
  revokeObjectUrl()
})
</script>
