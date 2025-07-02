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
          <h3 class="text-lg font-medium text-gray-900">Evaluation Errors</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="isLoading" class="text-center py-12">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading error details...</p>
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
                  <h3 class="text-sm font-medium text-red-800">Evaluation Issues Found</h3>
                  <p class="mt-1 text-sm text-red-700">
                    {{ errorDocuments.length }} document(s) encountered errors during evaluation.
                    These errors typically occur when documents cannot be matched with ground truth data.
                  </p>
                </div>
              </div>
            </div>

            <!-- Error Details -->
            <div class="space-y-4">
              <div
                v-for="errorDoc in errorDocuments"
                :key="errorDoc.document_id"
                class="border border-red-200 rounded-lg p-4 bg-red-50"
              >
                <div class="flex justify-between items-start mb-3">
                  <div>
                    <h4 class="text-sm font-medium text-red-800">Document #{{ errorDoc.document_id }}</h4>
                    <p class="text-xs text-red-600 mt-1">{{ errorDoc.error }}</p>
                  </div>
                  <div class="text-xs text-gray-500">
                    {{ errorDoc.filename || 'Unknown file' }}
                  </div>
                </div>

                <!-- Error details -->
                <div class="mt-3 bg-white border border-red-100 rounded p-3">
                  <h5 class="text-xs font-medium text-gray-700 mb-2">Error Details:</h5>
                  <div class="text-xs text-gray-600 space-y-1">
                    <div><strong>Type:</strong> {{ getErrorType(errorDoc.error) }}</div>
                    <div><strong>Possible Cause:</strong> {{ getErrorCause(errorDoc.error) }}</div>
                    <div><strong>Suggestion:</strong> {{ getErrorSuggestion(errorDoc.error) }}</div>
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
import { ref, onMounted, computed } from 'vue';
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
  }
});

const emit = defineEmits(['close']);

const toast = useToast();
const isLoading = ref(false);
const error = ref(null);
const errorDocuments = ref([]);

// Extract error documents from evaluation
const extractErrorDocuments = () => {
  if (!props.evaluation.document_summaries && !props.evaluation.document_metrics) {
    return [];
  }

  const documents = props.evaluation.document_summaries || props.evaluation.document_metrics || [];
  return documents.filter(doc => doc.error || doc.has_error);
};

// Error analysis functions
const getErrorType = (errorMessage) => {
  if (errorMessage.includes('No ground truth found')) {
    return 'Ground Truth Matching Error';
  } else if (errorMessage.includes('Document not found')) {
    return 'Document Reference Error';
  } else if (errorMessage.includes('Invalid document ID')) {
    return 'Data Type Error';
  } else {
    return 'Unknown Error';
  }
};

const getErrorCause = (errorMessage) => {
  if (errorMessage.includes('No ground truth found')) {
    return 'Document ID or filename does not match any key in the ground truth data';
  } else if (errorMessage.includes('Document not found')) {
    return 'Document exists in trial results but not in the database';
  } else if (errorMessage.includes('Invalid document ID')) {
    return 'Document ID is not a valid integer or is corrupted';
  } else {
    return 'An unexpected error occurred during evaluation';
  }
};

const getErrorSuggestion = (errorMessage) => {
  if (errorMessage.includes('No ground truth found')) {
    return 'Check that ground truth keys match document IDs or filenames. Consider using fuzzy matching or updating ground truth data.';
  } else if (errorMessage.includes('Document not found')) {
    return 'Verify database integrity. Document may have been deleted after trial completion.';
  } else if (errorMessage.includes('Invalid document ID')) {
    return 'Check trial result data integrity. Re-run the trial if necessary.';
  } else {
    return 'Contact support with the error details for further assistance.';
  }
};

onMounted(() => {
  errorDocuments.value = extractErrorDocuments();
});
</script>

