<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 overflow-hidden">
      <div class="absolute inset-0 bg-black bg-opacity-50" @click="$emit('close')"></div>

      <div class="absolute inset-x-4 top-1/2 transform -translate-y-1/2 max-w-2xl mx-auto">
        <div class="bg-white rounded-lg shadow-xl">
          <!-- Header -->
          <div class="px-6 py-4 border-b">
            <h3 class="text-lg font-semibold text-gray-900">
              {{ actionTitle }}
            </h3>
            <p class="mt-1 text-sm text-gray-500">
              {{ documents.length }} document{{ documents.length !== 1 ? 's' : '' }} selected
            </p>
          </div>

          <!-- Content -->
          <div class="p-6">
            <!-- Reprocess Action -->
            <div v-if="action === 'reprocess'" class="space-y-4">
              <p class="text-sm text-gray-600">
                Choose a preprocessing configuration for the selected documents:
              </p>

              <div class="space-y-3">
                <label
                  v-for="config in configurations"
                  :key="config.id"
                  class="flex items-start p-4 border rounded-lg cursor-pointer hover:bg-gray-50"
                >
                  <input
                    v-model="selectedConfigId"
                    :value="config.id"
                    type="radio"
                    class="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500 mt-0.5"
                  />
                  <div class="ml-3">
                    <p class="font-medium text-gray-900">{{ config.name }}</p>
                    <p class="text-sm text-gray-500">{{ config.description }}</p>
                    <div class="mt-1 flex flex-wrap gap-2">
                      <span class="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                        {{ config.file_type }}
                      </span>
                      <span v-if="config.use_ocr" class="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        OCR: {{ config.ocr_languages?.join(', ') }}
                      </span>
                    </div>
                  </div>
                </label>
              </div>

              <div class="flex items-center">
                <input
                  v-model="forceReprocess"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label class="ml-2 text-sm text-gray-700">
                  Force reprocess (ignore existing results)
                </label>
              </div>
            </div>

            <!-- Export Action -->
            <div v-else-if="action === 'export'" class="space-y-4">
              <p class="text-sm text-gray-600">
                Choose export format and options:
              </p>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Export Format
                </label>
                <select
                  v-model="exportFormat"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="json">JSON</option>
                  <option value="csv">CSV</option>
                  <option value="txt">Plain Text</option>
                  <option value="pdf">PDF (with text layer)</option>
                </select>
              </div>

              <div class="space-y-2">
                <label class="flex items-center">
                  <input
                    v-model="includeMetadata"
                    type="checkbox"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span class="ml-2 text-sm text-gray-700">Include metadata</span>
                </label>
                <label class="flex items-center">
                  <input
                    v-model="includePreprocessingInfo"
                    type="checkbox"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <span class="ml-2 text-sm text-gray-700">Include preprocessing information</span>
                </label>
              </div>
            </div>

            <!-- Delete Action -->
            <div v-else-if="action === 'delete'" class="space-y-4">
              <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex">
                  <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-800">
                      Warning: This action cannot be undone
                    </h3>
                    <p class="mt-1 text-sm text-red-700">
                      The selected documents and their preprocessing results will be permanently deleted.
                    </p>
                  </div>
                </div>
              </div>

              <div class="flex items-center">
                <input
                  v-model="confirmDelete"
                  type="checkbox"
                  class="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                />
                <label class="ml-2 text-sm text-gray-700">
                  I understand that this action is permanent
                </label>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-4 bg-gray-50 border-t flex justify-end space-x-3">
            <button
              @click="$emit('close')"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              @click="performAction"
              :disabled="!canPerformAction"
              :class="[
                'px-4 py-2 text-sm font-medium rounded-lg',
                action === 'delete'
                  ? 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300'
                  : 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300',
                'disabled:cursor-not-allowed'
              ]"
            >
              <span v-if="isProcessing" class="flex items-center">
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
              <span v-else>{{ actionButtonText }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '@/services/api.js';
import { useToast } from 'vue-toastification';

const props = defineProps({
  action: {
    type: String,
    required: true
  },
  documents: {
    type: Array,
    required: true
  },
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close', 'complete']);

const toast = useToast();
const configurations = ref([]);
const selectedConfigId = ref(null);
const forceReprocess = ref(false);
const exportFormat = ref('json');
const includeMetadata = ref(true);
const includePreprocessingInfo = ref(true);
const confirmDelete = ref(false);
const isProcessing = ref(false);

const actionTitle = computed(() => {
  switch (props.action) {
    case 'reprocess':
      return 'Reprocess Documents';
    case 'export':
      return 'Export Documents';
    case 'delete':
      return 'Delete Documents';
    default:
      return 'Batch Action';
  }
});

const actionButtonText = computed(() => {
  switch (props.action) {
    case 'reprocess':
      return 'Start Reprocessing';
    case 'export':
      return 'Export';
    case 'delete':
      return 'Delete Documents';
    default:
      return 'Confirm';
  }
});

const canPerformAction = computed(() => {
  if (isProcessing.value) return false;

  switch (props.action) {
    case 'reprocess':
      return selectedConfigId.value !== null;
    case 'export':
      return true;
    case 'delete':
      return confirmDelete.value;
    default:
      return false;
  }
});

const fetchConfigurations = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocessing-config`);
    configurations.value = response.data;
  } catch (error) {
    console.error('Failed to fetch configurations:', error);
  }
};

const performAction = async () => {
  if (!canPerformAction.value) return;

  isProcessing.value = true;
  try {
    switch (props.action) {
      case 'reprocess':
        await reprocessDocuments();
        break;
      case 'export':
        await exportDocuments();
        break;
      case 'delete':
        await deleteDocuments();
        break;
    }

    emit('complete');
  } catch (error) {
    toast.error(`Failed to ${props.action} documents`);
    console.error(error);
  } finally {
    isProcessing.value = false;
  }
};

const reprocessDocuments = async () => {
  // Get file IDs from documents
  const fileIds = props.documents.map(docId => {
    // You might need to fetch document details to get original file IDs
    return docId; // Placeholder
  });

  const taskData = {
    configuration_id: selectedConfigId.value,
    file_ids: fileIds,
    force_reprocess: forceReprocess.value
  };

  await api.post(`/project/${props.projectId}/preprocess`, taskData);
  toast.success('Reprocessing task started');
};

const exportDocuments = async () => {
  // Implement export functionality
  toast.info('Export functionality would be implemented here');
};

const deleteDocuments = async () => {
  for (const docId of props.documents) {
    await api.delete(`/project/${props.projectId}/document/${docId}`);
  }
  toast.success(`${props.documents.length} documents deleted`);
};

onMounted(() => {
  if (props.action === 'reprocess') {
    fetchConfigurations();
  }
});
</script>
