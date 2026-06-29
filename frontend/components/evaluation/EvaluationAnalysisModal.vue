<template>
  <BaseModal :open="open" size="2xl" body-class="!p-0 flex flex-col" @close="$emit('close')">
    <template #header>
      <div>
        <h3 class="text-lg font-semibold text-slate-900">Evaluation Analysis</h3>
        <p v-if="evaluation" class="text-sm text-slate-500">
          Trial #{{ evaluation.trial_id }} • {{ formatDate(evaluation.created_at) }}
        </p>
      </div>
    </template>

    <!-- Error Documents Warning Banner -->
    <div
      v-if="errorDocuments.length > 0"
      class="mx-6 mt-5 p-4 bg-yellow-50 border border-yellow-300 rounded-lg flex items-center gap-2"
    >
      <AlertTriangle class="h-5 w-5 text-yellow-500 flex-shrink-0" />
      <span>
        {{ errorDocuments.length }} document<span v-if="errorDocuments.length > 1">s</span>
        could not be evaluated due to missing or invalid ground truth. Please review the errors in
        the "Documents" tab.
      </span>
    </div>

    <!-- Tab Navigation -->
    <div class="px-6 py-3">
      <BaseTabGroup
        v-model="activeTab"
        :tabs="
          availableTabs.map((t) => ({
            label: t.name,
            value: t.id,
            icon: t.icon,
            badge: t.badge,
          }))
        "
      >
        <template #tab="{ tab }">
          <component :is="tab.icon" class="h-4 w-4 inline" />
          {{ tab.label }}
        </template>
      </BaseTabGroup>
    </div>

    <!-- Error Display -->
    <ErrorBanner
      v-if="error"
      :message="error"
      dismissable
      retry-text="Retry"
      :retry-loading="isRetrying"
      class="mx-6 mt-5"
      @dismiss="clearError"
      @retry="retryLoad"
    >
      <h4 class="text-sm font-semibold text-red-800 dark:text-red-300">Loading Error</h4>
      <p class="mt-1 text-sm text-red-700 dark:text-red-200">{{ error }}</p>
    </ErrorBanner>

    <!-- Tab Content -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="isLoading" class="text-center py-16">
        <div class="mb-3">
          <LoadingSpinner size="medium" />
        </div>
        <span class="text-slate-500">Loading evaluation details...</span>
      </div>

      <div v-else-if="activeTab === 'overview' && evaluationDetail" class="p-6">
        <EvaluationOverview
          :evaluation-detail="evaluationDetail"
          :document-stats="documentStats"
          @view-field-errors="viewFieldErrors"
          @view-document-details="switchToDocumentsTab"
        />
      </div>

      <div v-else-if="activeTab === 'documents'" class="p-6">
        <DocumentAnalysis
          :document-evaluations="documentEvaluations"
          :document-contents="documentContents"
          :document-names="documentNames"
          :loading-documents="loadingDocuments"
          @load-document-content="loadDocumentContent"
          @view-document-details="viewIndividualDocument"
        />
      </div>

      <div v-else-if="activeTab === 'field-errors'" class="p-6">
        <FieldErrorAnalysis
          :field-errors="fieldErrors"
          :selected-field="selectedFieldName"
          @select-field="selectFieldForErrors"
        />
      </div>

      <div v-else-if="activeTab === 'document-detail' && selectedDocument" class="p-6">
        <IndividualDocumentView
          :document="selectedDocument"
          :document-content="documentContents[selectedDocument?.document_id]"
          :loading-content="loadingDocuments[selectedDocument?.document_id]"
          @load-content="loadDocumentContent"
          @back-to-documents="switchToDocumentsTab"
        />
      </div>

      <EmptyState v-else title="No data available for this view">
        <template #icon>
          <BarChart3 class="h-12 w-12 mx-auto text-slate-300" />
        </template>
      </EmptyState>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="flex-1 text-sm text-slate-500">
        {{ evaluationDetail?.document_count || 0 }} documents •
        {{ evaluationDetail ? (evaluationDetail.metrics.accuracy * 100).toFixed(1) : '0.0' }}%
        accuracy
      </div>
      <BaseButton variant="secondary" @click="$emit('close')">Close</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { AlertTriangle, BarChart3, FileText, Search } from '@lucide/vue'
