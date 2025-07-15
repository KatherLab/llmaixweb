<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 overflow-hidden">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="$emit('close')"></div>

      <div class="absolute inset-y-0 right-0 max-w-2xl w-full bg-white shadow-xl flex flex-col">
        <!-- Header -->
        <div class="px-6 py-4 bg-gray-50 border-b">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">Preprocessing Configurations</h2>
            <button
              @click="$emit('close')"
              class="text-gray-400 hover:text-gray-500"
            >
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto">
          <!-- Create New Configuration -->
          <div class="p-6 border-b">
            <button
              @click="showCreateForm = !showCreateForm"
              class="w-full flex items-center justify-between px-4 py-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <span class="font-medium">Create New Configuration</span>
              <svg
                :class="['h-5 w-5 transition-transform', showCreateForm ? 'rotate-180' : '']"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <div v-if="showCreateForm" class="mt-4 space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Configuration Name</label>
                <input
                  v-model="newConfig.name"
                  type="text"
                  placeholder="e.g., High Quality OCR for Scanned PDFs"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  v-model="newConfig.description"
                  rows="2"
                  placeholder="Describe when to use this configuration..."
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">File Type</label>
                <select
                  v-model="newConfig.file_type"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="pdf">PDF Documents</option>
                  <option value="image">Images (PNG, JPG, etc.)</option>
                  <option value="mixed">Mixed File Types</option>
                </select>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">PDF Backend</label>
                  <select
                    v-model="newConfig.pdf_backend"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="pymupdf4llm">PyMuPDF4LLM (Recommended)</option>
                    <option value="markitdown">MarkItDown</option>
                  </select>
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">OCR Backend</label>
                  <select
                    v-model="newConfig.ocr_backend"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="ocrmypdf">OCRmyPDF</option>
                  </select>
                </div>
              </div>

              <div class="space-y-3">
                <label class="flex items-center">
                  <input
                    v-model="newConfig.use_ocr"
                    type="checkbox"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span class="ml-2 text-sm text-gray-700">Enable OCR</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="newConfig.force_ocr"
                    type="checkbox"
                    :disabled="!newConfig.use_ocr"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span class="ml-2 text-sm text-gray-700">Force OCR (ignore existing text)</span>
                </label>
              </div>

              <div v-if="newConfig.use_ocr">
                <label class="block text-sm font-medium text-gray-700 mb-1">OCR Languages</label>
                <Multiselect
                  v-model="newConfig.ocr_languages"
                  :options="ocrLanguages"
                  mode="tags"
                  :searchable="true"
                  :close-on-select="false"
                  placeholder="Select languages"
                  class="multiselect-blue"
                />
              </div>

              <div class="flex justify-end space-x-3">
                <button
                  @click="cancelCreate"
                  class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  @click="createConfiguration"
                  :disabled="!newConfig.name || isCreating"
                  class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span v-if="isCreating" class="flex items-center">
                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating...
                  </span>
                  <span v-else>Create Configuration</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Existing Configurations -->
          <div class="p-6">
            <h3 class="text-sm font-medium text-gray-900 mb-4">Saved Configurations</h3>

            <div v-if="isLoading" class="flex justify-center py-8">
              <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>

            <div v-else-if="configurations.length === 0" class="text-center py-8">
              <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <p class="mt-2 text-sm text-gray-600">No saved configurations yet</p>
            </div>

            <div v-else class="space-y-3">
              <div
                v-for="config in configurations"
                :key="config.id"
                class="border rounded-lg p-4 hover:border-blue-300 transition-colors"
              >
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <h4 class="font-medium text-gray-900">{{ config.name }}</h4>
                    <p v-if="config.description" class="text-sm text-gray-500 mt-1">
                      {{ config.description }}
                    </p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                        {{ config.file_type }}
                      </span>
                      <span v-if="config.use_ocr" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        OCR: {{ config.ocr_languages?.join(', ') || 'Default' }}
                      </span>
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                        PDF: {{ config.pdf_backend }}
                      </span>
                    </div>
                  </div>

                  <div class="ml-4 flex items-center space-x-2">
                    <button
                      @click="$emit('config-selected', config)"
                      class="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Use
                    </button>
                    <button
                      @click="editConfiguration(config)"
                      class="text-sm text-gray-600 hover:text-gray-800"
                    >
                      Edit
                    </button>
                    <button
                      @click="deleteConfiguration(config)"
                      class="text-sm text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import Multiselect from '@vueform/multiselect';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close', 'config-selected']);

const toast = useToast();
const configurations = ref([]);
const isLoading = ref(true);
const showCreateForm = ref(false);
const isCreating = ref(false);

const newConfig = ref({
  name: '',
  description: '',
  file_type: 'pdf',
  pdf_backend: 'pymupdf4llm',
  ocr_backend: 'ocrmypdf',
  use_ocr: true,
  force_ocr: false,
  ocr_languages: ['eng']
});

const ocrLanguages = ref([
  'eng', 'spa', 'fra', 'deu', 'ita', 'por', 'rus', 'jpn', 'chi_sim', 'chi_tra'
]);

const fetchConfigurations = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/preprocessing-config`);
    configurations.value = response.data;
  } catch (error) {
    toast.error('Failed to load configurations');
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

const createConfiguration = async () => {
  if (!newConfig.value.name) return;

  isCreating.value = true;
  try {
    const response = await api.post(`/project/${props.projectId}/preprocessing-config`, newConfig.value);
    configurations.value.unshift(response.data);
    toast.success('Configuration created successfully');

    // Reset form
    showCreateForm.value = false;
    newConfig.value = {
      name: '',
      description: '',
      file_type: 'pdf',
      pdf_backend: 'pymupdf4llm',
      ocr_backend: 'ocrmypdf',
      use_ocr: true,
      force_ocr: false,
      ocr_languages: ['eng']
    };
  } catch (error) {
    toast.error('Failed to create configuration');
    console.error(error);
  } finally {
    isCreating.value = false;
  }
};

const cancelCreate = () => {
  showCreateForm.value = false;
  newConfig.value = {
    name: '',
    description: '',
    file_type: 'pdf',
    pdf_backend: 'pymupdf4llm',
    ocr_backend: 'ocrmypdf',
    use_ocr: true,
    force_ocr: false,
    ocr_languages: ['eng']
  };
};

const editConfiguration = (config) => {
  // TODO: Implement edit functionality
  toast.info('Edit functionality coming soon');
};

const deleteConfiguration = async (config) => {
  if (!confirm(`Delete configuration "${config.name}"?`)) return;

  try {
    await api.delete(`/project/${props.projectId}/preprocessing-config/${config.id}`);
    configurations.value = configurations.value.filter(c => c.id !== config.id);
    toast.success('Configuration deleted');
  } catch (error) {
    toast.error('Failed to delete configuration');
    console.error(error);
  }
};

onMounted(() => {
  fetchConfigurations();
});
</script>

<style>
.multiselect-blue {
  --ms-bg: #ffffff;
  --ms-border-color: #d1d5db;
  --ms-border-color-active: #3b82f6;
  --ms-radius: 0.5rem;
  --ms-py: 0.5rem;
  --ms-px: 0.75rem;
  --ms-font-size: 0.875rem;
  --ms-option-bg-selected: #eff6ff;
  --ms-option-color-selected: #1e40af;
  --ms-tag-bg: #3b82f6;
  --ms-tag-color: #ffffff;
}
</style>
