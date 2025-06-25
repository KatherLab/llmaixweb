<!-- src/components/PreprocessingManagement.vue -->
<template>
  <div class="p-6">
    <h2 class="text-lg font-medium text-gray-900 mb-6">File Preprocessing</h2>
    <!-- Active Preprocessing Tasks -->
    <div v-if="preprocessingTasks.length > 0" class="mb-8">
      <h3 class="text-md font-medium text-gray-900 mb-4">Active Tasks</h3>
      <div class="space-y-4">
        <div
          v-for="task in preprocessingTasks"
          :key="task.id"
          class="border rounded-lg overflow-hidden bg-white shadow-sm"
        >
          <div class="p-4">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="font-medium text-gray-900">
                  Task #{{ task.id }}
                  <span
                    class="ml-2 text-xs font-medium px-2 py-1 rounded-full"
                    :class="{
                      'bg-blue-100 text-blue-800': task.status === 'processing',
                      'bg-green-100 text-green-800': task.status === 'completed',
                      'bg-red-100 text-red-800': task.status === 'failed',
                      'bg-yellow-100 text-yellow-800': task.status === 'pending'
                    }"
                  >
                    {{ formatStatus(task.status) }}
                  </span>
                </h4>
                <div class="mt-2 text-sm text-gray-600 space-y-1">
                  <p>{{ task.file_ids.length }} file(s) • Started {{ formatDate(task.created_at) }}</p>
                  <p>
                    <span class="font-medium">Method:</span>
                    {{ task.use_ocr ? `OCR (${task.ocr_backend || 'default'})` : 'Text Extraction' }} •
                    PDF Backend: {{ task.pdf_backend || 'default' }}
                  </p>
                  <p v-if="task.message" class="text-sm mt-1 italic">{{ task.message }}</p>
                </div>
              </div>
              <div class="text-right">
                <div v-if="task.status === 'processing'" class="space-y-1">
                  <div class="h-2 w-32 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-blue-600 transition-all duration-300 ease-out"
                      :style="{ width: `${(task.progress || 0) * 100}%` }"
                    ></div>
                  </div>
                  <p class="text-xs text-gray-500">
                    {{ Math.round((task.progress || 0) * 100) }}% complete
                    <template v-if="task.progress_details">
                      <span v-if="task.progress_details.processed_docs">
                        • {{ task.progress_details.processed_docs }} docs processed
                      </span>
                    </template>
                  </p>
                </div>
                <div v-if="task.status === 'failed'" class="mt-2">
                  <button
                    @click="retryPreprocessing(task)"
                    class="inline-flex items-center px-3 py-1 text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                  >
                    <svg class="h-3 w-3 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Retry
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- New Preprocessing Task Form -->
    <div class="border rounded-lg bg-white shadow-sm">
      <div class="border-b px-4 py-3">
        <h3 class="text-md font-medium text-gray-900">Create New Preprocessing Task</h3>
      </div>
      <div class="p-4">
        <div v-if="error" class="bg-red-50 p-4 text-red-500 rounded-md mb-4">
          {{ error }}
        </div>
        <form @submit.prevent="startPreprocessing">
          <!-- OCR Settings -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h4 class="font-medium text-gray-700 mb-3">OCR Settings</h4>
              <div class="space-y-4">
                <div class="flex items-center">
                  <input
                    id="use-ocr"
                    v-model="preprocessingConfig.use_ocr"
                    type="checkbox"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label for="use-ocr" class="ml-2 block text-sm text-gray-700">
                    Use OCR
                  </label>
                </div>
                <div class="flex items-center">
                  <input
                    id="force-ocr"
                    v-model="preprocessingConfig.force_ocr"
                    type="checkbox"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    :disabled="!preprocessingConfig.use_ocr"
                  />
                  <label for="force-ocr" class="ml-2 block text-sm text-gray-700">
                    Force OCR (ignore existing text layers)
                  </label>
                </div>
                <div>
                  <label for="ocr-backend" class="block text-sm font-medium text-gray-700 mb-1">OCR Backend</label>
                  <select
                    id="ocr-backend"
                    v-model="preprocessingConfig.ocr_backend"
                    class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                    :disabled="!preprocessingConfig.use_ocr"
                  >
                    <option value="ocrmypdf">OCRMYPDF</option>
                  </select>
                </div>
                <div v-if="preprocessingConfig.ocr_backend === 'ocrmypdf'" class="mt-4">
                  <label for="ocr-languages" class="block text-sm font-medium text-gray-700 mb-1">OCR Languages</label>
                  <Multiselect
                    v-model="preprocessingConfig.ocr_languages"
                    :options="ocrLanguagesForSelect"
                    mode="tags"
                    :searchable="true"
                    :close-on-select="false"
                    :clear-on-select="false"
                    :preserve-search="true"
                    :filter-results="false"
                    :hide-selected="false"
                    placeholder="Select languages"
                    label="label"
                    track-by="value"
                    class="w-full"
                  />
                </div>
              </div>
            </div>
            <div>
              <h4 class="font-medium text-gray-700 mb-3">PDF Settings</h4>
              <div>
                <label for="pdf-backend" class="block text-sm font-medium text-gray-700 mb-1">PDF Backend</label>
                <select
                  id="pdf-backend"
                  v-model="preprocessingConfig.pdf_backend"
                  class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                >
                  <option value="pymupdf4llm">PyMuPDF4LLM</option>
                  <option value="markitdown">MarkItDown</option>
                </select>
              </div>
            </div>
          </div>
          <!-- File Selection -->
          <div>
            <h4 class="font-medium text-gray-700 mb-3">Select Files to Preprocess</h4>
            <div v-if="projectFiles.length === 0" class="bg-gray-50 p-4 text-center text-gray-500 rounded-md">
              No files available. Please upload files first.
            </div>
            <div v-else class="border rounded-md divide-y overflow-hidden">
              <div class="bg-gray-50 px-4 py-2 flex items-center">
                <div class="w-8">
                  <input
                    type="checkbox"
                    :checked="isAllFilesSelected"
                    @change="toggleSelectAllFiles"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </div>
                <div class="flex-1 text-sm font-medium text-gray-700">File Name</div>
                <div class="w-32 text-sm font-medium text-gray-700">Uploaded</div>
              </div>
              <div v-for="file in projectFiles" :key="file.id" class="px-4 py-3 flex items-center hover:bg-gray-50">
                <div class="w-8">
                  <input
                    type="checkbox"
                    v-model="selectedFiles"
                    :value="file.id"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </div>
                <div class="flex-1 truncate" :title="file.file_name">{{ file.file_name }}</div>
                <div class="w-32 text-sm text-gray-500">{{ formatDate(file.created_at) }}</div>
              </div>
            </div>
          </div>
          <div class="mt-6 flex justify-end">
            <button
              type="submit"
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              :disabled="isSubmitting || selectedFiles.length === 0"
            >
              <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Start Preprocessing
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { api } from '@/services/api';
import Multiselect from '@vueform/multiselect';
import '@vueform/multiselect/themes/default.css';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  files: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['update:files']);

