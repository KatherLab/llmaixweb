<template>
  <teleport to="body">
    <div
      class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      @click.self="$emit('close')"
    >
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm transition-all"></div>
      <div
        class="relative bg-white rounded-3xl shadow-2xl w-full max-w-5xl max-h-[95vh] flex flex-col overflow-hidden"
        @click.stop
      >
        <!-- Header -->
        <div class="px-8 py-6 border-b flex justify-between items-center rounded-t-3xl bg-white/90">
          <div>
            <h3 class="text-2xl font-bold text-gray-900">Evaluation Analysis</h3>
            <p v-if="evaluation" class="text-sm text-gray-500">
              Trial #{{ evaluation.trial_id }} • {{ formatDate(evaluation.created_at) }}
            </p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-blue-700 hover:bg-blue-50 rounded-full p-2 focus:outline-none focus:ring-2 focus:ring-blue-500" aria-label="Close">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Error Documents Warning Banner -->
        <div v-if="errorDocuments.length > 0" class="mx-8 mt-5 p-4 bg-yellow-50 border border-yellow-300 rounded-lg flex items-center gap-2">
          <span class="text-yellow-500 text-xl">⚠️</span>
          <span>
            {{ errorDocuments.length }} document<span v-if="errorDocuments.length > 1">s</span> could not be evaluated due to missing or invalid ground truth. Please review the errors in the "Documents" tab.
          </span>
        </div>

        <!-- Tab Navigation -->
        <div class="px-8 py-3 border-b bg-gradient-to-r from-blue-50/70 to-white/80">
          <nav class="flex space-x-8">
            <button
              v-for="tab in availableTabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              class="py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200"
              :class="{
                'border-blue-500 text-blue-700': activeTab === tab.id,
                'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300': activeTab !== tab.id
              }"
            >
              <span class="flex items-center gap-2">
                <span class="text-lg">{{ tab.icon }}</span>
                {{ tab.name }}
                <span v-if="tab.badge" class="bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full text-xs ml-1">
                  {{ tab.badge }}
                </span>
              </span>
            </button>
          </nav>
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
                  @click="retryLoad"
                  class="text-sm bg-red-100 text-red-800 px-3 py-1 rounded hover:bg-red-200 transition-colors"
                  :disabled="isRetrying"
                >
                  {{ isRetrying ? 'Retrying...' : 'Retry' }}
                </button>
                <button @click="clearError" class="text-sm text-red-600 hover:text-red-800">
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-y-auto bg-white/60">
          <div v-if="isLoading" class="text-center py-16">
            <span class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mb-3"></span>
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
              :project-id="projectId"
              :evaluation="evaluation"
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
              :project-id="projectId"
              :evaluation="evaluation"
              :field-errors="fieldErrors"
              :selected-field="selectedFieldName"
              @select-field="selectFieldForErrors"
            />
          </div>

          <div v-else-if="activeTab === 'document-detail' && selectedDocument" class="p-8">
            <IndividualDocumentView
              :project-id="projectId"
              :evaluation="evaluation"
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
        <div class="px-8 py-6 border-t flex justify-between items-center bg-white/90 rounded-b-3xl">
          <div class="text-sm text-gray-500">
            {{ evaluationDetail?.document_count || 0 }} documents •
            {{ evaluationDetail ? (evaluationDetail.metrics.accuracy * 100).toFixed(1) : '0.0' }}% accuracy
          </div>
          <button
            @click="$emit('close')"
            class="px-5 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 transition shadow"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue';
import { api } from '@/services/api.js';
import { formatDate } from '@/utils/formatters.js';
import { useToast } from 'vue-toastification';

// Import sub-components
import EvaluationOverview from '@/components/EvaluationOverview.vue';
import DocumentAnalysis from '@/components/evaluation/DocumentAnalysis.vue';
import FieldErrorAnalysis from '@/components/evaluation/FieldErrorAnalysis.vue';
import IndividualDocumentView from '@/components/IndividualDocumentView.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  evaluation: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close']);
const toast = useToast();

// State
const activeTab = ref('overview');
const isLoading = ref(false);
const isRetrying = ref(false);
const error = ref(null);

// Data
const evaluationDetail = ref(null);
const documentEvaluations = ref([]);
const documentContents = ref({});
const documentNames = ref({});
const loadingDocuments = ref({});
const fieldErrors = ref({});
const selectedFieldName = ref(null);
const selectedDocument = ref(null);

// Computed: documents with errors
const errorDocuments = computed(() => {
  return documentEvaluations.value.filter(d =>
    !!d.error ||
    d.has_error ||
    (d.accuracy === 0 && d.correct_fields === 0 && d.total_fields === 0)
  );
});

// Tab configuration
const availableTabs = computed(() => {
  const tabs = [
    {
      id: 'overview',
      name: 'Overview',
      icon: '📊',
      badge: evaluationDetail.value ? `${(evaluationDetail.value.metrics.accuracy * 100).toFixed(1)}%` : null
    },
    {
      id: 'documents',
      name: 'Documents',
      icon: '📄',
      badge: documentEvaluations.value.length || null
    }
  ];

  // Add field errors tab if there are errors
  const totalFieldErrors = getTotalFieldErrors();
  if (totalFieldErrors > 0) {
    tabs.push({
      id: 'field-errors',
      name: 'Field Errors',
      icon: '⚠️',
      badge: totalFieldErrors
    });
  }

  // Add individual document tab if a document is selected
  if (selectedDocument.value) {
    tabs.push({
      id: 'document-detail',
      name: `Document #${selectedDocument.value.document_id}`,
      icon: '🔍',
      badge: null
    });
  }

  return tabs;
});

