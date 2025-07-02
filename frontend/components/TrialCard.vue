<template>
  <div class="border rounded-lg overflow-hidden bg-white shadow-sm">
    <div class="p-4">
      <div class="flex flex-col md:flex-row md:justify-between md:items-center">
        <div>
          <h3 class="font-medium flex items-center">
            Trial #{{ trial.id }}
            <span :class="['ml-2 text-xs px-2 py-1 rounded-full', statusClass]">
              {{ trial.status }}
            </span>
          </h3>
          <p class="text-sm text-gray-500">
            {{ trial.document_ids.length }} document(s) • Started {{ formatDate(trial.created_at) }}
          </p>
          <p class="text-sm mt-1">
            Model: {{ trial.llm_model }}
          </p>
        </div>

        <div class="mt-3 md:mt-0 space-y-3 md:text-right md:flex md:flex-col md:items-end">
          <div v-if="resultSummary" class="text-sm text-green-600">
            {{ resultSummary }}
          </div>

          <div v-if="isActive" class="md:w-32 space-y-1">
            <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                class="h-full bg-blue-500 transition-all duration-300 ease-out"
                :style="{ width: progressPercentage !== null ? `${progressPercentage}%` : '0%' }"
              ></div>
            </div>
            <p class="text-xs text-gray-500">
              {{ progressPercentage !== null ? `${progressPercentage}%` : 'Processing...' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Expandable Results Section -->
    <div v-if="trial.results && trial.results.length > 0" class="border-t">
      <button
        @click="toggleResults"
        class="w-full px-4 py-2 text-sm text-left flex items-center justify-between hover:bg-gray-50"
      >
        <span>View Results ({{ trial.results.length }} documents)</span>
        <svg
          class="w-5 h-5 transform transition-transform"
          :class="{ 'rotate-180': showResults }"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>

      <div v-if="showResults" class="p-4 bg-gray-50">
        <!-- Results navigation tabs -->
        <div class="mb-4 border-b">
          <div class="flex overflow-x-auto">
            <button
              v-for="(result, index) in trial.results"
              :key="index"
              @click="selectedResultIndex = index"
              :class="[
                'px-3 py-2 text-sm whitespace-nowrap',
                selectedResultIndex === index
                  ? 'border-b-2 border-blue-500 font-medium text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              ]"
            >
              Document #{{ index + 1 }}
            </button>
          </div>
        </div>

        <!-- Selected result display -->
        <div v-if="currentResult" class="bg-gray-50 p-4 rounded-md overflow-x-auto">
          <pre class="text-xs text-gray-800">{{ prettyJson(currentResult.result) }}</pre>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="mt-4 flex justify-end gap-2 p-4">
      <!-- Download button -->
      <button
        v-if="trial.results && trial.results.length > 0"
        @click="toggleDownloadModal"
        class="px-3 py-1.5 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm flex items-center"
      >
        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download
      </button>

      <!-- View Results (route to detailed view) -->
      <button
        v-if="trial.results && trial.results.length > 0"
        @click="emit('view', trial)"
        class="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
      >
        Details
      </button>

      <!-- Retry button -->
      <button
        v-if="trial.status === 'completed' || trial.status === 'failed'"
        @click="emit('retry', trial)"
        class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm"
      >
        Retry
      </button>

      <!-- Delete button -->
      <button
        @click="emit('delete', trial)"
        class="px-3 py-1.5 bg-white hover:bg-gray-100 text-red-600 rounded-md border border-gray-300 text-sm"
      >
        Delete
      </button>
    </div>

    <!-- Download Modal -->
    <div v-if="showDownloadModal" class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50" @click.self="showDownloadModal = false">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-medium">Download Trial Results</h3>
          <button @click="showDownloadModal = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">Format</label>
            <div class="mt-2 space-y-2">
              <div class="flex items-center">
                <input
                  id="format-json"
                  v-model="downloadFormat"
                  type="radio"
                  value="json"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                />
                <label for="format-json" class="ml-2 block text-sm text-gray-700">
                  JSON (one file per document, zipped)
                </label>
              </div>
              <div class="flex items-center">
                <input
                  id="format-csv"
                  v-model="downloadFormat"
                  type="radio"
                  value="csv"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                />
                <label for="format-csv" class="ml-2 block text-sm text-gray-700">
                  CSV (flattened structure)
                </label>
              </div>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">Options</label>
            <div class="mt-2">
              <div class="flex items-center">
                <input
                  id="include-content"
                  v-model="includeContent"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="include-content" class="ml-2 block text-sm text-gray-700">
                  Include document text
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 flex justify-end space-x-3">
          <button
            @click="showDownloadModal = false"
            class="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="downloadResults"
            :disabled="isDownloading"
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-blue-300 disabled:cursor-not-allowed flex items-center"
          >
            <svg v-if="isDownloading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ isDownloading ? 'Downloading...' : 'Download' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { formatDate } from '@/utils/formatters';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';

const props = defineProps({
  trial: {
    type: Object,
    required: true
  },
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['view', 'retry', 'delete']);
const toast = useToast();

// State variables
const showResults = ref(false);
const selectedResultIndex = ref(0);
const showDownloadModal = ref(false);
const downloadFormat = ref('json');
const includeContent = ref(true);
const isDownloading = ref(false);

// Format progress as percentage
const progressPercentage = computed(() => {
  if (!props.trial.progress && props.trial.progress !== 0) return null;
  return Math.round(props.trial.progress * 100);
});

// Determine if the trial is active (in progress)
const isActive = computed(() => {
  return !['completed', 'failed'].includes(props.trial.status);
});

// Compute status display classes
const statusClass = computed(() => {
  const statusMap = {
    'pending': 'bg-yellow-100 text-yellow-800',
    'processing': 'bg-blue-100 text-blue-800',
    'completed': 'bg-green-100 text-green-800',
    'failed': 'bg-red-100 text-red-800'
  };
  return statusMap[props.trial.status] || 'bg-gray-100 text-gray-800';
});

// Get trial results summary
const resultSummary = computed(() => {
  if (!props.trial.results || props.trial.results.length === 0) {
    return null;
  }
  return props.trial.results.length === 1
    ? '1 document processed'
    : `${props.trial.results.length} documents processed`;
});

// Toggle results visibility
const toggleResults = () => {
  showResults.value = !showResults.value;
};

// Get currently selected result
const currentResult = computed(() => {
  if (!props.trial.results || props.trial.results.length === 0) {
    return null;
  }

  return props.trial.results[selectedResultIndex.value] || props.trial.results[0];
});

// Format JSON for display
const prettyJson = (obj) => {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (e) {
    return 'Invalid JSON';
  }
};

// Toggle download modal
const toggleDownloadModal = () => {
  showDownloadModal.value = !showDownloadModal.value;
};

// Download trial results function
const downloadResults = async () => {
  if (isDownloading.value) return;

  isDownloading.value = true;
  try {
    const response = await api.get(
      `/project/${props.projectId}/trial/${props.trial.id}/download?format=${downloadFormat.value}&include_content=${includeContent.value}`,
      { responseType: 'blob' }
    );

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;

    // Use appropriate file extension based on format and content
    const fileExt = (downloadFormat.value === 'json' || (downloadFormat.value === 'csv' && includeContent.value)) ? 'zip' : downloadFormat.value;
    link.setAttribute('download', `trial_${props.trial.id}_results.${fileExt}`);

    document.body.appendChild(link);
    link.click();
    link.remove();

    toast.success('Trial results downloaded successfully');
    showDownloadModal.value = false;
  } catch (err) {
    toast.error(`Failed to download trial results: ${err.message}`);
    console.error(err);
  } finally {
    isDownloading.value = false;
  }
};
</script>
