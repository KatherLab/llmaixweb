<template>
  <div class="space-y-6">
    <!-- Header with summary -->
    <div class="bg-gradient-to-r from-blue-50 to-white rounded-lg p-6 border">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-800">Document Analysis</h2>
          <p class="text-gray-600">Detailed comparison of extracted data vs ground truth</p>
        </div>
        <div class="text-right">
          <div class="text-2xl font-bold text-blue-600">{{ documentEvaluations.length }}</div>
          <div class="text-sm text-gray-500">Documents</div>
        </div>
      </div>

      <!-- Quick stats -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
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
          <div class="text-lg font-semibold text-pink-600">{{ errorDocuments }}</div>
          <div class="text-sm text-gray-500">No Ground Truth</div>
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
    <div class="bg-white rounded-lg border p-4">
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
            <option value="poor">Needs Review (&lt;70%)</option>
            <option value="error">No Ground Truth</option>
          </select>
        </div>
        <div class="flex items-center gap-2">
          <label class="text-sm font-medium text-gray-700">Sort:</label>
          <select
            v-model="sortBy"
            class="rounded-md border border-gray-300 text-sm py-1 px-2 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
          >
            <option value="error_first">No Ground Truth First</option>
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

    <!-- Document list -->
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
                'bg-green-100 text-green-800': docEval.accuracy >= 1.0 && !docEval.error,
                'bg-yellow-100 text-yellow-800': docEval.accuracy >= 0.7 && docEval.accuracy < 1.0 && !docEval.error,
                'bg-red-100 text-red-800': docEval.accuracy < 0.7 && !docEval.error,
                'bg-pink-100 text-pink-800': docEval.error
              }"
            >
              {{ index + 1 }}
            </div>
            <div>
              <h3 class="font-medium text-gray-800 flex items-center gap-2">
                {{ documentNames[docEval.document_id]?.name || `Document ${docEval.document_id}` }}
                <span
                  v-if="docEval.error"
                  class="inline-flex items-center bg-pink-100 text-pink-800 px-2 py-0.5 rounded-full font-semibold select-none"
                  title="Evaluation error: {{ docEval.error }}"
                  style="border: 1px solid #f87171;"
                >
                  ⚠️ No Ground Truth
                </span>
                <span
                  v-else-if="getErrorCount(docEval) > 0"
                  class="text-red-600 font-semibold"
                >
                  {{ getErrorCount(docEval) }} error<span v-if="getErrorCount(docEval) > 1">s</span>
                </span>
              </h3>
              <div
                v-if="documentNames[docEval.document_id]?.original
                      && documentNames[docEval.document_id]?.original !== documentNames[docEval.document_id]?.name"
                class="text-xs text-gray-400 italic mt-0.5 truncate max-w-xs"
              >
                (Original: {{ documentNames[docEval.document_id].original }})
              </div>
              <div class="flex items-center gap-4 mt-1 text-sm text-gray-500">
                <span>{{ docEval.correct_fields }}/{{ docEval.total_fields }} fields correct</span>
                <span>{{ (docEval.accuracy * 100).toFixed(1) }}% accuracy</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-20 bg-gray-200 rounded-full h-2">
              <div
                class="h-2 rounded-full"
                :class="{
                  'bg-green-500': docEval.accuracy >= 1.0 && !docEval.error,
                  'bg-yellow-500': docEval.accuracy >= 0.7 && docEval.accuracy < 1.0 && !docEval.error,
                  'bg-red-500': docEval.accuracy < 0.7 && !docEval.error,
                  'bg-pink-500': docEval.error
                }"
                :style="{width: `${docEval.accuracy * 100}%`}"
              ></div>
            </div>
            <button
              @click.stop="$emit('view-document-details', docEval.document_id)"
              class="text-blue-600 hover:text-blue-800 text-sm underline"
            >
              Details
            </button>
            <span
              class="text-lg transition-transform duration-200 text-gray-500 cursor-pointer"
              :class="{ 'transform rotate-180': expandedDocuments[docEval.document_id] }"
            >
              ⌄
            </span>
          </div>
        </div>

        <div v-if="expandedDocuments[docEval.document_id]" class="p-6">
          <div
            v-if="docEval.error"
            class="mb-6 p-5 bg-pink-100 border-2 border-pink-400 rounded text-pink-900 font-semibold flex items-center gap-3 select-text"
          >
            <span class="text-2xl">⚠️</span>
            <span>{{ docEval.error }}</span>
          </div>

          <div v-else>
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
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
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
                          {{ fieldDetail.is_correct ? 'Correct' : (fieldDetail.error_type || 'Incorrect') }}
                        </span>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm">
                        <div v-if="fieldDetail.confidence_score !== null" class="flex items-center">
                          <div class="mr-2">{{ (fieldDetail.confidence_score * 100).toFixed(1) }}%</div>
                          <div class="w-12 bg-gray-200 rounded-full h-1.5">
                            <div
                              class="h-1.5 rounded-full"
                              :class="{
                                'bg-green-500': fieldDetail.confidence_score >= 0.8,
                                'bg-yellow-500': fieldDetail.confidence_score >= 0.5,
                                'bg-red-500': fieldDetail.confidence_score < 0.5
                              }"
                              :style="{width: `${fieldDetail.confidence_score * 100}%`}"
                            ></div>
                          </div>
                        </div>
                        <span v-else class="text-gray-400">-</span>
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
                  <span class="mr-2">📄</span>
                  Document Text
                  <button
                    v-if="!documentContents[docEval.document_id] && !loadingDocuments[docEval.document_id]"
                    @click="$emit('load-document-content', docEval.document_id)"
                    class="ml-auto text-xs text-blue-600 hover:text-blue-800"
                  >
                    Load
                  </button>
                </h4>
                <div v-if="documentContents[docEval.document_id]" class="text-xs text-gray-800 whitespace-pre-wrap">
                  {{ documentContents[docEval.document_id] }}
                </div>
                <div v-else-if="loadingDocuments[docEval.document_id]" class="text-center py-8">
                  <div class="inline-block animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  <p class="mt-2 text-gray-500 text-sm">Loading...</p>
                </div>
                <div v-else class="text-center py-8">
                  <span class="text-4xl text-gray-400 mb-2 block">📄</span>
                  <p class="text-sm text-gray-500">Click "Load" to view document text</p>
                </div>
              </div>

              <!-- Ground truth data -->
              <div class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96 border border-gray-200">
                <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                  <span class="mr-2">✅</span>
                  Ground Truth
                </h4>
                <JsonViewer :data="getGroundTruthData(docEval)" />
              </div>

              <!-- Extracted data -->
              <div class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96 border border-gray-200">
                <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                  <span class="mr-2">🤖</span>
                  Extracted Data
                </h4>
                <JsonViewer :data="getExtractedData(docEval)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import JsonViewer from '@/components/JsonViewer.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  evaluation: {
    type: Object,
    required: true
  },
  documentEvaluations: {
    type: Array,
    required: true
  },
  documentContents: {
    type: Object,
    required: true
  },
  documentNames: {
    type: Object,
    required: true
  },
  loadingDocuments: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['load-document-content', 'view-document-details']);

