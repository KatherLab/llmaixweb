<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-6xl max-h-[95vh] flex flex-col"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Evaluation Details</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <!-- Enhanced Error Display -->
          <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex items-start">
              <svg class="w-5 h-5 text-red-400 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div class="flex-1">
                <h4 class="text-sm font-medium text-red-800">Loading Error</h4>
                <p class="mt-1 text-sm text-red-700">{{ error }}</p>
                <div class="mt-3">
                  <button
                    @click="retryLoad"
                    class="text-sm bg-red-100 text-red-800 px-3 py-1 rounded hover:bg-red-200 transition-colors"
                    :disabled="isRetrying"
                  >
                    <span v-if="isRetrying">Retrying...</span>
                    <span v-else>Retry</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="isLoading" class="text-center py-12">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading evaluation details...</p>
          </div>

          <div v-else-if="evaluationDetail">
            <!-- Header with overall metrics -->
            <div class="bg-gradient-to-r from-blue-50 to-white rounded-lg p-6 mb-6 border">
              <div class="flex justify-between items-start mb-4">
                <div>
                  <h2 class="text-xl font-semibold text-gray-800">Trial #{{ evaluationDetail.trial_id }}</h2>
                  <p class="text-gray-600">Model: {{ evaluationDetail.model }}</p>
                  <p class="text-sm text-gray-500">{{ formatDate(evaluationDetail.created_at) }}</p>

                  <!-- Enhanced Error Summary -->
                  <div v-if="hasDocumentErrors" class="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <div class="flex items-start">
                      <svg class="w-4 h-4 text-yellow-400 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                      </svg>
                      <div>
                        <p class="text-sm font-medium text-yellow-800">
                          {{ errorDocumentCount }} document(s) have evaluation errors
                        </p>
                        <p class="text-xs text-yellow-700 mt-1">
                          These documents couldn't be properly evaluated due to missing ground truth data or other issues.
                        </p>
                        <button
                          @click="showErrorsModal = true"
                          class="mt-2 text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded hover:bg-yellow-200 transition-colors"
                        >
                          View Error Details
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-2xl font-bold text-blue-600">
                    {{ (evaluationDetail.metrics.accuracy * 100).toFixed(1) }}%
                  </div>
                  <div class="text-sm text-gray-500">Overall Accuracy</div>
                </div>
              </div>

              <!-- Key metrics grid -->
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-gray-800">{{ evaluationDetail.document_count }}</div>
                  <div class="text-sm text-gray-500">Documents</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-green-600">
                    {{ (evaluationDetail.metrics.precision * 100).toFixed(1) }}%
                  </div>
                  <div class="text-sm text-gray-500">Precision</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-yellow-600">
                    {{ (evaluationDetail.metrics.recall * 100).toFixed(1) }}%
                  </div>
                  <div class="text-sm text-gray-500">Recall</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-purple-600">
                    {{ (evaluationDetail.metrics.f1_score * 100).toFixed(1) }}%
                  </div>
                  <div class="text-sm text-gray-500">F1 Score</div>
                </div>
              </div>
            </div>

            <!-- Field-level metrics -->
            <div class="bg-white rounded-lg border p-6 mb-6">
              <h3 class="text-lg font-semibold text-gray-800 mb-4">Field-Level Performance</h3>
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Field</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accuracy</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precision</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recall</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">F1 Score</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Errors</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="(fieldData, fieldName) in evaluationDetail.fields" :key="fieldName" class="hover:bg-gray-50">
                      <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                        {{ fieldName }}
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm">
                        <div class="flex items-center">
                          <div class="mr-2">{{ (fieldData.accuracy * 100).toFixed(1) }}%</div>
                          <div class="w-16 bg-gray-200 rounded-full h-2">
                            <div class="bg-blue-600 h-2 rounded-full" :style="{width: `${fieldData.accuracy * 100}%`}"></div>
                          </div>
                        </div>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {{ (fieldData.precision * 100).toFixed(1) }}%
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {{ (fieldData.recall * 100).toFixed(1) }}%
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {{ (fieldData.f1_score * 100).toFixed(1) }}%
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm">
                        <button
                          @click="viewFieldErrors(fieldName)"
                          class="text-red-600 hover:text-red-800 text-sm underline disabled:text-gray-400 disabled:no-underline disabled:cursor-not-allowed"
                          :disabled="!fieldData.error_count || fieldData.error_count === 0"
                        >
                          {{ fieldData.error_count || 0 }} errors
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Document-level summary -->
            <div class="bg-white rounded-lg border p-6">
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-800">Document Performance Summary</h3>
                <div class="text-sm text-gray-500">
                  Showing {{ evaluationDetail.documents.length }} documents
                </div>
              </div>

              <!-- Document performance distribution -->
              <div class="mb-4">
                <div class="flex items-center justify-between text-sm text-gray-600 mb-2">
                  <span>Accuracy Distribution</span>
                  <span>{{ documentStats.perfect }} perfect, {{ documentStats.good }} good, {{ documentStats.poor }} needs improvement</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-3">
                  <div class="h-3 rounded-full flex">
                    <div class="bg-green-500 rounded-l-full" :style="{width: `${documentStats.perfectPercent}%`}"></div>
                    <div class="bg-yellow-500" :style="{width: `${documentStats.goodPercent}%`}"></div>
                    <div class="bg-red-500 rounded-r-full" :style="{width: `${documentStats.poorPercent}%`}"></div>
                  </div>
                </div>
              </div>

              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Document</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accuracy</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Correct Fields</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="doc in evaluationDetail.documents" :key="doc.document_id" class="hover:bg-gray-50">
                      <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                        Document #{{ doc.document_id }}
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm">
                        <div v-if="doc.error" class="text-red-600 text-xs">
                          Error: {{ doc.error }}
                        </div>
                        <div v-else class="flex items-center">
                          <div class="mr-2">{{ (doc.accuracy * 100).toFixed(1) }}%</div>
                          <div class="w-16 bg-gray-200 rounded-full h-2">
                            <div
                              class="h-2 rounded-full"
                              :class="{
                                'bg-green-500': doc.accuracy >= 0.9,
                                'bg-yellow-500': doc.accuracy >= 0.7 && doc.accuracy < 0.9,
                                'bg-red-500': doc.accuracy < 0.7
                              }"
                              :style="{width: `${doc.accuracy * 100}%`}"
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        <div v-if="doc.error" class="text-red-600">-</div>
                        <div v-else>{{ doc.correct_fields }}/{{ doc.total_fields }}</div>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap">
                        <span
                          v-if="doc.error"
                          class="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                        >
                          Error
                        </span>
                        <span
                          v-else
                          class="px-2 py-1 rounded-full text-xs font-medium"
                          :class="{
                            'bg-green-100 text-green-800': doc.accuracy >= 0.9,
                            'bg-yellow-100 text-yellow-800': doc.accuracy >= 0.7 && doc.accuracy < 0.9,
                            'bg-red-100 text-red-800': doc.accuracy < 0.7
                          }"
                        >
                          {{ doc.accuracy >= 0.9 ? 'Perfect' : doc.accuracy >= 0.7 ? 'Good' : 'Needs Review' }}
                        </span>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm">
                        <button
                          v-if="!doc.error"
                          @click="viewDocumentDetails(doc)"
                          class="text-blue-600 hover:text-blue-800 text-sm underline"
                        >
                          Details
                        </button>
                        <button
                          v-else
                          @click="viewDocumentError(doc)"
                          class="text-red-600 hover:text-red-800 text-sm underline"
                        >
                          View Error
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            @click="downloadReport"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            :disabled="isDownloading"
          >
            <span v-if="isDownloading" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Downloading...
            </span>
            <span v-else class="flex items-center">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download Report
            </span>
          </button>
          <button
            @click="$emit('close')"
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            Close
          </button>
        </div>

        <!-- Error Details Modal -->
        <EvaluationErrorsModal
          v-if="showErrorsModal"
          :project-id="projectId"
          :evaluation="evaluation"
          @close="showErrorsModal = false"
        />

        <!-- Field Errors Modal -->
        <FieldErrorsModal
          v-if="showFieldErrorsModal"
          :project-id="projectId"
          :evaluation="evaluation"
          :field-name="selectedFieldName"
          @close="showFieldErrorsModal = false"
        />

        <!-- Document Details Modal -->
        <DocumentDetailsModal
          v-if="showDocumentDetailsModal"
          :project-id="projectId"
          :evaluation="evaluation"
          :document="selectedDocument"
          @close="showDocumentDetailsModal = false"
        />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters';
