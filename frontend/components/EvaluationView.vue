<template>
  <div class="evaluation-view p-4">
    <div class="header flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Evaluation</h1>
        <p class="text-gray-600">Compare trial results against ground truth data</p>
      </div>
      <div class="flex gap-2">
        <button
          @click="showUploadModal = true"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
          :disabled="isLoading"
        >
          Upload Ground Truth
        </button>
        <button
          v-if="groundTruthFiles.length > 0"
          @click="downloadMetrics"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-green-600 text-white hover:bg-green-700 disabled:bg-green-300 disabled:cursor-not-allowed"
          :disabled="isLoading || !selectedGroundTruth"
        >
          <span class="flex items-center">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Metrics
          </span>
        </button>
      </div>
    </div>

    <ErrorBanner v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading" />

    <!-- No ground truth files yet -->
    <EmptyState
      v-else-if="groundTruthFiles.length === 0"
      title="No ground truth files yet"
      description="Upload ground truth data to evaluate your trial results"
      actionText="Upload Ground Truth"
      @action="showUploadModal = true"
    >
      <template #icon>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </template>
    </EmptyState>

    <!-- Ground truth file selection and evaluation display -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Ground truth files panel -->
      <div class="bg-white shadow-sm rounded-lg p-4">
        <h2 class="font-medium mb-3">Ground Truth Files</h2>
        <div class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="(gt, index) in groundTruthFiles"
            :key="gt.id"
            class="border rounded-lg p-3 hover:bg-gray-50"
            :class="{ 'border-blue-500 bg-blue-50': selectedGroundTruth?.id === gt.id }"
          >
            <div class="flex justify-between items-center">
              <div>
                <div class="font-medium">{{ gt.name || `Ground Truth #${index + 1}` }}</div>
                <div class="text-sm text-gray-500">{{ formatDate(gt.created_at) }}</div>
              </div>
              <div class="flex gap-2">
                <button
                  @click="selectGroundTruth(gt)"
                  class="p-1 text-blue-600 hover:text-blue-800"
                  :class="{ 'bg-blue-100 rounded': selectedGroundTruth?.id === gt.id }"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
                <button @click="deleteGroundTruth(gt)" class="p-1 text-red-600 hover:text-red-800">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Evaluation results panel -->
      <div class="bg-white shadow-sm rounded-lg p-4 lg:col-span-2">
        <h2 class="font-medium mb-3">Evaluation Results</h2>

        <div v-if="!selectedGroundTruth" class="text-center py-8 text-gray-500">
          Select a ground truth file to view evaluation results
        </div>

        <div v-else-if="!evaluationResults.length" class="text-center py-8 text-gray-500">
          No trials have been evaluated yet
        </div>

        <div v-else>
          <!-- Trial summary metrics -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trial</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accuracy</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">F1 Score</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Details</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="result in evaluationResults" :key="result.trial_id">
                  <td class="px-4 py-3 whitespace-nowrap text-sm">Trial #{{ result.trial_id }}</td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">{{ result.model }}</td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="flex items-center">
                      <div class="mr-2">{{ (result.metrics.accuracy * 100).toFixed(1) }}%</div>
                      <div class="w-16 bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" :style="{width: `${result.metrics.accuracy * 100}%`}"></div>
                      </div>
                    </div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="flex items-center">
                      <div class="mr-2">{{ (result.metrics.f1_score * 100).toFixed(1) }}%</div>
                      <div class="w-16 bg-gray-200 rounded-full h-2">
                        <div class="bg-green-600 h-2 rounded-full" :style="{width: `${result.metrics.f1_score * 100}%`}"></div>
                      </div>
                    </div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <button
                      @click="viewTrialEvaluation(result)"
                      class="text-blue-600 hover:text-blue-800 underline"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Detailed view for selected trial evaluation -->
          <div v-if="selectedTrialEvaluation" class="mt-6 border-t pt-4">
            <h3 class="font-medium mb-3">Detailed Evaluation: Trial #{{ selectedTrialEvaluation.trial_id }}</h3>

            <div class="mb-4 flex justify-between items-center">
              <div class="text-sm text-gray-500">
                {{ selectedTrialEvaluation.document_count }} documents evaluated
              </div>
              <div class="flex gap-3">
                <div class="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
                  Accuracy: {{ (selectedTrialEvaluation.metrics.accuracy * 100).toFixed(1) }}%
                </div>
                <div class="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">
                  F1: {{ (selectedTrialEvaluation.metrics.f1_score * 100).toFixed(1) }}%
                </div>
              </div>
            </div>

            <!-- Document-level metrics -->
            <div class="bg-gray-50 p-4 rounded-md overflow-x-auto">
              <h4 class="font-medium mb-2">Document-Level Results</h4>
              <table class="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th class="px-3 py-2 bg-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Document</th>
                    <th class="px-3 py-2 bg-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accuracy</th>
                    <th class="px-3 py-2 bg-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fields Correct</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="(doc, idx) in selectedTrialEvaluation.documents" :key="idx">
                    <td class="px-3 py-2 whitespace-nowrap text-sm">Document #{{ doc.document_id }}</td>
                    <td class="px-3 py-2 whitespace-nowrap text-sm">
                      {{ (doc.accuracy * 100).toFixed(1) }}%
                    </td>
                    <td class="px-3 py-2 whitespace-nowrap text-sm">
                      {{ doc.fields_correct }}/{{ doc.total_fields }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Field-level metrics -->
            <div class="mt-4 bg-gray-50 p-4 rounded-md overflow-x-auto">
              <h4 class="font-medium mb-2">Field-Level Results</h4>
              <table class="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th class="px-3 py-2 bg-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Field</th>
                    <th class="px-3 py-2 bg-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accuracy</th>
                    <th class="px-3 py-2 bg-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precision</th>
                    <th class="px-3 py-2 bg-gray-100 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recall</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="(field, fieldName) in selectedTrialEvaluation.fields" :key="fieldName">
                    <td class="px-3 py-2 whitespace-nowrap text-sm">{{ fieldName }}</td>
                    <td class="px-3 py-2 whitespace-nowrap text-sm">
                      {{ (field.accuracy * 100).toFixed(1) }}%
                    </td>
                    <td class="px-3 py-2 whitespace-nowrap text-sm">
                      {{ (field.precision * 100).toFixed(1) }}%
                    </td>
                    <td class="px-3 py-2 whitespace-nowrap text-sm">
                      {{ (field.recall * 100).toFixed(1) }}%
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Upload ground truth modal -->
    <ModalDialog
      v-if="showUploadModal"
      title="Upload Ground Truth"
      @close="showUploadModal = false"
    >
      <form @submit.prevent="uploadGroundTruth">
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">Name (optional)</label>
            <input
              v-model="groundTruthName"
              type="text"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Ground truth file name"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">Format</label>
            <select
              v-model="groundTruthFormat"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="json">JSON (one file per document)</option>
              <option value="csv">CSV (all documents in one file)</option>
              <option value="xlsx">XLSX (all documents in one file)</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">File</label>
            <div
              class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md"
              @dragover.prevent
              @drop.prevent="handleFileDrop"
            >
              <div class="space-y-1 text-center">
                <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                  <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <div class="flex text-sm text-gray-600">
                  <label for="file-upload" class="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none">
                    <span>Upload a file</span>
                    <input
                      id="file-upload"
                      name="file-upload"
                      type="file"
                      class="sr-only"
                      @change="handleFileSelect"
                    />
                  </label>
                  <p class="pl-1">or drag and drop</p>
                </div>
                <p class="text-xs text-gray-500">
                  {{ groundTruthFormat === 'json' ? 'ZIP of JSON files' : groundTruthFormat.toUpperCase() }}
                </p>
              </div>
            </div>
            <div v-if="selectedFile" class="mt-2 text-sm text-gray-600">
              Selected: {{ selectedFile.name }}
            </div>
          </div>

          <div v-if="groundTruthFormat !== 'json'">
            <label class="block text-sm font-medium text-gray-700">Comparison Options</label>
            <div class="mt-2 space-y-2">
              <div class="flex items-center">
                <input
                  id="ignore-case"
                  v-model="comparisonOptions.ignoreCase"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="ignore-case" class="ml-2 block text-sm text-gray-700">
                  Ignore case when comparing
                </label>
              </div>
              <div class="flex items-center">
                <input
                  id="category-matching"
                  v-model="comparisonOptions.categoryMatching"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="category-matching" class="ml-2 block text-sm text-gray-700">
                  Enable category matching (e.g., "yes"="1"="true")
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 flex justify-end space-x-3">
          <button
            type="button"
            @click="showUploadModal = false"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            :disabled="isUploading || !selectedFile"
          >
            <span v-if="isUploading" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Uploading...
            </span>
            <span v-else>Upload</span>
          </button>
        </div>
      </form>
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters';
import { useToast } from 'vue-toastification';
import ModalDialog from '@/components/ModalDialog.vue';
import ErrorBanner from '@/components/ErrorBanner.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import EmptyState from '@/components/EmptyState.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const toast = useToast();
const isLoading = ref(false);
const error = ref(null);
const groundTruthFiles = ref([]);
const selectedGroundTruth = ref(null);
const evaluationResults = ref([]);
const selectedTrialEvaluation = ref(null);
const showUploadModal = ref(false);

// Upload form state
const groundTruthName = ref('');
const groundTruthFormat = ref('json');
const selectedFile = ref(null);
const isUploading = ref(false);
const comparisonOptions = ref({
  ignoreCase: true,
  categoryMatching: false
});

// Load ground truth files
const fetchGroundTruthFiles = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/groundtruth`);
    groundTruthFiles.value = response.data;
    // Select the first one by default if available
    if (groundTruthFiles.value.length > 0 && !selectedGroundTruth.value) {
      selectGroundTruth(groundTruthFiles.value[0]);
    }
  } catch (err) {
    error.value = `Failed to load ground truth files: ${err.message}`;
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Select a ground truth file and load evaluations
const selectGroundTruth = async (groundTruth) => {
  selectedGroundTruth.value = groundTruth;
  selectedTrialEvaluation.value = null;

  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/evaluation?groundtruth_id=${groundTruth.id}`);
    evaluationResults.value = response.data;
  } catch (err) {
    error.value = `Failed to load evaluation results: ${err.message}`;
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// View detailed evaluation for a trial
const viewTrialEvaluation = async (evaluation) => {
  selectedTrialEvaluation.value = null;
  isLoading.value = true;

  try {
    const response = await api.get(`/project/${props.projectId}/evaluation/${evaluation.id}`);
    selectedTrialEvaluation.value = response.data;
  } catch (err) {
    error.value = `Failed to load trial evaluation details: ${err.message}`;
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Delete ground truth file
const deleteGroundTruth = async (groundTruth) => {
  if (!confirm(`Are you sure you want to delete this ground truth file?`)) {
    return;
  }

  try {
    await api.delete(`/project/${props.projectId}/groundtruth/${groundTruth.id}`);

    // Remove from list and reset selection if needed
    groundTruthFiles.value = groundTruthFiles.value.filter(gt => gt.id !== groundTruth.id);
    if (selectedGroundTruth.value?.id === groundTruth.id) {
      selectedGroundTruth.value = groundTruthFiles.value.length > 0 ? groundTruthFiles.value[0] : null;
      evaluationResults.value = [];
      selectedTrialEvaluation.value = null;
    }

    toast.success('Ground truth file deleted successfully');
  } catch (err) {
    toast.error(`Failed to delete ground truth file: ${err.message}`);
    console.error(err);
  }
};

// File selection handlers
const handleFileSelect = (event) => {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
  }
};

const handleFileDrop = (event) => {
  const file = event.dataTransfer.files[0];
  if (file) {
    selectedFile.value = file;
  }
};

// Upload ground truth file
const uploadGroundTruth = async () => {
  if (!selectedFile.value) {
    toast.warning('Please select a file to upload');
    return;
  }

  isUploading.value = true;

  const formData = new FormData();
  formData.append('file', selectedFile.value);
  formData.append('name', groundTruthName.value || selectedFile.value.name);
  formData.append('format', groundTruthFormat.value);

  if (groundTruthFormat.value !== 'json') {
    formData.append('comparison_options', JSON.stringify(comparisonOptions.value));
  }

  try {
    const response = await api.post(`/project/${props.projectId}/groundtruth`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    // Add the new ground truth file and select it
    groundTruthFiles.value.push(response.data);
    selectGroundTruth(response.data);

    toast.success('Ground truth file uploaded successfully');
    showUploadModal.value = false;

    // Reset form
    groundTruthName.value = '';
    selectedFile.value = null;
  } catch (err) {
    toast.error(`Failed to upload ground truth file: ${err.message}`);
    console.error(err);
  } finally {
    isUploading.value = false;
  }
};

// Download metrics as CSV
const downloadMetrics = async () => {
  if (!selectedGroundTruth.value) {
    return;
  }

  try {
    const response = await api.get(
      `/project/${props.projectId}/evaluation/download?groundtruth_id=${selectedGroundTruth.value.id}`,
      { responseType: 'blob' }
    );

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `evaluation_metrics_${props.projectId}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();

    toast.success('Metrics downloaded successfully');
  } catch (err) {
    toast.error(`Failed to download metrics: ${err.message}`);
    console.error(err);
  }
};

// Load data on mount
onMounted(() => {
  fetchGroundTruthFiles();
});
</script>