// Computed properties
const documentStats = computed(() => {
  if (!documentEvaluations.value.length) {
    return { perfect: 0, good: 0, poor: 0, error: 0, perfectPercent: 0, goodPercent: 0, poorPercent: 0, errorPercent: 0 };
  }

  const docs = documentEvaluations.value;
  const error = docs.filter(d => !!d.error || d.has_error).length;
  const perfect = docs.filter(d => !d.error && d.accuracy >= 0.9).length;
  const good = docs.filter(d => !d.error && d.accuracy >= 0.7 && d.accuracy < 0.9).length;
  const poor = docs.filter(d => !d.error && d.accuracy < 0.7).length;
  const total = docs.length;

  return {
    error,
    perfect,
    good,
    poor,
    perfectPercent: total > 0 ? (perfect / total) * 100 : 0,
    goodPercent: total > 0 ? (good / total) * 100 : 0,
    poorPercent: total > 0 ? (poor / total) * 100 : 0,
    errorPercent: total > 0 ? (error / total) * 100 : 0
  };
});

// Helper functions
const getTotalFieldErrors = () => {
  return Object.values(fieldErrors.value).reduce((total, errors) => total + errors.length, 0);
};

const clearError = () => {
  error.value = null;
};

const retryLoad = async () => {
  isRetrying.value = true;
  error.value = null;
  await fetchAllData();
  isRetrying.value = false;
};

// Data fetching
const fetchAllData = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    // Fetch evaluation details
    const evaluationResponse = await api.get(
      `/project/${props.projectId}/evaluation/${props.evaluation.id}`
    );
    evaluationDetail.value = evaluationResponse.data;

    // Fetch document evaluations
    if (props.evaluation.document_metrics?.length) {
      const documentPromises = props.evaluation.document_metrics.map(async (docMetric) => {
        try {
          const response = await api.get(
            `/project/${props.projectId}/evaluation/${props.evaluation.id}/document/${docMetric.document_id}`
          );
          return response.data;
        } catch (err) {
          return {
            document_id: docMetric.document_id,
            error: err.response?.data?.detail || err.message,
            accuracy: 0,
            correct_fields: 0,
            total_fields: 0,
            field_details: {}
          };
        }
      });

      documentEvaluations.value = await Promise.all(documentPromises);
    }

    // Load document names
    await loadDocumentNames();

    // Load field errors for each field
    if (evaluationDetail.value?.fields) {
      await loadFieldErrors();
    }

  } catch (err) {
    console.error('Failed to load evaluation data:', err);

    if (err.response?.status === 404) {
      error.value = 'Evaluation not found. It may have been deleted.';
    } else if (err.response?.status === 403) {
      error.value = 'You do not have permission to view this evaluation.';
    } else {
      error.value = `Failed to load evaluation data: ${err.response?.data?.detail || err.message}`;
    }
  } finally {
    isLoading.value = false;
  }
};

const loadDocumentNames = async () => {
  const promises = documentEvaluations.value.map(async (docEval) => {
    try {
      const response = await api.get(`/project/${props.projectId}/document/${docEval.document_id}`);
      const doc = response.data;

      documentNames.value[docEval.document_id] = {
        name: doc.document_name || doc.original_file?.file_name || `Document ${docEval.document_id}`,
        original: doc.original_file?.file_name || ''
      };
    } catch (err) {
      documentNames.value[docEval.document_id] = {
        name: `Document ${docEval.document_id}`,
        original: ''
      };
    }
  });
  await Promise.all(promises);
};


const loadFieldErrors = async () => {
  const fieldNames = Object.keys(evaluationDetail.value.fields);

  const promises = fieldNames.map(async (fieldName) => {
    try {
      const response = await api.get(
        `/project/${props.projectId}/evaluation/${props.evaluation.id}/errors?field_name=${fieldName}&limit=50`
      );
      fieldErrors.value[fieldName] = response.data;
    } catch (err) {
      console.error(`Failed to load errors for field ${fieldName}:`, err);
      fieldErrors.value[fieldName] = [];
    }
  });

  await Promise.all(promises);
};

const loadDocumentContent = async (documentId) => {
  if (documentContents.value[documentId] || loadingDocuments.value[documentId]) return;

  loadingDocuments.value[documentId] = true;

  try {
    const response = await api.get(`/project/${props.projectId}/document/${documentId}`);
    documentContents.value[documentId] = response.data.text || 'No text content available';
  } catch (err) {
    console.error(`Failed to load document content for ${documentId}:`, err);
    documentContents.value[documentId] = 'Error loading document content';
  } finally {
    loadingDocuments.value[documentId] = false;
  }
};

// Navigation actions
const viewFieldErrors = (fieldName) => {
  selectedFieldName.value = fieldName;
  activeTab.value = 'field-errors';
};

const selectFieldForErrors = (fieldName) => {
  selectedFieldName.value = fieldName;
};

const switchToDocumentsTab = () => {
  activeTab.value = 'documents';
  selectedDocument.value = null;
};

const viewIndividualDocument = async (documentId) => {
  const document = documentEvaluations.value.find(d => d.document_id === documentId);
  if (document) {
    selectedDocument.value = document;
    activeTab.value = 'document-detail';

    if (!documentContents.value[documentId]) {
      await loadDocumentContent(documentId);
    }
  }
};

watch(() => true, () => { document.body.style.overflow = 'hidden'; }, { immediate: true });
onUnmounted(() => { document.body.style.overflow = ''; });

onMounted(() => {
  fetchAllData();
});
</script>