import { useToast } from 'vue-toastification';
import EvaluationErrorsModal from './EvaluationErrorsModal.vue';
import FieldErrorsModal from './FieldErrorsModal.vue';
import DocumentDetailsModal from './DocumentDetailsModal.vue';

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
const isLoading = ref(false);
const isDownloading = ref(false);
const isRetrying = ref(false);
const error = ref(null);
const evaluationDetail = ref(null);

// Modal states
const showErrorsModal = ref(false);
const showFieldErrorsModal = ref(false);
const showDocumentDetailsModal = ref(false);

// Selected items
const selectedFieldName = ref(null);
const selectedDocument = ref(null);

// Computed properties
const hasDocumentErrors = computed(() => {
  if (!evaluationDetail.value?.documents) return false;
  return evaluationDetail.value.documents.some(doc => doc.error);
});

const errorDocumentCount = computed(() => {
  if (!evaluationDetail.value?.documents) return 0;
  return evaluationDetail.value.documents.filter(doc => doc.error).length;
});

// Computed statistics for document performance
const documentStats = computed(() => {
  if (!evaluationDetail.value?.documents) {
    return { perfect: 0, good: 0, poor: 0, perfectPercent: 0, goodPercent: 0, poorPercent: 0 };
  }

  const docs = evaluationDetail.value.documents.filter(d => !d.error); // Exclude error documents
  const perfect = docs.filter(d => d.accuracy >= 0.9).length;
  const good = docs.filter(d => d.accuracy >= 0.7 && d.accuracy < 0.9).length;
  const poor = docs.filter(d => d.accuracy < 0.7).length;
  const total = docs.length;

  return {
    perfect,
    good,
    poor,
    perfectPercent: total > 0 ? (perfect / total) * 100 : 0,
    goodPercent: total > 0 ? (good / total) * 100 : 0,
    poorPercent: total > 0 ? (poor / total) * 100 : 0
  };
});

