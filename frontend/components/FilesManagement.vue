<!-- src/components/FilesManagement.vue -->
<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-medium text-gray-900">Files</h2>
      <div>
        <input
          ref="fileInputRef"
          type="file"
          @change="handleFileUpload"
          accept="application/pdf"
          multiple
          class="hidden"
        />
        <button
          @click="$refs.fileInputRef.click()"
          class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md flex items-center"
          :disabled="isUploading"
        >
          <svg class="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
          Upload Files
        </button>
      </div>
    </div>

    <!-- Upload Progress -->
    <div v-if="uploadProgress > 0 && isUploading" class="mb-6">
      <div class="bg-gray-200 rounded-full overflow-hidden">
        <div
          class="bg-blue-600 text-xs leading-none py-1 text-center text-white"
          :style="{ width: `${uploadProgress}%` }"
        >
          {{ uploadProgress }}%
        </div>
      </div>
      <p class="text-sm text-gray-600 mt-1">Uploading {{ currentUploadingFile }}...</p>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
      {{ error }}
    </div>

    <!-- File List -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="files.length === 0" class="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="mt-2 text-sm text-gray-600">No files uploaded yet</p>
      <p class="mt-1 text-sm text-gray-500">Upload PDF files to begin processing</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
      <div v-for="file in files" :key="file.id" class="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div class="p-4">
          <div class="flex items-start justify-between">
            <div class="flex items-center">
              <div class="flex-shrink-0 bg-blue-100 rounded-md p-2">
                <svg class="h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-gray-900 truncate max-w-[140px]" :title="file.file_name">
                  {{ file.file_name }}
                </h3>
                <p class="text-xs text-gray-500">
                  {{ formatDate(file.created_at) }} • {{ formatFileSize(file.file_size) }}
                </p>
              </div>
            </div>
            <button
              @click="confirmDeleteFile(file)"
              class="text-gray-400 hover:text-red-500"
              title="Delete file"
            >
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 border-t text-xs font-medium">
          <div class="flex justify-between items-center">
            <span class="text-gray-500">{{ file.file_type || 'application/pdf' }}</span>
            <button
              @click="previewFile(file)"
              class="text-blue-600 hover:text-blue-800 flex items-center"
            >
              Preview
              <svg class="h-4 w-4 ml-1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDeleteModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg max-w-md w-full p-6">
          <h3 class="text-lg font-medium text-gray-900">Delete File</h3>
          <p class="mt-2 text-sm text-gray-500">
            Are you sure you want to delete this file? This action cannot be undone.
          </p>
          <div class="mt-6 flex justify-end space-x-3">
            <button
              class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="showDeleteModal = false"
            >
              Cancel
            </button>
            <button
              class="inline-flex justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
              @click="deleteSelectedFile"
              :disabled="isDeleting"
            >
              <svg v-if="isDeleting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- File Preview Modal -->
    <Teleport to="body">
  <div
    v-if="showPreviewModal"
    class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
    @click="showPreviewModal = false"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl h-[80vh] flex flex-col" @click.stop>
      <div class="flex justify-between items-center p-4 border-b">
        <h3 class="text-lg font-medium text-gray-900">{{ previewingFile?.file_name }}</h3>
        <button @click="showPreviewModal = false" class="text-gray-400 hover:text-gray-500">
          <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="flex-1 overflow-hidden bg-gray-100">
        <iframe
          v-if="previewUrl && ['application/pdf'].includes(previewingFile.file_type)"
          :src="previewUrl"
          class="w-full h-full"
          title="File preview"
        ></iframe>
        <img
          v-else-if="previewUrl && previewingFile.file_type.startsWith('image/')"
          :src="previewUrl"
          class="object-contain w-full h-full"
          alt="File preview"
        />
        <div v-else-if="previewUrl && previewingFile.file_type === 'text/csv'" class="p-4 overflow-auto h-full">
          <pre>{{ previewText }}</pre>
        </div>
        <div v-else-if="previewUrl" class="flex items-center justify-center h-full">
          <a :href="previewUrl" target="_blank" class="text-blue-600 hover:text-blue-800">
            Download {{ previewingFile.file_name }}
          </a>
        </div>
        <div v-else class="flex items-center justify-center h-full">
          <p class="text-gray-500">Preview not available</p>
        </div>
      </div>
    </div>
  </div>
</Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { api } from '@/services/api';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['files-uploaded']);

const files = ref([]);
const isLoading = ref(true);
const error = ref('');
const isUploading = ref(false);
const uploadProgress = ref(0);
const currentUploadingFile = ref('');
const fileInputRef = ref(null);

// Delete confirmation
const showDeleteModal = ref(false);
const isDeleting = ref(false);
const fileToDelete = ref(null);

// Preview
const showPreviewModal = ref(false);
const previewingFile = ref(null);
const previewUrl = ref('');

// Fetch files for the project
const fetchFiles = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/file?file_creator=user`);
    files.value = response.data;
  } catch (err) {
    error.value = 'Failed to load files';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Handle file upload
const handleFileUpload = async (event) => {
  const selectedFiles = event.target.files;
  if (!selectedFiles.length) return;

  isUploading.value = true;
  error.value = '';

  for (let i = 0; i < selectedFiles.length; i++) {
    const file = selectedFiles[i];
    currentUploadingFile.value = file.name;
    uploadProgress.value = 0;

    try {
      // Create file info object
      const fileInfo = JSON.stringify({
        file_name: file.name,
        file_type: file.type,
        description: ''
      });

      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_info', fileInfo);

      // Upload with progress tracking
      const response = await api.post(
        `/project/${props.projectId}/file`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            uploadProgress.value = percentCompleted;
          }
        }
      );

      // Add the new file to the list
      files.value.push(response.data);

    } catch (err) {
      error.value = `Failed to upload ${file.name}: ${err.response?.data?.detail || err.message}`;
      console.error(err);
      break;
    }
  }

  isUploading.value = false;
  currentUploadingFile.value = '';
  uploadProgress.value = 0;
  event.target.value = null; // Reset file input

  emit('files-uploaded');
};

// Format file size
const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown size';

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

// Format date
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

// Confirm file deletion
const confirmDeleteFile = (file) => {
  fileToDelete.value = file;
  showDeleteModal.value = true;
};

// Delete file
const deleteSelectedFile = async () => {
  if (!fileToDelete.value) return;

  isDeleting.value = true;
  try {
    await api.delete(`/project/${props.projectId}/file/${fileToDelete.value.id}`);
    files.value = files.value.filter(f => f.id !== fileToDelete.value.id);
    showDeleteModal.value = false;
    emit('files-uploaded');
  } catch (err) {
    error.value = 'Failed to delete file';
    console.error(err);
  } finally {
    isDeleting.value = false;
    fileToDelete.value = null;
  }
};

const previewText = ref('');


const previewFile = async (file) => {
  previewingFile.value = file;
  showPreviewModal.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/file/${file.id}/content?preview=true`, {
      responseType: 'blob'
    });
    previewUrl.value = URL.createObjectURL(response.data);
  } catch (err) {
    previewUrl.value = '';
    console.error('Failed to get file preview:', err);
  }
};

onMounted(() => {
  fetchFiles();
});
</script>