// Local state
const expandedDocuments = ref({});
const accuracyFilter = ref('all');
const sortBy = ref('error_first');

// Computed properties
const filteredDocuments = computed(() => {
  let filtered = [...props.documentEvaluations];

  // Apply accuracy filter including error docs
  if (accuracyFilter.value !== 'all') {
    filtered = filtered.filter(doc => {
      switch (accuracyFilter.value) {
        case 'perfect':
          return doc.accuracy >= 1.0 && !doc.error;
        case 'good':
          return doc.accuracy >= 0.7 && doc.accuracy < 1.0 && !doc.error;
        case 'poor':
          return doc.accuracy < 0.7 && !doc.error;
        case 'error':
          return !!doc.error;
        default:
          return true;
      }
    });
  }

  // Apply sorting
  filtered.sort((a, b) => {
    // Put error docs on top if selected sorting
    if (sortBy.value === 'error_first') {
      if (a.error && !b.error) return -1;
      if (!a.error && b.error) return 1;
    }

    switch (sortBy.value) {
      case 'accuracy_desc':
        return b.accuracy - a.accuracy;
      case 'accuracy_asc':
        return a.accuracy - b.accuracy;
      case 'document_id':
        return a.document_id - b.document_id;
      case 'errors_desc':
        return getErrorCount(b) - getErrorCount(a);
      default:
        return 0;
    }
  });

  return filtered;
});

const perfectDocuments = computed(() => {
  return props.documentEvaluations.filter(doc => !doc.error && doc.accuracy >= 1.0).length;
});

const goodDocuments = computed(() => {
  return props.documentEvaluations.filter(doc => !doc.error && doc.accuracy >= 0.7 && doc.accuracy < 1.0).length;
});

const poorDocuments = computed(() => {
  return props.documentEvaluations.filter(doc => !doc.error && doc.accuracy < 0.7).length;
});

const errorDocuments = computed(() =>
  props.documentEvaluations.filter(doc => doc.error).length
);

const averageAccuracy = computed(() => {
  if (props.documentEvaluations.length === 0) return 0;
  // Include only docs without errors for average accuracy
  const validDocs = props.documentEvaluations.filter(doc => !doc.error);
  if (validDocs.length === 0) return 0;
  const sum = validDocs.reduce((acc, doc) => acc + doc.accuracy, 0);
  return sum / validDocs.length;
});

// Helper functions
const toggleDocumentExpansion = (documentId) => {
  expandedDocuments.value[documentId] = !expandedDocuments.value[documentId];

  // Auto-load document content when expanded
  if (expandedDocuments.value[documentId] && !props.documentContents[documentId]) {
    emit('load-document-content', documentId);
  }
};

const getErrorCount = (docEval) => {
  if (!docEval.field_details || docEval.error) return 0; // no field errors if document has error
  return Object.values(docEval.field_details).filter(field => !field.is_correct).length;
};

const formatFieldValue = (value) => {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const getGroundTruthData = (docEval) => {
  const groundTruthData = {};
  Object.entries(docEval.field_details || {}).forEach(([fieldName, fieldDetail]) => {
    groundTruthData[fieldName] = fieldDetail.ground_truth_value;
  });
  return groundTruthData;
};

const getExtractedData = (docEval) => {
  const extractedData = {};
  Object.entries(docEval.field_details || {}).forEach(([fieldName, fieldDetail]) => {
    extractedData[fieldName] = fieldDetail.predicted_value;
  });
  return extractedData;
};
</script>