// Load evaluation details
const fetchEvaluationDetail = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await api.get(
      `/project/${props.projectId}/evaluation/${props.evaluation.id}`
    );
    evaluationDetail.value = response.data;
  } catch (err) {
    console.error('Failed to load evaluation details:', err);

    if (err.response?.status === 404) {
      error.value = 'Evaluation not found. It may have been deleted.';
    } else if (err.response?.status === 403) {
      error.value = 'You do not have permission to view this evaluation.';
    } else {
      error.value = `Failed to load evaluation details: ${err.response?.data?.detail || err.message}`;
    }
  } finally {
    isLoading.value = false;
  }
};

// Retry loading
const retryLoad = async () => {
  isRetrying.value = true;
  await fetchEvaluationDetail();
  isRetrying.value = false;
};

// View field errors
const viewFieldErrors = async (fieldName) => {
  if (!fieldName) return;

  selectedFieldName.value = fieldName;
  showFieldErrorsModal.value = true;
};

// View document details
const viewDocumentDetails = (document) => {
  selectedDocument.value = document;
  showDocumentDetailsModal.value = true;
};

// View document error
const viewDocumentError = (document) => {
  toast.error(`Document #${document.document_id}: ${document.error}`);
};

// Download evaluation report
const downloadReport = async () => {
  isDownloading.value = true;
  try {
    const response = await api.get(
      `/project/${props.projectId}/evaluations/download?evaluation_ids=${props.evaluation.id}&format=csv&include_details=true`,
      { responseType: 'blob' }
    );

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `evaluation_${props.evaluation.id}_report.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    toast.success('Report downloaded successfully');
  } catch (err) {
    console.error('Failed to download report:', err);
    toast.error(`Failed to download report: ${err.response?.data?.detail || err.message}`);
  } finally {
    isDownloading.value = false;
  }
};

onMounted(() => {
  fetchEvaluationDetail();
});
</script>
