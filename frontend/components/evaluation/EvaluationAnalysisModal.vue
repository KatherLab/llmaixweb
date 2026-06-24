<template>
  <teleport to="body">
    <transition name="fade">
      <div
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/30 backdrop-blur-md"
        @click.self="$emit('close')"
      >
        <div
          class="relative bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-5xl max-h-[95vh] flex flex-col overflow-hidden"
          @click.stop
        >
          <!-- Header -->
          <div
            class="px-8 py-6 border-b flex justify-between items-center rounded-t-2xl bg-gray-50"
          >
            <div>
              <h3 class="text-2xl font-bold text-gray-900">Evaluation Analysis</h3>
              <p v-if="evaluation" class="text-sm text-gray-500">
                Trial #{{ evaluation.trial_id }} • {{ formatDate(evaluation.created_at) }}
              </p>
            </div>
            <button
              class="text-gray-400 hover:text-gray-600 transition-colors rounded-full p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close"
              @click="$emit('close')"
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <!-- Error Documents Warning Banner -->
          <div
            v-if="errorDocuments.length > 0"
            class="mx-8 mt-5 p-4 bg-yellow-50 border border-yellow-300 rounded-lg flex items-center gap-2"
          >
            <span class="text-yellow-500 text-xl">⚠️</span>
            <span>
              {{ errorDocuments.length }} document<span v-if="errorDocuments.length > 1">s</span>
              could not be evaluated due to missing or invalid ground truth. Please review the
              errors in the "Documents" tab.
            </span>
          </div>

          <!-- Tab Navigation -->
          <div class="px-8 py-3 bg-gradient-to-r from-blue-50/70 to-white/80">
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
              tone="blue"
            />
          </div>

          <!-- Error Display -->
          <div v-if="error" class="mx-8 mt-5 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex items-start">
              <span class="text-red-400 text-lg mr-3">⚠️</span>
              <div class="flex-1">
                <h4 class="text-sm font-semibold text-red-800">Loading Error</h4>
                <p class="mt-1 text-sm text-red-700">{{ error }}</p>
                <div class="mt-3 flex gap-2">
                  <button
                    class="text-sm bg-red-100 text-red-800 px-3 py-1 rounded hover:bg-red-200 transition-colors"
                    :disabled="isRetrying"
                    @click="retryLoad"
                  >
                    {{ isRetrying ? 'Retrying...' : 'Retry' }}
                  </button>
                  <button class="text-sm text-red-600 hover:text-red-800" @click="clearError">
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Tab Content -->
          <div class="flex-1 overflow-y-auto bg-white/60">
            <div v-if="isLoading" class="text-center py-16">
              <div class="mb-3">
                <LoadingSpinner size="medium" />
              </div>
              <span class="text-gray-500">Loading evaluation details...</span>
            </div>

            <div v-else-if="activeTab === 'overview' && evaluationDetail" class="p-8">
              <EvaluationOverview
                :evaluation-detail="evaluationDetail"
                :document-stats="documentStats"
                @view-field-errors="viewFieldErrors"
                @view-document-details="switchToDocumentsTab"
              />
            </div>

            <div v-else-if="activeTab === 'documents'" class="p-8">
              <DocumentAnalysis
                :document-evaluations="documentEvaluations"
                :document-contents="documentContents"
                :document-names="documentNames"
                :loading-documents="loadingDocuments"
                @load-document-content="loadDocumentContent"
                @view-document-details="viewIndividualDocument"
              />
            </div>

            <div v-else-if="activeTab === 'field-errors'" class="p-8">
              <FieldErrorAnalysis
                :field-errors="fieldErrors"
                :selected-field="selectedFieldName"
                @select-field="selectFieldForErrors"
              />
            </div>

            <div v-else-if="activeTab === 'document-detail' && selectedDocument" class="p-8">
              <IndividualDocumentView
                :document="selectedDocument"
                :document-content="documentContents[selectedDocument?.document_id]"
                :loading-content="loadingDocuments[selectedDocument?.document_id]"
                @load-content="loadDocumentContent"
                @back-to-documents="switchToDocumentsTab"
              />
            </div>

            <div v-else class="text-center py-16 text-gray-500">
              <span class="text-4xl text-gray-300 mb-2 block">📊</span>
              <p>No data available for this view</p>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="px-8 py-6 border-t flex justify-between items-center bg-gray-50 rounded-b-2xl"
          >
            <div class="text-sm text-gray-500">
              {{ evaluationDetail?.document_count || 0 }} documents •
              {{ evaluationDetail ? (evaluationDetail.metrics.accuracy * 100).toFixed(1) : '0.0' }}%
              accuracy
            </div>
            <button
              class="px-5 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 transition shadow"
              @click="$emit('close')"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { evaluationsApi } from '@/services/evaluationsApi'
import { documentsApi } from '@/services/documentsApi'
import { formatDate } from '@/utils/formatters.js'
import { useScrollLock } from '@/composables/useScrollLock'
import { extractErrorMessage } from '@/utils/errors'

useScrollLock({ autoLock: true })

// Import sub-components
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import EvaluationOverview from '@/components/evaluation/EvaluationOverview.vue'
import DocumentAnalysis from '@/components/evaluation/DocumentAnalysis.vue'
import FieldErrorAnalysis from '@/components/evaluation/FieldErrorAnalysis.vue'
import IndividualDocumentView from '@/components/documents/IndividualDocumentView.vue'

const props = defineProps({
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
      icon: '📊',
      badge: evaluationDetail.value
        ? `${(evaluationDetail.value.metrics.accuracy * 100).toFixed(1)}%`
        : null,
    },
    {
      id: 'documents',
      name: 'Documents',
      icon: '📄',
      badge: documentEvaluations.value.length || null,
    },
  ]

  // Add field errors tab if there are errors
  const totalFieldErrors = getTotalFieldErrors()
  if (totalFieldErrors > 0) {
    tabs.push({
      id: 'field-errors',
      name: 'Field Errors',
      icon: '⚠️',
      badge: totalFieldErrors,
    })
  }

  // Add individual document tab if a document is selected
  if (selectedDocument.value) {
    tabs.push({
      id: 'document-detail',
      name: `Document #${selectedDocument.value.document_id}`,
      icon: '🔍',
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

onMounted(() => {
  fetchAllData()
})
</script>
