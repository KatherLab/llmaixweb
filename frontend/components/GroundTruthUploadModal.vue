<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-lg overflow-hidden"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Upload Ground Truth</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="px-6 py-4">
          <form @submit.prevent="uploadGroundTruth">
            <div class="space-y-4">
              <div>
                <label for="ground-truth-name" class="block text-sm font-medium text-gray-700">Name (optional)</label>
                <input
                  id="ground-truth-name"
                  v-model="groundTruthName"
                  type="text"
                  class="mt-1 block w-full rounded-md border border-gray-300 shadow-sm py-2 px-3 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                  placeholder="Ground truth file name"
                />
              </div>
              <div>
                <label for="ground-truth-format" class="block text-sm font-medium text-gray-700">Format</label>
                <select
                  id="ground-truth-format"
                  v-model="groundTruthFormat"
                  class="mt-1 block w-full rounded-md border border-gray-300 shadow-sm py-2 px-3 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                >
                  <option value="csv">CSV (flattened fields with dots)</option>
                  <option value="json">JSON (single file with document map or multiple files)</option>
                  <option value="zip">ZIP (multiple JSON files)</option>
                </select>
              </div>

              <!-- Add info box for JSON -->
              <div v-if="groundTruthFormat === 'json' || groundTruthFormat === 'zip'"
                   class="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
                <p class="text-sm text-blue-700">
                  <strong>Important:</strong> Each document must have an 'id' field that matches your document identifiers.
                </p>
              </div>

              <div>
                <label for="file-upload" class="block text-sm font-medium text-gray-700">File(s)</label>
                <div
                  class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md"
                  @dragover.prevent
                  @drop.prevent="handleFileDrop"
                >
                  <div class="space-y-1 text-center">
                    <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                      <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                    <div class="flex text-sm text-gray-600 justify-center">
                      <label for="file-upload" class="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none">
                        <span>Upload file(s)</span>
                        <input
                          id="file-upload"
                          name="file-upload"
                          type="file"
                          class="sr-only"
                          :accept="acceptedFileTypes"
                          :multiple="groundTruthFormat === 'json'"
                          @change="handleFileSelect"
                        />
                      </label>
                      <p class="pl-1">or drag and drop</p>
                    </div>
                    <p class="text-xs text-gray-500">
                      <template v-if="groundTruthFormat === 'csv'">CSV file with flattened fields (dots for nesting)</template>
                      <template v-else-if="groundTruthFormat === 'json'">JSON file(s) - single file or multiple files</template>
                      <template v-else-if="groundTruthFormat === 'zip'">ZIP file containing JSON files</template>
                    </p>
                  </div>
                </div>
                <div v-if="selectedFiles.length > 0" class="mt-2">
                  <p class="text-sm font-medium text-gray-700 mb-1">Selected files:</p>
                  <ul class="text-sm text-gray-600 space-y-1">
                    <li v-for="(file, index) in selectedFiles" :key="index" class="flex items-center justify-between">
                      <span>{{ file.name }}</span>
                      <button
                        v-if="groundTruthFormat === 'json' && selectedFiles.length > 1"
                        @click="removeFile(index)"
                        type="button"
                        class="text-red-600 hover:text-red-800"
                      >
                        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <div class="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                @click="$emit('close')"
                class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                :disabled="isUploading || selectedFiles.length === 0"
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
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close', 'uploaded']);
const toast = useToast();

const groundTruthName = ref('');
const groundTruthFormat = ref('csv');
const selectedFiles = ref([]);
const isUploading = ref(false);

const acceptedFileTypes = computed(() => {
  switch (groundTruthFormat.value) {
    case 'json':
      return '.json';
    case 'zip':
      return '.zip';
    case 'csv':
      return '.csv';
    default:
      return '.csv,.json,.zip';
  }
});

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  if (groundTruthFormat.value === 'json') {
    // For JSON, allow multiple files
    selectedFiles.value = files;
  } else {
    // For CSV and ZIP, only allow single file
    selectedFiles.value = files.slice(0, 1);
  }
};

const handleFileDrop = (event) => {
  const files = Array.from(event.dataTransfer.files);
  if (groundTruthFormat.value === 'json') {
    selectedFiles.value = files.filter(f => f.name.endsWith('.json'));
  } else {
    selectedFiles.value = files.slice(0, 1);
  }
};

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1);
};

const uploadGroundTruth = async () => {
  if (selectedFiles.value.length === 0) {
    toast.warning('Please select at least one file to upload');
    return;
  }

  isUploading.value = true;

  try {
    let response;

    if (groundTruthFormat.value === 'json' && selectedFiles.value.length > 1) {
      // Multiple JSON files - create a ZIP in memory
      const { default: JSZip } = await import('jszip');
      const zip = new JSZip();

      // Add each JSON file to the ZIP
      for (const file of selectedFiles.value) {
        const content = await file.text();
        zip.file(file.name, content);
      }

      // Generate ZIP blob
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const zipFile = new File([zipBlob], 'ground_truth.zip', { type: 'application/zip' });

      const formData = new FormData();
      formData.append('file', zipFile);
      formData.append('name', groundTruthName.value || 'JSON Ground Truth');
      formData.append('format', 'zip');

      response = await api.post(`/project/${props.projectId}/groundtruth`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
    } else {
      // Single file upload (CSV, ZIP, or single JSON)
      const formData = new FormData();
      formData.append('file', selectedFiles.value[0]);
      formData.append('name', groundTruthName.value || selectedFiles.value[0].name);
      formData.append('format', groundTruthFormat.value);

      response = await api.post(`/project/${props.projectId}/groundtruth`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
    }

    emit('uploaded', response.data);
    toast.success('Ground truth uploaded successfully');
  } catch (err) {
    const errorMessage = err.response?.data?.detail || err.message;
    toast.error(`Failed to upload ground truth: ${errorMessage}`);
    console.error(err);
  } finally {
    isUploading.value = false;
  }
};
</script>
