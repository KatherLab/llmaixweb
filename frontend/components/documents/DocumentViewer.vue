<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 overflow-hidden">
      <div class="absolute inset-0 bg-black bg-opacity-75" @click="$emit('close')"></div>

      <div class="absolute inset-4 md:inset-8 bg-white rounded-lg shadow-2xl flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b bg-gray-50 rounded-t-lg">
          <div class="flex items-center space-x-4">
            <h3 class="text-lg font-semibold text-gray-900">
              {{ document.original_file?.file_name || `Document #${document.id}` }}
            </h3>
            <span
              :class="[
                'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                document.preprocessing_status === 'success' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              ]"
            >
              {{ document.preprocessing_status || 'Processed' }}
            </span>
          </div>

          <div class="flex items-center space-x-2">
            <button
              @click="toggleView"
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <svg class="h-4 w-4 mr-1.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
              {{ viewMode === 'text' ? 'Show Original' : 'Show Text' }}
            </button>

            <button
              @click="downloadDocument"
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <svg class="h-4 w-4 mr-1.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
              </svg>
              Download
            </button>

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

        <!-- Content Area -->
        <div class="flex-1 flex overflow-hidden">
          <!-- Main Content -->
          <div class="flex-1 overflow-auto">
            <!-- Text View -->
            <div v-if="viewMode === 'text'" class="p-6">
              <div class="prose max-w-none">
                <pre class="whitespace-pre-wrap font-sans text-sm text-gray-800 bg-gray-50 p-4 rounded-lg">{{ document.text || 'No text content available' }}</pre>
              </div>
            </div>

            <!-- PDF View -->
            <div v-else-if="viewMode === 'pdf' && pdfUrl" class="h-full">
              <iframe
                :src="pdfUrl"
                class="w-full h-full"
                frameborder="0"
              ></iframe>
            </div>

            <!-- Side-by-side View -->
            <div v-else-if="viewMode === 'compare'" class="flex h-full">
              <div class="w-1/2 border-r overflow-auto p-4">
                <h4 class="font-medium text-gray-700 mb-2">Original</h4>
                <iframe
                  v-if="originalPdfUrl"
                  :src="originalPdfUrl"
                  class="w-full h-full"
                  frameborder="0"
                ></iframe>
              </div>
              <div class="w-1/2 overflow-auto p-4">
                <h4 class="font-medium text-gray-700 mb-2">Processed (with text layer)</h4>
                <iframe
                  v-if="pdfUrl"
                  :src="pdfUrl"
                  class="w-full h-full"
                  frameborder="0"
                ></iframe>
              </div>
            </div>
          </div>

          <!-- Sidebar -->
          <div class="w-80 border-l bg-gray-50 overflow-auto">
            <div class="p-4 space-y-4">
              <!-- Document Info -->
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Document Information</h4>
                <dl class="space-y-2 text-sm">
                  <div>
                    <dt class="text-gray-500">Created</dt>
                    <dd class="text-gray-900">{{ formatDateTime(document.created_at) }}</dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">File Size</dt>
                    <dd class="text-gray-900">{{ formatFileSize(document.original_file?.file_size) }}</dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">Text Length</dt>
                    <dd class="text-gray-900">{{ document.text?.length || 0 }} characters</dd>
                  </div>
                </dl>
              </div>

              <!-- Preprocessing Info -->
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Preprocessing Configuration</h4>
                <dl class="space-y-2 text-sm">
                  <div>
                    <dt class="text-gray-500">Configuration</dt>
                    <dd class="text-gray-900">{{ document.preprocessing_config?.name || 'Custom' }}</dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">OCR Enabled</dt>
                    <dd class="text-gray-900">{{ document.preprocessing_config?.use_ocr ? 'Yes' : 'No' }}</dd>
                  </div>
                  <div v-if="document.preprocessing_config?.use_ocr">
                    <dt class="text-gray-500">OCR Languages</dt>
                    <dd class="text-gray-900">
                      {{ document.preprocessing_config?.ocr_languages?.join(', ') || 'Default' }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">PDF Backend</dt>
                    <dd class="text-gray-900">{{ document.preprocessing_config?.pdf_backend || 'Default' }}</dd>
                  </div>
                </dl>
              </div>

              <!-- Metadata -->
              <div v-if="document.meta_data && Object.keys(document.meta_data).length > 0">
                <h4 class="font-medium text-gray-900 mb-2">Metadata</h4>
                <div class="bg-white rounded-lg p-3 text-xs">
                  <pre class="overflow-x-auto">{{ JSON.stringify(document.meta_data, null, 2) }}</pre>
                </div>
              </div>

              <!-- Actions -->
              <div class="pt-4 border-t">
                <button
                  @click="$emit('reprocess', document)"
                  class="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <svg class="h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Reprocess Document
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { api } from '@/services/api.js';
import { useToast } from 'vue-toastification';

const props = defineProps({
  document: {
    type: Object,
    required: true
  },
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close', 'reprocess']);

const toast = useToast();
const viewMode = ref('text');
const pdfUrl = ref('');
const originalPdfUrl = ref('');

const toggleView = () => {
  if (viewMode.value === 'text') {
    viewMode.value = 'pdf';
  } else if (viewMode.value === 'pdf' && props.document.preprocessed_file?.id) {
    viewMode.value = 'compare';
  } else {
    viewMode.value = 'text';
  }
};

const downloadDocument = async () => {
  try {
    const fileId = props.document.preprocessed_file?.id || props.document.original_file?.id;
    if (!fileId) {
      toast.error('No file available for download');
      return;
    }

    const response = await api.get(`/project/${props.projectId}/file/${fileId}/content`, {
      responseType: 'blob'
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', props.document.original_file?.file_name || `document_${props.document.id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    toast.error('Failed to download document');
    console.error(error);
  }
};

const formatDateTime = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString();
};

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

// Load PDF URLs
onMounted(async () => {
  try {
    if (props.document.preprocessed_file?.id) {
      pdfUrl.value = `/api/v1/project/${props.projectId}/file/${props.document.preprocessed_file.id}/content?preview=true`;
    }
    if (props.document.original_file?.id) {
      originalPdfUrl.value = `/api/v1/project/${props.projectId}/file/${props.document.original_file.id}/content?preview=true`;
    }
  } catch (error) {
    console.error('Failed to load PDF URLs:', error);
  }
});

// Cleanup
onUnmounted(() => {
  if (pdfUrl.value && pdfUrl.value.startsWith('blob:')) {
    window.URL.revokeObjectURL(pdfUrl.value);
  }
  if (originalPdfUrl.value && originalPdfUrl.value.startsWith('blob:')) {
    window.URL.revokeObjectURL(originalPdfUrl.value);
  }
});
</script>

