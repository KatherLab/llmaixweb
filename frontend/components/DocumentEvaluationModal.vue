<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-[95vw] max-h-[95vh] flex flex-col"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Document-Level Evaluation</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="isLoading" class="text-center py-12">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading document evaluations...</p>
          </div>

          <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4">
            <div class="flex">
              <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
              <div class="ml-3">
                <p class="text-sm text-red-700">{{ error }}</p>
              </div>
            </div>
          </div>

          <div v-else-if="documentEvaluations.length > 0">
            <!-- Header with evaluation summary -->
            <div class="bg-gradient-to-r from-blue-50 to-white rounded-lg p-6 mb-6 border">
              <div class="flex justify-between items-start mb-4">
                <div>
                  <h2 class="text-xl font-semibold text-gray-800">Trial #{{ evaluation.trial_id }} - Document Analysis</h2>
                  <p class="text-gray-600">Detailed comparison of extracted data vs ground truth</p>
                </div>
                <div class="text-right">
                  <div class="text-2xl font-bold text-blue-600">
                    {{ documentEvaluations.length }}
                  </div>
                  <div class="text-sm text-gray-500">Documents</div>
                </div>
              </div>

              <!-- Quick stats -->
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-green-600">{{ perfectDocuments }}</div>
                  <div class="text-sm text-gray-500">Perfect Match</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-yellow-600">{{ goodDocuments }}</div>
                  <div class="text-sm text-gray-500">Good (≥70%)</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-red-600">{{ poorDocuments }}</div>
                  <div class="text-sm text-gray-500">Needs Review</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-gray-600">
                    {{ (averageAccuracy * 100).toFixed(1) }}%
                  </div>
                  <div class="text-sm text-gray-500">Avg Accuracy</div>
                </div>
              </div>
            </div>

            <!-- Filter and sort controls -->
            <div class="bg-white rounded-lg border p-4 mb-6">
              <div class="flex flex-wrap gap-4 items-center">
                <div class="flex items-center gap-2">
                  <label class="text-sm font-medium text-gray-700">Filter:</label>
                  <select
                    v-model="accuracyFilter"
                    class="rounded-md border border-gray-300 text-sm py-1 px-2 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                  >
                    <option value="all">All Documents</option>
                    <option value="perfect">Perfect (100%)</option>
                    <option value="good">Good (≥70%)</option>
                    <option value="poor">Needs Review (<70%)</option>
                  </select>
                </div>
                <div class="flex items-center gap-2">
                  <label class="text-sm font-medium text-gray-700">Sort:</label>
                  <select
                    v-model="sortBy"
                    class="rounded-md border border-gray-300 text-sm py-1 px-2 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                  >
                    <option value="accuracy_desc">Accuracy (High to Low)</option>
                    <option value="accuracy_asc">Accuracy (Low to High)</option>
                    <option value="document_id">Document ID</option>
                    <option value="errors_desc">Most Errors First</option>
                  </select>
                </div>
                <div class="flex items-center gap-2 ml-auto">
                  <span class="text-sm text-gray-600">{{ filteredDocuments.length }} documents</span>
                </div>
              </div>
            </div>

            <!-- Document accordion -->
            <div class="space-y-4">
              <div
                v-for="(docEval, index) in filteredDocuments"
                :key="docEval.document_id"
                class="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-100 hover:shadow-md transition-shadow duration-200"
              >
                <div
                  @click="toggleDocumentExpansion(docEval.document_id)"
                  class="p-4 cursor-pointer border-b flex justify-between items-center hover:bg-gray-50 transition-colors duration-150"
                >
                  <div class="flex items-center gap-4">
                    <div
                      class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                      :class="{
                        'bg-green-100 text-green-800': docEval.accuracy >= 1.0,
                        'bg-yellow-100 text-yellow-800': docEval.accuracy >= 0.7 && docEval.accuracy < 1.0,
                        'bg-red-100 text-red-800': docEval.accuracy < 0.7
                      }"
                    >
                      {{ index + 1 }}
                    </div>
                    <div>
                      <h3 class="font-medium text-gray-800">
                        {{ getDocumentName(docEval.document_id) }}
                      </h3>
                      <div class="flex items-center gap-4 mt-1 text-sm text-gray-500">
                        <span>{{ docEval.correct_fields }}/{{ docEval.total_fields }} fields correct</span>
                        <span>{{ (docEval.accuracy * 100).toFixed(1) }}% accuracy</span>
                        <span v-if="docEval.incorrect_fields.length > 0" class="text-red-600">
                          {{ docEval.incorrect_fields.length }} errors
                        </span>
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <div class="w-20 bg-gray-200 rounded-full h-2">
                      <div
                        class="h-2 rounded-full"
                        :class="{
                          'bg-green-500': docEval.accuracy >= 1.0,
                          'bg-yellow-500': docEval.accuracy >= 0.7 && docEval.accuracy < 1.0,
                          'bg-red-500': docEval.accuracy < 0.7
                        }"
                        :style="{width: `${docEval.accuracy * 100}%`}"
                      ></div>
                    </div>
                    <svg
                      class="w-5 h-5 transition-transform duration-200 text-gray-500"
                      :class="{ 'transform rotate-180': expandedDocuments[docEval.document_id] }"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                  </div>
                </div>

                <div v-if="expandedDocuments[docEval.document_id]" class="p-6">
                  <!-- Field comparison table -->
                  <div class="mb-6">
                    <h4 class="font-medium text-gray-800 mb-3">Field-by-Field Comparison</h4>
                    <div class="overflow-x-auto">
                      <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                          <tr>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Field</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ground Truth</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Extracted</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Error Type</th>
                          </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                          <tr
                            v-for="(fieldDetail, fieldName) in docEval.field_details"
                            :key="fieldName"
                            class="hover:bg-gray-50"
                            :class="{
                              'bg-green-50': fieldDetail.is_correct,
                              'bg-red-50': !fieldDetail.is_correct
                            }"
                          >
                            <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                              {{ fieldName }}
                            </td>
                            <td class="px-4 py-3 text-sm text-gray-600 max-w-xs">
                              <div class="truncate" :title="formatFieldValue(fieldDetail.ground_truth_value)">
                                {{ formatFieldValue(fieldDetail.ground_truth_value) }}
                              </div>
                            </td>
                            <td class="px-4 py-3 text-sm text-gray-600 max-w-xs">
                              <div class="truncate" :title="formatFieldValue(fieldDetail.predicted_value)">
                                {{ formatFieldValue(fieldDetail.predicted_value) }}
                              </div>
                            </td>
                            <td class="px-4 py-3 whitespace-nowrap">
                              <span
                                class="px-2 py-1 rounded-full text-xs font-medium"
                                :class="{
                                  'bg-green-100 text-green-800': fieldDetail.is_correct,
                                  'bg-red-100 text-red-800': !fieldDetail.is_correct
                                }"
                              >
                                {{ fieldDetail.is_correct ? 'Correct' : 'Incorrect' }}
                              </span>
                            </td>
                            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                              {{ fieldDetail.error_type || '-' }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <!-- Document content panels -->
                  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <!-- Document text -->
                    <div class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96 border border-gray-200">
                      <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Document Text
                      </h4>
                      <div v-if="documentContents[docEval.document_id]" class="text-xs text-gray-800 whitespace-pre-wrap">
                        {{ documentContents[docEval.document_id] }}
                      </div>
                      <div v-else-if="loadingDocuments[docEval.document_id]" class="text-center py-8">
                        <div class="inline-block animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                        <p class="mt-2 text-gray-500 text-sm">Loading...</p>
                      </div>
                      <div v-else class="text-gray-500 text-sm">Document content not available</div>
                    </div>

                    <!-- Ground truth data -->
                    <div class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96 border border-gray-200">
                      <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Ground Truth
                      </h4>
                      <JsonViewer :data="getGroundTruthData(docEval)" />
                    </div>

                    <!-- Extracted data -->
                    <div class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96 border border-gray-200">
                      <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                        Extracted Data
                      </h4>
                      <JsonViewer :data="getExtractedData(docEval)" />
                    </div>
                  </div>

                  <!-- View controls -->
                  <div class="mt-4 flex justify-end gap-2">
                    <button
                      @click="viewDocumentDetails(docEval.document_id)"
                      class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-md text-sm flex items-center transition-colors duration-150"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      View Full Document
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="text-center py-12 text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p>No document evaluations available</p>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            @click="downloadDocumentReport"
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
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import JsonViewer from '@/components/JsonViewer.vue';

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
const error = ref(null);

// Data
const documentEvaluations = ref([]);
const documentContents = ref({});
const documentNames = ref({});
const loadingDocuments = ref({});
const expandedDocuments = ref({});

// Filters and sorting
const accuracyFilter = ref('all');
const sortBy = ref('accuracy_desc');

// Computed properties
const filteredDocuments = computed(() => {
  let filtered = [...documentEvaluations.value];

  // Apply accuracy filter
  if (accuracyFilter.value !== 'all') {
    filtered = filtered.filter(doc => {
      switch (accuracyFilter.value) {
        case 'perfect':
          return doc.accuracy >= 1.0;
        case 'good':
          return doc.accuracy >= 0.7 && doc.accuracy < 1.0;
        case 'poor':
          return doc.accuracy < 0.7;
        default:
          return true;
      }
    });
  }

  // Apply sorting
  filtered.sort((a, b) => {
    switch (sortBy.value) {
      case 'accuracy_desc':
        return b.accuracy - a.accuracy;
      case 'accuracy_asc':
        return a.accuracy - b.accuracy;
      case 'document_id':
        return a.document_id - b.document_id;
      case 'errors_desc':
        return b.incorrect_fields.length - a.incorrect_fields.length;
      default:
        return 0;
    }
  });

  return filtered;
});

const perfectDocuments = computed(() => {
  return documentEvaluations.value.filter(doc => doc.accuracy >= 1.0).length;
});

const goodDocuments = computed(() => {
  return documentEvaluations.value.filter(doc => doc.accuracy >= 0.7 && doc.accuracy < 1.0).length;
});

const poorDocuments = computed(() => {
  return documentEvaluations.value.filter(doc => doc.accuracy < 0.7).length;
});

const averageAccuracy = computed(() => {
  if (documentEvaluations.value.length === 0) return 0;
  const sum = documentEvaluations.value.reduce((acc, doc) => acc + doc.accuracy, 0);
  return sum / documentEvaluations.value.length;
});

// Load document evaluations
const fetchDocumentEvaluations = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    // Get all document evaluations for this evaluation
    const promises = props.evaluation.document_metrics.map(async (docMetric) => {
      const response = await api.get(
        `/project/${props.projectId}/evaluation/${props.evaluation.id}/document/${docMetric.document_id}`
      );
      return response.data;
    });

    documentEvaluations.value = await Promise.all(promises);

    // Load document names
    await loadDocumentNames();

  } catch (err) {
    error.value = `Failed to load document evaluations: ${err.message}`;
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Load document names
const loadDocumentNames = async () => {
  const promises = documentEvaluations.value.map(async (docEval) => {
    try {
      const response = await api.get(`/project/${props.projectId}/document/${docEval.document_id}`);
      const doc = response.data;

      let name = '';
      if (doc.original_file?.file_name) {
        name = doc.original_file.file_name;
      } else if (doc.meta_data?.title) {
        name = doc.meta_data.title;
      } else {
        name = `Document ${docEval.document_id}`;
      }

      documentNames.value[docEval.document_id] = name;
    } catch (err) {
      console.error(`Failed to load document name for ${docEval.document_id}:`, err);
      documentNames.value[docEval.document_id] = `Document ${docEval.document_id}`;
    }
  });

  await Promise.all(promises);
};

// Toggle document expansion and load content
const toggleDocumentExpansion = async (documentId) => {
  expandedDocuments.value[documentId] = !expandedDocuments.value[documentId];

  // Load document content if expanded and not already loaded
  if (expandedDocuments.value[documentId] && !documentContents.value[documentId]) {
    await loadDocumentContent(documentId);
  }
};

// Load document content
const loadDocumentContent = async (documentId) => {
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

// Helper functions
const getDocumentName = (documentId) => {
  return documentNames.value[documentId] || `Document ${documentId}`;
};

const formatFieldValue = (value) => {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const getGroundTruthData = (docEval) => {
  const groundTruthData = {};
  Object.entries(docEval.field_details).forEach(([fieldName, fieldDetail]) => {
    groundTruthData[fieldName] = fieldDetail.ground_truth_value;
  });
  return groundTruthData;
};

const getExtractedData = (docEval) => {
  const extractedData = {};
  Object.entries(docEval.field_details).forEach(([fieldName, fieldDetail]) => {
    extractedData[fieldName] = fieldDetail.predicted_value;
  });
  return extractedData;
};

// View document details (placeholder for future implementation)
const viewDocumentDetails = (documentId) => {
  toast.info(`Viewing full document ${documentId} - Feature coming soon!`);
  // TODO: Implement full document view modal
};

// Download document report
const downloadDocumentReport = async () => {
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
    link.setAttribute('download', `document_evaluation_${props.evaluation.id}_report.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    toast.success('Document report downloaded successfully');
  } catch (err) {
    toast.error(`Failed to download report: ${err.message}`);
    console.error(err);
  } finally {
    isDownloading.value = false;
  }
};

onMounted(() => {
  fetchDocumentEvaluations();
});
</script>