import { evaluationsApi } from '@/services/evaluationsApi'
import { documentsApi } from '@/services/documentsApi'
import { formatDate } from '@/utils/formatters.js'
import { extractErrorMessage } from '@/utils/errors'

// Import sub-components
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import EvaluationOverview from '@/components/evaluation/EvaluationOverview.vue'
import DocumentAnalysis from '@/components/evaluation/DocumentAnalysis.vue'
import FieldErrorAnalysis from '@/components/evaluation/FieldErrorAnalysis.vue'
import IndividualDocumentView from '@/components/documents/IndividualDocumentView.vue'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: [String, Number],
    required: true,
  },
  evaluation: {
    type: Object,
    required: true,
  },
})

defineEmits(['close'])

// State
const activeTab = ref('overview')
const isLoading = ref(false)
const isRetrying = ref(false)
const error = ref(null)

// Data
const evaluationDetail = ref(null)
const documentEvaluations = ref([])
const documentContents = ref({})
const documentNames = ref({})
const loadingDocuments = ref({})
const fieldErrors = ref({})
const selectedFieldName = ref(null)
const selectedDocument = ref(null)

// Computed: documents with errors
const errorDocuments = computed(() => {
  return documentEvaluations.value.filter(
    (d) =>
      !!d.error ||
      d.has_error ||
      (d.accuracy === 0 && d.correct_fields === 0 && d.total_fields === 0),
  )
})

// Tab configuration
const availableTabs = computed(() => {
  const tabs = [
    {
      id: 'overview',
      name: 'Overview',
      icon: BarChart3,
      badge: evaluationDetail.value
        ? `${(evaluationDetail.value.metrics.accuracy * 100).toFixed(1)}%`
        : null,
    },
    {
      id: 'documents',
      name: 'Documents',
      icon: FileText,
      badge: documentEvaluations.value.length || null,
    },
  ]

  // Add field errors tab if there are errors
  const totalFieldErrors = getTotalFieldErrors()
  if (totalFieldErrors > 0) {
    tabs.push({
      id: 'field-errors',
      name: 'Field Errors',
      icon: AlertTriangle,
      badge: totalFieldErrors,
    })
  }

  // Add individual document tab if a document is selected
  if (selectedDocument.value) {
    tabs.push({
      id: 'document-detail',
      name: `Document #${selectedDocument.value.document_id}`,
      icon: Search,
      badge: null,
    })
  }

  return tabs
})

// Computed properties
const documentStats = computed(() => {
  if (!documentEvaluations.value.length) {
    return {
      perfect: 0,
      good: 0,
      poor: 0,
      error: 0,
      perfectPercent: 0,
      goodPercent: 0,
      poorPercent: 0,
      errorPercent: 0,
    }
  }

  const docs = documentEvaluations.value
  const error = docs.filter((d) => !!d.error || d.has_error).length
  const perfect = docs.filter((d) => !d.error && d.accuracy >= 0.9).length
  const good = docs.filter((d) => !d.error && d.accuracy >= 0.7 && d.accuracy < 0.9).length
  const poor = docs.filter((d) => !d.error && d.accuracy < 0.7).length
  const total = docs.length

  return {
    error,
    perfect,
    good,
    poor,
    perfectPercent: total > 0 ? (perfect / total) * 100 : 0,
    goodPercent: total > 0 ? (good / total) * 100 : 0,
    poorPercent: total > 0 ? (poor / total) * 100 : 0,
    errorPercent: total > 0 ? (error / total) * 100 : 0,
  }
})

// Helper functions
const getTotalFieldErrors = () => {
  return Object.values(fieldErrors.value).reduce((total, errors) => total + errors.length, 0)
}

const clearError = () => {
  error.value = null
}

const retryLoad = async () => {
  isRetrying.value = true
  error.value = null
  await fetchAllData()
  isRetrying.value = false
}

