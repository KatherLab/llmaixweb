<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-5xl max-h-[95vh] flex flex-col"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Document #{{ document.document_id }} Details</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="isLoading" class="text-center py-12">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading document details...</p>
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

          <div v-else-if="documentDetail">
            <!-- Document Header -->
            <div class="bg-gradient-to-r from-gray-50 to-white rounded-lg p-6 mb-6 border">
              <div class="flex justify-between items-start mb-4">
                <div>
                  <h2 class="text-xl font-semibold text-gray-800">Document #{{ documentDetail.document_id }}</h2>
                  <p class="text-gray-600">{{ documentDetail.document_name || 'Unknown filename' }}</p>
                </div>
                <div class="text-right">
                  <div class="text-2xl font-bold text-blue-600">
                    {{ (documentDetail.accuracy * 100).toFixed(1) }}%
                  </div>
                  <div class="text-sm text-gray-500">Accuracy</div>
                </div>
              </div>

              <!-- Summary stats -->
              <div class="grid grid-cols-3 gap-4">
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-green-600">{{ documentDetail.correct_fields }}</div>
                  <div class="text-sm text-gray-500">Correct Fields</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-red-600">{{ documentDetail.total_fields - documentDetail.correct_fields }}</div>
                  <div class="text-sm text-gray-500">Incorrect Fields</div>
                </div>
                <div class="bg-white rounded-lg p-4 text-center border">
                  <div class="text-lg font-semibold text-gray-800">{{ documentDetail.total_fields }}</div>
                  <div class="text-sm text-gray-500">Total Fields</div>
                </div>
              </div>
            </div>

            <!-- Field-by-field comparison -->
            <div class="bg-white rounded-lg border p-6">
              <h3 class="text-lg font-semibold text-gray-800 mb-4">Field-by-Field Analysis</h3>
              <div class="space-y-4">
                <div
                  v-for="(fieldDetail, fieldName) in documentDetail.field_details"
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
                      <p class="text-sm text-gray-800">{{ fieldDetail.ground_truth_value || 'No value' }}</p>
                    </div>
                    <div class="bg-white border rounded p-3">
                      <h5 class="text-xs font-medium text-gray-700 mb-1">Predicted</h5>
                      <p class="text-sm text-gray-800">{{ fieldDetail.predicted_value || 'No value' }}</p>
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
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
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
import { ref, onMounted } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';

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
  }
});

const emit = defineEmits(['close']);

const toast = useToast();
const isLoading = ref(false);
const error = ref(null);
const documentDetail = ref(null);

// Load document details
const fetchDocumentDetail = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await api.get(
      `/project/${props.projectId}/evaluation/${props.evaluation.id}/document/${props.document.document_id}`
    );
    documentDetail.value = response.data;
  } catch (err) {
    console.error('Failed to load document details:', err);
    error.value = `Failed to load document details: ${err.response?.data?.detail || err.message}`;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchDocumentDetail();
});
</script>