const preprocessingTasks = ref([]);
const isLoading = ref(true);
const error = ref('');
const isSubmitting = ref(false);
const selectedFiles = ref([]);
const pollInterval = ref(null);
const projectFiles = ref(props.files);

// Language mapping
const languageMap = {
  'eng': 'English',
  'spa': 'Spanish',
  'fra': 'French',
  'deu': 'German',
  'ita': 'Italian',
};

// Preprocessing configuration - simplified
const preprocessingConfig = ref({
  use_ocr: true,
  force_ocr: false,
  ocr_backend: 'ocrmypdf',
  pdf_backend: 'pymupdf4llm',
  ocr_languages: [{ value: 'eng', label: 'English' }], // Initialize with objects that have value and label
});

// Language options - simplified to use strings directly
const ocrLanguagesForSelect = ref([
  { value: 'eng', label: 'English' },
  { value: 'spa', label: 'Spanish' },
  { value: 'fra', label: 'French' },
  { value: 'deu', label: 'German' },
  { value: 'ita', label: 'Italian' },
]);

// Check if all files are selected
const isAllFilesSelected = computed(() => {
  return projectFiles.value.length > 0 && selectedFiles.value.length === projectFiles.value.length;
});

// Toggle select all files
const toggleSelectAllFiles = () => {
  if (isAllFilesSelected.value) {
    selectedFiles.value = [];
  } else {
    selectedFiles.value = projectFiles.value.map(file => file.id);
  }
};

