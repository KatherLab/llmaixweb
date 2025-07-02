<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-4xl max-h-[90vh] flex flex-col"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Field Errors: {{ fieldName }}</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="isLoading" class="text-center py-12">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading field errors...</p>
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

          <div v-else>
            <!-- Error Summary -->
            <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div class="flex">
                <svg class="w-5 h-5 text-red-400 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
                <div>
                  <h3 class="text-sm font-medium text-red-800">Field Errors for "{{ fieldName }}"</h3>
                  <p class="mt-1 text-sm text-red-700">
                    {{ fieldErrors.length }} error(s) found for this field across different documents.
                  </p>
                </div>
              </div>
            </div>

            <!-- Error List -->
            <div class="space-y-4">
              <div
                v-for="fieldError in fieldErrors"
                :key="`${fieldError.document_id}-${fieldError.field_name}`"
                class="border border-red-200 rounded-lg p-4 bg-red-50"
              >
                <div class="flex justify-between items-start mb-3">
                  <div>
                    <h4 class="text-sm font-medium text-red-800">Document #{{ fieldError.document_id }}</h4>
                    <p class="text-xs text-red-600 mt-1">{{ fieldError.document_name || 'Unknown file' }}</p>
                  </div>
                  <div class="text-xs text-gray-500">
                    Error Type: {{ fieldError.error_type }}
                  </div>
                </div>

                <!-- Error comparison -->
                <div class="grid grid-cols-2 gap-4 mb-3">
                  <div class="bg-white border border-green-200 rounded p-3">
                    <h5 class="text-xs font-medium text-green-700 mb-1">Ground Truth</h5>
                    <p class="text-sm text-gray-800">{{ fieldError.ground_truth_value || 'No value' }}</p>
                  </div>
                  <div class="bg-white border border-red-200 rounded p-3">
                    <h5 class="text-xs font-medium text-red-700 mb-1">Predicted</h5>
                    <p class="text-sm text-gray-800">{{ fieldError.predicted_value || 'No value' }}</p>
                  </div>
                </div>

                <!-- Additional details -->
                <div class="mt-3 bg-white border border-gray-200 rounded p-3">
                  <h5 class="text-xs font-medium text-gray-700 mb-2">Error Analysis:</h5>
                  <div class="text-xs text-gray-600 space-y-1">
                    <div><strong>Error Type:</strong> {{ getErrorTypeDescription(fieldError.error_type) }}</div>
                    <div v-if="fieldError.confidence_score !== null">
                      <strong>Confidence:</strong> {{ (fieldError.confidence_score * 100).toFixed(1) }}%
                    </div>
                    <div><strong>Suggestion:</strong> {{ getErrorSuggestion(fieldError.error_type) }}</div>
                  </div>

                  <!-- Context if available -->
                  <div v-if="fieldError.context" class="mt-2">
                    <h6 class="text-xs font-medium text-gray-700 mb-1">Document Context:</h6>
                    <p class="text-xs text-gray-600 bg-gray-50 p-2 rounded">{{ fieldError.context }}</p>
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
  fieldName: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close']);

const toast = useToast();
const isLoading = ref(false);
const error = ref(null);
const fieldErrors = ref([]);

// Error analysis functions
const getErrorTypeDescription = (errorType) => {
  const descriptions = {
    'missing': 'Field was not extracted from the document',
    'mismatch': 'Extracted value does not match ground truth',
    'fuzzy_mismatch': 'Extracted value is similar but not close enough to ground truth',
    'numeric_mismatch': 'Numeric value is outside acceptable tolerance',
    'boolean_mismatch': 'Boolean value is incorrect',
    'category_mismatch': 'Category value does not match expected options',
    'date_mismatch': 'Date value is incorrect or in wrong format',
    'type_error': 'Value type is incorrect (e.g., text instead of number)',
    'extra': 'Field was extracted but not expected in ground truth'
  };
  return descriptions[errorType] || 'Unknown error type';
};

const getErrorSuggestion = (errorType) => {
  const suggestions = {
    'missing': 'Check if the field exists in the document or improve extraction prompts',
    'mismatch': 'Review extraction accuracy or ground truth data',
    'fuzzy_mismatch': 'Consider adjusting fuzzy matching threshold or improving extraction',
    'numeric_mismatch': 'Check numeric parsing or adjust tolerance settings',
    'boolean_mismatch': 'Review boolean value mapping or extraction logic',
    'category_mismatch': 'Verify category mappings or improve classification',
    'date_mismatch': 'Check date format parsing or improve date extraction',
    'type_error': 'Review data type conversion or schema definition',
    'extra': 'Check if this field should be included in ground truth'
  };
  return suggestions[errorType] || 'Review extraction logic and ground truth data';
};

// Load field errors
const fetchFieldErrors = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await api.get(
      `/project/${props.projectId}/evaluation/${props.evaluation.id}/errors?field_name=${props.fieldName}&limit=50`
    );
    fieldErrors.value = response.data;
  } catch (err) {
    console.error('Failed to load field errors:', err);
    error.value = `Failed to load field errors: ${err.response?.data?.detail || err.message}`;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchFieldErrors();
});
</script>