// Data fetching
const fetchAllData = async () => {
  isLoading.value = true
  error.value = null

  try {
    // Fetch evaluation details
    const evaluationResponse = await evaluationsApi.get(props.projectId, props.evaluation.id)
    evaluationDetail.value = evaluationResponse.data

    // Fetch document evaluations
    if (props.evaluation.document_metrics?.length) {
      const documentPromises = props.evaluation.document_metrics.map(async (docMetric) => {
        try {
          const response = await evaluationsApi.getDocument(
            props.projectId,
            props.evaluation.id,
            docMetric.document_id,
          )
          return response.data
        } catch (err) {
          return {
            document_id: docMetric.document_id,
            error: extractErrorMessage(err),
            accuracy: 0,
            correct_fields: 0,
            total_fields: 0,
            field_details: {},
          }
        }
      })

      documentEvaluations.value = await Promise.all(documentPromises)
    }

    // Load document names
    await loadDocumentNames()

    // Load field errors for each field
    if (evaluationDetail.value?.fields) {
      await loadFieldErrors()
    }
  } catch (err) {
    console.error('Failed to load evaluation data:', err)

    if (err.response?.status === 404) {
      error.value = 'Evaluation not found. It may have been deleted.'
    } else if (err.response?.status === 403) {
      error.value = 'You do not have permission to view this evaluation.'
    } else {
      error.value = `Failed to load evaluation data: ${extractErrorMessage(err)}`
    }
  } finally {
    isLoading.value = false
  }
}

const loadDocumentNames = async () => {
  const promises = documentEvaluations.value.map(async (docEval) => {
    try {
      const response = await documentsApi.get(props.projectId, docEval.document_id)
      const doc = response.data

      documentNames.value[docEval.document_id] = {
        name:
          doc.document_name || doc.original_file?.file_name || `Document ${docEval.document_id}`,
        original: doc.original_file?.file_name || '',
      }
    } catch (err) {
      documentNames.value[docEval.document_id] = {
        name: `Document ${docEval.document_id}`,
        original: '',
      }
    }
  })
  await Promise.all(promises)
}

const loadFieldErrors = async () => {
  const fieldNames = Object.keys(evaluationDetail.value.fields)

  const promises = fieldNames.map(async (fieldName) => {
    try {
      const response = await evaluationsApi.getErrors(props.projectId, props.evaluation.id, {
        field_name: fieldName,
        limit: 50,
      })
      fieldErrors.value[fieldName] = response.data
    } catch (err) {
      console.error(`Failed to load errors for field ${fieldName}:`, err)
      fieldErrors.value[fieldName] = []
    }
  })

  await Promise.all(promises)
}

const loadDocumentContent = async (documentId) => {
  if (documentContents.value[documentId] || loadingDocuments.value[documentId]) return

  loadingDocuments.value[documentId] = true

  try {
    const response = await documentsApi.get(props.projectId, documentId)
    documentContents.value[documentId] = response.data.text || 'No text content available'
  } catch (err) {
    console.error(`Failed to load document content for ${documentId}:`, err)
    documentContents.value[documentId] = 'Error loading document content'
  } finally {
    loadingDocuments.value[documentId] = false
  }
}

// Navigation actions
const viewFieldErrors = (fieldName) => {
  selectedFieldName.value = fieldName
  activeTab.value = 'field-errors'
}

const selectFieldForErrors = (fieldName) => {
  selectedFieldName.value = fieldName
}

const switchToDocumentsTab = () => {
  activeTab.value = 'documents'
  selectedDocument.value = null
}

const viewIndividualDocument = async (documentId) => {
  const document = documentEvaluations.value.find((d) => d.document_id === documentId)
  if (document) {
    selectedDocument.value = document
    activeTab.value = 'document-detail'

    if (!documentContents.value[documentId]) {
      await loadDocumentContent(documentId)
    }
  }
}

// Fetch data whenever the modal opens (component stays mounted to enable the
// close transition). Immediate so the first open also fetches. Resets transient
// state on close so a reopen for a different evaluation starts fresh.
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      activeTab.value = 'overview'
      selectedDocument.value = null
      selectedFieldName.value = null
      fetchAllData()
    } else {
      evaluationDetail.value = null
      documentEvaluations.value = []
      documentContents.value = {}
      documentNames.value = {}
      fieldErrors.value = {}
      selectedDocument.value = null
      selectedFieldName.value = null
      error.value = null
    }
  },
  { immediate: true },
)
</script>