// Format status
const formatStatus = (status) => {
  if (!status) return 'Unknown';
  return status.charAt(0).toUpperCase() + status.slice(1);
};

// Format date
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

// Start preprocessing
const startPreprocessing = async () => {
  if (selectedFiles.value.length === 0) {
    error.value = 'Please select at least one file to preprocess';
    return;
  }
  isSubmitting.value = true;
  error.value = '';
  try {
    const taskData = {
      ...preprocessingConfig.value,
      ocr_languages: preprocessingConfig.value.ocr_languages.map(lang =>
        typeof lang === 'string' ? lang : lang.value
      ),
      file_ids: selectedFiles.value
    };
    const response = await api.post(`/project/${props.projectId}/preprocess`, taskData);
    // Add the new task to the list
    preprocessingTasks.value.unshift(response.data);
    // Reset selection
    selectedFiles.value = [];
    // Ensure polling is active
    setupPolling();
  } catch (err) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail.map(detail => detail.msg).join(', ');
    } else {
      error.value = err.response?.data?.detail || 'Failed to start preprocessing task';
    }
    console.error(err);
  } finally {
    isSubmitting.value = false;
  }
};

// Retry a failed preprocessing task
const retryPreprocessing = (task) => {
  // Pre-populate the form with the same configuration
  preprocessingConfig.value = {
    use_ocr: task.use_ocr,
    force_ocr: task.force_ocr,
    ocr_backend: task.ocr_backend || 'ocrmypdf',
    pdf_backend: task.pdf_backend || 'pymupdf4llm',
    ocr_languages: task.ocr_languages || ['eng'],
  };
  // Select the same files
  selectedFiles.value = task.file_ids || [];
  // Scroll to the form
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
};

// Fetch preprocessing tasks
const fetchPreprocessingTasks = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess`);
    preprocessingTasks.value = response.data;
  } catch (err) {
    error.value = 'Failed to load preprocessing tasks';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Fetch project files
const fetchProjectFiles = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/file`);
    projectFiles.value = response.data;
  } catch (err) {
    error.value = 'Failed to load project files';
    console.error(err);
  }
};

// Update task status
const updateTaskStatus = async (taskId) => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess/${taskId}`);
    // Update the task in the list
    const index = preprocessingTasks.value.findIndex(task => task.id === taskId);
    if (index !== -1) {
      preprocessingTasks.value[index] = response.data;
    }
  } catch (err) {
    console.error(`Failed to update status for task ${taskId}:`, err);
  }
};

// Set up polling for active tasks
const setupPolling = () => {
  // Clear existing interval if any
  if (pollInterval.value) {
    clearInterval(pollInterval.value);
  }
  // Set up new polling interval
  pollInterval.value = setInterval(() => {
    // Find active tasks (not completed or failed)
    const activeTasks = preprocessingTasks.value.filter(
      task => task.status !== 'completed' && task.status !== 'failed'
    );
    // If no active tasks, stop polling
    if (activeTasks.length === 0) {
      clearInterval(pollInterval.value);
      pollInterval.value = null;
      return;
    }
    // Update status for each active task
    activeTasks.forEach(task => {
      updateTaskStatus(task.id);
    });
  }, 3000); // Poll every 3 seconds
};

watch(() => props.files, (newFiles) => {
  projectFiles.value = newFiles;
}, { immediate: true });

onMounted(() => {
  fetchPreprocessingTasks().then(() => {
    setupPolling();
  });
  fetchProjectFiles();
});

onUnmounted(() => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value);
  }
});
</script>

<style>
.multiselect {
  --ms-bg: #ffffff;
  --ms-border-color: #d1d5db;
  --ms-radius: 0.375rem;
  --ms-py: 0.5rem;
  --ms-px: 0.75rem;
  z-index: 10;
}

.multiselect__content-wrapper {
  z-index: 1000;
  position: absolute;
  width: 100%;
  max-height: 300px !important;
  overflow-y: auto !important;
}

.multiselect__option {
  display: block !important;
}

.multiselect__option--selected {
  background-color: rgba(59, 130, 246, 0.1) !important;
  color: #333 !important;
}

.multiselect__option--highlight {
  background-color: #3b82f6 !important;
  color: white !important;
}

.multiselect__tag {
  background-color: #3b82f6 !important;
}
</style>
