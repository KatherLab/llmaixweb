<template>
  <div class="space-y-6">
    <!-- Header with document info -->
    <div class="bg-gradient-to-r from-gray-50 to-white rounded-lg p-6 border">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-800">Document #{{ document.document_id }}</h2>
          <p class="text-gray-600">Individual field-by-field analysis</p>
          <button
            @click="$emit('back-to-documents')"
            class="mt-2 text-sm text-blue-600 hover:text-blue-800 flex items-center"
          >
            <span class="mr-1">←</span>
            Back to Documents
          </button>
        </div>
        <div class="text-right">
          <div class="text-2xl font-bold text-blue-600">
            {{ (document.accuracy * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-gray-500">Accuracy</div>
        </div>
      </div>

      <!-- Summary stats -->
      <div class="grid grid-cols-3 gap-4">
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-green-600">{{ document.correct_fields }}</div>
          <div class="text-sm text-gray-500">Correct Fields</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-red-600">{{ document.total_fields - document.correct_fields }}</div>
          <div class="text-sm text-gray-500">Incorrect Fields</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-gray-800">{{ document.total_fields }}</div>
          <div class="text-sm text-gray-500">Total Fields</div>
        </div>
      </div>
    </div>

    <!-- Field-by-field analysis -->
    <div class="bg-white rounded-lg border p-6 shadow-sm">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">Field-by-Field Analysis</h3>
      <div class="space-y-4">
        <div
          v-for="(fieldDetail, fieldName) in document.field_details"
          :key="fieldName"
          class="border rounded-lg p-4"
          :class="{
            'border-green-200 bg-green-50': fieldDetail.is_correct,
            'border-red-200 bg-red-50': !fieldDetail.is_correct
          }"
        >
          <div class="flex justify-between items-start mb-3">
            <h4 class="font-medium text-gray-900">{{ fieldName }}</h4>
            <span
              class="px-2 py-1 rounded-full text-xs font-medium"
              :class="{
                'bg-green-100 text-green-800': fieldDetail.is_correct,
                'bg-red-100 text-red-800': !fieldDetail.is_correct
              }"
            >
              {{ fieldDetail.is_correct ? 'Correct' : fieldDetail.error_type || 'Incorrect' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="bg-white border rounded p-3">
              <h5 class="text-xs font-medium text-gray-700 mb-1">Ground Truth</h5>
              <p class="text-sm text-gray-800">{{ formatFieldValue(fieldDetail.ground_truth_value) }}</p>
            </div>
            <div class="bg-white border rounded p-3">
              <h5 class="text-xs font-medium text-gray-700 mb-1">Predicted</h5>
              <p class="text-sm text-gray-800">{{ formatFieldValue(fieldDetail.predicted_value) }}</p>
            </div>
          </div>

          <div v-if="fieldDetail.confidence_score !== null" class="mt-3">
            <div class="flex items-center justify-between text-xs text-gray-600 mb-1">
              <span>Confidence Score</span>
              <span>{{ (fieldDetail.confidence_score * 100).toFixed(1) }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="h-2 rounded-full"
                :class="{
                  'bg-green-500': fieldDetail.confidence_score >= 0.8,
                  'bg-yellow-500': fieldDetail.confidence_score >= 0.5 && fieldDetail.confidence_score < 0.8,
                  'bg-red-500': fieldDetail.confidence_score < 0.5
                }"
                :style="{width: `${fieldDetail.confidence_score * 100}%`}"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Document content -->
    <div class="bg-white rounded-lg border p-6 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-gray-800">Document Content</h3>
        <button
          v-if="!documentContent && !loadingContent"
          @click="$emit('load-content', document.document_id)"
          class="text-blue-600 hover:text-blue-800 text-sm underline"
        >
          Load Content
        </button>
      </div>

      <div v-if="documentContent" class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96 border border-gray-200">
        <div class="text-sm text-gray-800 whitespace-pre-wrap">{{ documentContent }}</div>
      </div>
      <div v-else-if="loadingContent" class="text-center py-8">
        <div class="inline-block animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        <p class="mt-2 text-gray-500 text-sm">Loading document content...</p>
      </div>
      <div v-else class="text-center py-8">
        <span class="text-4xl text-gray-400 mb-2 block">📄</span>
        <p class="text-sm text-gray-500">Click "Load Content" to view document text</p>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  evaluation: {
    type: Object,
    required: true
  },
  document: {
    type: Object,
    required: true
  },
  documentContent: {
    type: String,
    default: null
  },
  loadingContent: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['load-content', 'back-to-documents']);

const formatFieldValue = (value) => {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};
</script>
