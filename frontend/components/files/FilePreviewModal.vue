<!-- FilePreviewModal.vue -->
<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-xl w-full max-w-5xl h-[85vh] flex flex-col"
        @click.stop
      >
        <!-- Header -->
        <div class="flex justify-between items-center p-4 border-b">
          <div class="flex items-center space-x-3">
            <FileIcon :fileType="file.file_type" :size="32" />
            <div>
              <h3 class="text-lg font-medium text-gray-900">{{ file.file_name }}</h3>
              <p class="text-sm text-gray-500">
                {{ formatFileSize(file.file_size) }} • {{ file.file_type }}
              </p>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <button
              @click="downloadFile"
              class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg"
              title="Download"
            >
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
              </svg>
            </button>
            <button
              @click="$emit('close')"
              class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Preview Content -->
        <div class="flex-1 overflow-hidden bg-gray-100">
          <!-- Loading State -->
          <div v-if="isLoading" class="flex items-center justify-center h-full">
            <LoadingSpinner size="large" />
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="flex items-center justify-center h-full">
            <div class="text-center">
              <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p class="mt-2 text-sm text-gray-600">{{ error }}</p>
              <button
                @click="loadPreview"
                class="mt-4 text-sm text-blue-600 hover:text-blue-800"
              >
                Try Again
              </button>
            </div>
          </div>

          <!-- PDF Preview -->
          <iframe
            v-else-if="previewUrl && file.file_type === 'application/pdf'"
            :src="previewUrl"
            class="w-full h-full"
            title="PDF preview"
          ></iframe>

          <!-- Image Preview -->
          <div
            v-else-if="previewUrl && file.file_type?.startsWith('image/')"
            class="flex items-center justify-center h-full p-8"
          >
            <img
              :src="previewUrl"
              :alt="file.file_name"
              class="max-w-full max-h-full object-contain"
            />
          </div>

          <!-- Text/CSV Preview -->
          <div
            v-else-if="previewContent && (file.file_type === 'text/plain' || file.file_type === 'text/csv')"
            class="h-full overflow-auto"
          >
            <pre class="p-6 text-sm font-mono whitespace-pre-wrap">{{ previewContent }}</pre>
          </div>

          <!-- Excel Preview -->
          <div
            v-else-if="excelData && isExcelFile"
            class="h-full overflow-auto p-6"
          >
            <div class="bg-white rounded-lg shadow">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th
                      v-for="(header, index) in excelData.headers"
                      :key="index"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {{ header }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="(row, rowIndex) in excelData.rows" :key="rowIndex">
                    <td
                      v-for="(cell, cellIndex) in row"
                      :key="cellIndex"
                      class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                    >
                      {{ cell }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="excelData.truncated" class="px-6 py-3 bg-gray-50 text-sm text-gray-500">
                Showing first 100 rows of {{ excelData.totalRows }} total rows
              </div>
            </div>
          </div>

          <!-- Word Document Preview -->
          <div
            v-else-if="wordContent && isWordFile"
            class="h-full overflow-auto p-6 bg-white"
          >
            <div class="prose max-w-none" v-html="wordContent"></div>
          </div>

          <!-- Unsupported File Type -->
          <div v-else class="flex items-center justify-center h-full">
            <div class="text-center">
              <FileIcon :fileType="file.file_type" :size="64" />
              <p class="mt-4 text-sm text-gray-600">
                Preview not available for this file type
              </p>
              <button
                @click="downloadFile"
                class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <svg class="mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                </svg>
                Download File
              </button>
            </div>
          </div>
        </div>

        <!-- File Info Footer -->
        <div class="border-t bg-gray-50 px-4 py-3">
          <div class="flex items-center justify-between text-sm">
            <div class="flex items-center space-x-4 text-gray-500">
              <span>Created: {{ formatDate(file.created_at) }}</span>
              <span v-if="file.file_hash" class="font-mono text-xs">
                Hash: {{ file.file_hash.substring(0, 8) }}...
              </span>
            </div>
            <div v-if="file.description" class="text-gray-600">
              {{ file.description }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import FileIcon from '@/components/common/FileIcon.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const props = defineProps({
  file: {
    type: Object,
    required: true
  },
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close']);
const toast = useToast();

// State
const isLoading = ref(true);
const error = ref('');
const previewUrl = ref('');
const previewContent = ref('');
const excelData = ref(null);
const wordContent = ref('');

// Computed
const isExcelFile = computed(() => {
  return props.file.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
         props.file.file_type === 'application/vnd.ms-excel';
});

const isWordFile = computed(() => {
  return props.file.file_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
         props.file.file_type === 'application/msword';
});

// Methods
const loadPreview = async () => {
  isLoading.value = true;
  error.value = '';

  try {
    const response = await api.get(
      `/project/${props.projectId}/file/${props.file.id}/content?preview=true`,
      { responseType: 'blob' }
    );

    // Handle different file types
    if (props.file.file_type === 'text/plain' || props.file.file_type === 'text/csv') {
      const text = await response.data.text();
      previewContent.value = text;
    } else if (isExcelFile.value) {
      // For Excel files, we'd need a server-side preview endpoint
      // For now, show download option
      error.value = 'Excel preview requires server-side processing';
    } else if (isWordFile.value) {
      // For Word files, we'd need a server-side preview endpoint
      error.value = 'Word preview requires server-side processing';
    } else {
      // Create blob URL for other file types
      previewUrl.value = URL.createObjectURL(response.data);
    }
  } catch (err) {
    error.value = 'Failed to load preview';
    console.error('Preview error:', err);
  } finally {
    isLoading.value = false;
  }
};

const downloadFile = async () => {
  try {
    const response = await api.get(
      `/project/${props.projectId}/file/${props.file.id}/content`,
      { responseType: 'blob' }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', props.file.file_name);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    toast.success('File downloaded successfully');
  } catch (err) {
    toast.error('Failed to download file');
    console.error(err);
  }
};

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString();
};

// Lifecycle
onMounted(() => {
  loadPreview();
  document.body.style.overflow = 'hidden';
});

onUnmounted(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
  document.body.style.overflow = '';
});
</script>
