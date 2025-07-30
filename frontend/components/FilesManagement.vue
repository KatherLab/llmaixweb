<template>
  <div class="p-6 space-y-6">
    <!-- Header with Stats -->
    <div class="flex justify-between items-start">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Files</h2>
        <p class="mt-1 text-sm text-gray-500">
          Upload and manage project files
        </p>
      </div>

      <!-- Quick Stats -->
      <div class="grid grid-cols-4 gap-4">
        <div class="text-center">
          <p class="text-2xl font-semibold text-gray-900">{{ stats.total_files }}</p>
          <p class="text-xs text-gray-500">Total Files</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-semibold text-blue-600">{{ stats.recent_files }}</p>
          <p class="text-xs text-gray-500">Recent</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-semibold text-amber-600">{{ formatFileSize(stats.total_size) }}</p>
          <p class="text-xs text-gray-500">Total Size</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-semibold text-red-600">{{ stats.duplicates }}</p>
          <p class="text-xs text-gray-500">Duplicates</p>
        </div>
      </div>
    </div>

    <!-- Filters and Search -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <!-- Search -->
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Search</label>
          <div class="relative">
            <input
              v-model="filters.search"
              type="text"
              placeholder="Search files..."
              class="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @input="debouncedFetch"
            />
            <svg class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        <!-- File Type Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">File Type</label>
          <select
            v-model="filters.fileType"
            @change="fetchFiles"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            <option value="application/pdf">PDF</option>
            <option value="image/jpeg">JPEG</option>
            <option value="image/png">PNG</option>
            <option value="text/plain">Text</option>
            <option value="text/csv">CSV</option>
            <option value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">Excel</option>
            <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">Word</option>
          </select>
        </div>

        <!-- File Creator Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">File Source</label>
          <select
            v-model="filters.fileCreator"
            @change="fetchFiles"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="user">User Uploaded</option>
            <option value="preprocessing">From Preprocessing</option>
            <option value="">All Sources</option>
          </select>
        </div>

        <!-- Date Range -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
          <select
            v-model="filters.dateRange"
            @change="applyDateFilter"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Time</option>
            <option value="today">Today</option>
            <option value="week">Last 7 days</option>
            <option value="month">Last 30 days</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Action Bar -->
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-4">
        <!-- Upload Button -->
        <input
          ref="fileInputRef"
          type="file"
          @change="handleFileUpload"
          accept=".pdf,.jpg,.jpeg,.png,.txt,.csv,.xlsx,.docx"
          multiple
          class="hidden"
        />
        <button
          @click="$refs.fileInputRef.click()"
          class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg flex items-center transition-colors"
          :disabled="isUploading"
        >
          <svg class="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
            <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 00-2 2v6a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-1a1 1 0 100-2h1a4 4 0 014 4v6a4 4 0 01-4 4H6a4 4 0 01-4-4V7a4 4 0 014-4z" clip-rule="evenodd" />
          </svg>
          Upload Files
        </button>

        <!-- Select All / Batch Actions -->
        <div v-if="selectedFiles.length === 0 && files.length > 0" class="flex items-center">
          <button
            @click="selectAllFiles"
            class="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center"
          >
            <svg class="w-4 h-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Select All ({{ files.length }})
          </button>
        </div>

        <!-- Batch Actions (when files are selected) -->
        <div v-else-if="selectedFiles.length > 0" class="flex items-center space-x-2">
          <span class="text-sm text-gray-700">
            {{ selectedFiles.length }} selected
          </span>
          <button
            @click="showBatchDownload"
            class="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Download
          </button>
          <button
            @click="confirmBatchDelete"
            class="text-sm text-red-600 hover:text-red-800 font-medium"
          >
            Delete
          </button>
          <button
            @click="selectedFiles = []"
            class="text-sm text-gray-600 hover:text-gray-800"
          >
            Clear
          </button>
        </div>
      </div>

      <!-- View Toggle -->
      <div class="flex items-center space-x-2">
        <button
          @click="viewMode = 'grid'"
          :class="[
            'p-2 rounded-lg transition-colors',
            viewMode === 'grid'
              ? 'bg-blue-100 text-blue-600'
              : 'text-gray-400 hover:text-gray-600'
          ]"
        >
          <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
        </button>
        <button
          @click="viewMode = 'list'"
          :class="[
            'p-2 rounded-lg transition-colors',
            viewMode === 'list'
              ? 'bg-blue-100 text-blue-600'
              : 'text-gray-400 hover:text-gray-600'
          ]"
        >
          <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Upload Progress -->
    <UploadProgress
      v-if="uploadQueue.length > 0"
      :queue="uploadQueue"
      :current-file="currentUploadingFile"
      :progress="uploadProgress"
      @cancel="cancelUpload"
    />

    <!-- Error Messages -->
    <ErrorAlert
      v-if="error"
      :message="error"
      @close="error = ''"
    />

    <!-- File List/Grid -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="large" />
    </div>

    <!-- Empty State with Drag & Drop -->
    <FileDropZone
      v-else-if="files.length === 0"
      @files-selected="handleFilesSelected"
      :disabled="isUploading"
    />

    <!-- Grid View -->
    <div v-else-if="viewMode === 'grid'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <FileCard
        v-for="file in files"
        :key="file.id"
        :file="file"
        :selected="selectedFiles.includes(file.id)"
        @toggle-selection="toggleFileSelection"
        @preview="previewFile"
        @download="downloadFile"
        @delete="confirmDeleteFile"
        @configure-import="handleConfigureImport"
      />
    </div>

    <!-- List View -->
    <div v-else class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <FileListTable
        :files="files"
        :selected-files="selectedFiles"
        @toggle-selection="toggleFileSelection"
        @toggle-all="toggleSelectAll"
        @preview="previewFile"
        @download="downloadFile"
        @delete="confirmDeleteFile"
        @configure-import="handleConfigureImport"
      />
    </div>

    <!-- Modals -->
    <FilePreviewModal
      v-if="showPreviewModal"
      :file="previewingFile"
      :project-id="projectId"
      @close="closePreview"
    />

    <DeleteConfirmationModal
      v-if="showDeleteModal"
      :title="deleteModalTitle"
      :message="deleteModalMessage"
      :is-processing="isDeleting"
      @confirm="executeDelete"
      @cancel="cancelDelete"
    />

    <DuplicateFilesModal
      v-if="showDuplicatesModal"
      :duplicates="duplicateFiles"
      @proceed="proceedWithDuplicates"
      @cancel="cancelDuplicates"
    />

    <!-- File Batch Actions Modal -->
    <FileBatchActionsModal
      v-if="showBatchActionsModal"
      :action="batchAction"
      :selected-files="selectedFiles.map(id => files.find(f => f.id === id)).filter(Boolean)"
      :project-id="projectId"
      @close="closeBatchActions"
      @complete="handleBatchComplete"
    />
    <FileImportConfigModal
      v-if="showImportConfigModal && importConfigFile"
      :file="importConfigFile"
      :project-id="projectId"
      @close="() => { showImportConfigModal = false; importConfigFile = null; fetchFiles(); }"
      @saved="fetchFiles"
    />

  </div>
</template>


<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import { debounce } from 'perfect-debounce';
import LoadingSpinner from './common/LoadingSpinner.vue';
import ErrorAlert from './common/ErrorAlert.vue';
import FileCard from './files/FileCard.vue';
import FileListTable from './files/FileListTable.vue';
import FilePreviewModal from './files/FilePreviewModal.vue';
import FileBatchActionsModal from './files/FileBatchActionsModal.vue';
import DeleteConfirmationModal from './files/DeleteConfirmationModal.vue';
import DuplicateFilesModal from './files/DuplicateFilesModal.vue';
import UploadProgress from './files/UploadProgress.vue';
import FileDropZone from './files/FileDropZone.vue';
import FileImportConfigModal from './files/FileImportConfigModal.vue';


const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['files-changed']);
const toast = useToast();

// State
const files = ref([]);
const stats = ref({
  total_files: 0,
  total_size: 0,
  unique_files: 0,
  recent_files: 0,
  duplicates: 0,
  by_type: []
});
const isLoading = ref(true);
const error = ref('');
const viewMode = ref('grid');
const selectedFiles = ref([]);
const fileInputRef = ref(null);

// Upload state
const isUploading = ref(false);
const uploadQueue = ref([]);
const currentUploadingFile = ref('');
const uploadProgress = ref(0);
const uploadAbortController = ref(null);

// Modal state
const showPreviewModal = ref(false);
const previewingFile = ref(null);
const previewUrl = ref('');
const previewText = ref('');

// Delete modal state
const showDeleteModal = ref(false);
const deleteModalTitle = ref('');
const deleteModalMessage = ref('');
const isDeleting = ref(false);
const filesToDelete = ref([]);
const deleteMode = ref(''); // 'single' or 'batch'

// Duplicate detection
const showDuplicatesModal = ref(false);
const duplicateFiles = ref([]);
const pendingUploads = ref([]);

// Batch actions
const showBatchActionsModal = ref(false);
const batchAction = ref('');

// File Import Config Modal
const showImportConfigModal = ref(false)
const importConfigFile = ref(null)

function isCSVXLSX(file) {
  if (!file || !file.file_type) return false;
  return (
    file.file_type === 'text/csv' ||
    file.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    file.file_type === 'application/vnd.ms-excel'
  );
}

function uploadedFileTypeIsCSVXLSX(file) {
  if (!file) return false;
  const type = file.type || '';
  const name = file.name?.toLowerCase() || '';
  return (
    type === 'text/csv' ||
    type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    type === 'application/vnd.ms-excel' ||
    name.endsWith('.csv') ||
    name.endsWith('.xlsx') ||
    name.endsWith('.xls')
  );
}



// Filters
const filters = ref({
  search: '',
  fileType: '',
  fileCreator: 'user', // Default to 'user' to show only user-uploaded files
  dateRange: '',
  date_from: null,
  date_to: null,
  minSize: null,
  maxSize: null
});

// Debounced search
const debouncedFetch = debounce(() => {
  fetchFiles();
}, 300);

// Watch filters
watch(() => filters.value, () => {
  fetchFiles();
}, { deep: true });

watch(files, (newFiles, oldFiles) => {
  // Find unconfigured CSV/XLSX file
  const unconfigured = newFiles.find(
    file => isCSVXLSX(file) && !file.preprocessing_strategy
  );
  if (unconfigured) {
    importConfigFile.value = unconfigured;
    showImportConfigModal.value = true;
  }
});


const handleConfigureImport = (file) => {
  importConfigFile.value = file;
  showImportConfigModal.value = true;
};

// Format file size
const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const handleFilesSelected = async (files, errors) => {
  // Show errors if any
  errors.forEach(err => {
    toast.warning(`${err.file}: ${err.error}`);
  });

  // Process valid files
  if (files.length > 0) {
    await handleFileUpload({ target: { files } });
  }
};

const selectAllFiles = () => {
  selectedFiles.value = files.value.map(f => f.id);
  toast.info(`Selected all ${files.value.length} files`);
};

// Apply date filter
const applyDateFilter = () => {
  const now = new Date();
  switch (filters.value.dateRange) {
    case 'today':
      filters.value.date_from = new Date(now.setHours(0, 0, 0, 0)).toISOString();
      filters.value.date_to = new Date().toISOString();
      break;
    case 'week':
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      filters.value.date_from = weekAgo.toISOString();
      filters.value.date_to = new Date().toISOString();
      break;
    case 'month':
      const monthAgo = new Date();
      monthAgo.setDate(monthAgo.getDate() - 30);
      filters.value.date_from = monthAgo.toISOString();
      filters.value.date_to = new Date().toISOString();
      break;
    default:
      delete filters.value.date_from;
      delete filters.value.date_to;
  }
};

async function sha256Hex(buffer) {
  const subtle = globalThis.crypto?.subtle;
  if (subtle && typeof subtle.digest === 'function') {
    const hashBuf = await subtle.digest('SHA-256', buffer);
    return Array.from(new Uint8Array(hashBuf))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }
  // Fallback: load crypto-js only when needed (npm install crypto-js)
  const CryptoJS = (await import('crypto-js')).default;
  const wordArray = CryptoJS.lib.WordArray.create(new Uint8Array(buffer));
  return CryptoJS.SHA256(wordArray).toString(CryptoJS.enc.Hex);
}

// Enhanced file upload with duplicate detection
const handleFileUpload = async (event) => {
  const selectedFiles = Array.from(event.target.files);
  if (!selectedFiles.length) return;

  // Calculate hashes for duplicate detection
  const fileHashes = await Promise.all(
    selectedFiles.map(async (file) => {
      const buffer = await file.arrayBuffer();
      const hashHex = await sha256Hex(buffer);
      return {
        filename: file.name,
        hash: hashHex,
        file: file
      };
    })
  );

  // Check for duplicates
  try {
    const response = await api.post(
      `/project/${props.projectId}/file/check-duplicates`,
      fileHashes.map(f => ({ filename: f.filename, hash: f.hash }))
    );

    const duplicates = response.data.filter(f => f.exists);

    if (duplicates.length > 0) {
      duplicateFiles.value = duplicates;
      pendingUploads.value = fileHashes.filter(
        f => !duplicates.some(d => d.hash === f.hash)
      );
      showDuplicatesModal.value = true;
    } else {
      await uploadFiles(fileHashes);
    }
  } catch (err) {
    toast.error('Failed to check for duplicates');
    console.error(err);
  }

  event.target.value = null;
};

// Process uploads after duplicate check
const proceedWithDuplicates = async (skipDuplicates) => {
  showDuplicatesModal.value = false;

  if (skipDuplicates) {
    await uploadFiles(pendingUploads.value);
  } else {
    // Upload all files including duplicates
    const allFiles = [...pendingUploads.value];
    duplicateFiles.value.forEach(dup => {
      const file = uploadQueue.value.find(f => f.hash === dup.hash);
      if (file) allFiles.push(file);
    });
    await uploadFiles(allFiles);
  }

  pendingUploads.value = [];
  duplicateFiles.value = [];
};

const cancelDuplicates = () => {
  showDuplicatesModal.value = false;
  pendingUploads.value = [];
  duplicateFiles.value = [];
  toast.info('Upload cancelled');
};

// Upload files with progress tracking
const uploadFiles = async (fileData) => {
  isUploading.value = true;
  uploadQueue.value = fileData.map(f => f.filename);
  error.value = '';

  let successCount = 0;
  let failedFiles = [];

  let justUploadedFiles = [];

  for (let i = 0; i < fileData.length; i++) {
    const { file, hash } = fileData[i];
    currentUploadingFile.value = file.name;
    uploadProgress.value = 0;

    try {
      const fileInfo = JSON.stringify({
        file_name: file.name,
        file_type: file.type || 'application/octet-stream',
        file_size: file.size,
        file_hash: hash,
        description: ''
      });

      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_info', fileInfo);

      uploadAbortController.value = new AbortController();

      // Actual upload
      const response = await api.post(
        `/project/${props.projectId}/file`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          signal: uploadAbortController.value.signal,
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            uploadProgress.value = percentCompleted;
          }
        }
      );

      justUploadedFiles.push(response.data); // <--- Save uploaded file with backend info (including id)
      successCount++;
    } catch (err) {
      if (err.name === 'CanceledError') {
        toast.warning('Upload cancelled');
        break;
      }

      failedFiles.push(file.name);
      console.error(`Failed to upload ${file.name}:`, err);

      if (err.response?.status === 409) {
        toast.warning(`${file.name} already exists`, {
          timeout: 3000
        });
      } else {
        toast.error(`Failed to upload ${file.name}`, {
          timeout: 3000
        });
      }
    }
  }

  // Show summary
  if (successCount > 0) {
    toast.success(`Successfully uploaded ${successCount} file${successCount !== 1 ? 's' : ''}`, {
      timeout: 5000
    });
  }

  if (failedFiles.length > 0) {
    toast.error(`Failed to upload ${failedFiles.length} file${failedFiles.length !== 1 ? 's' : ''}`, {
      timeout: 5000
    });
  }

  isUploading.value = false;
  currentUploadingFile.value = '';
  uploadProgress.value = 0;
  uploadQueue.value = [];
  uploadAbortController.value = null;

  await fetchFiles();
  await fetchStats();
  emit('files-changed');

  // ======== OPEN CSV/XLSX IMPORT CONFIG MODAL IF NEEDED =========
  // For each file just uploaded, if CSV/XLSX and not configured, open config modal
  for (const uploadedFile of justUploadedFiles) {
    if (uploadedFileTypeIsCSVXLSX(uploadedFile) && !uploadedFile.preprocessing_strategy) {
      importConfigFile.value = uploadedFile; // file object from backend, includes id!
      showImportConfigModal.value = true;
      break; // Open one at a time (modal flow)
    }
  }
};


// Cancel ongoing upload
const cancelUpload = () => {
  if (uploadAbortController.value) {
    uploadAbortController.value.abort();
  }
};

// Toggle file selection
const toggleFileSelection = (fileId) => {
  const index = selectedFiles.value.indexOf(fileId);
  if (index > -1) {
    selectedFiles.value.splice(index, 1);
  } else {
    selectedFiles.value.push(fileId);
  }
};

// Toggle select all
const toggleSelectAll = () => {
  if (selectedFiles.value.length === files.value.length) {
    selectedFiles.value = [];
  } else {
    selectedFiles.value = files.value.map(f => f.id);
  }
};

// Download selected files
const downloadSelected = async () => {
  for (const fileId of selectedFiles.value) {
    const file = files.value.find(f => f.id === fileId);
    if (file) {
      await downloadFile(file);
    }
  }
  toast.success(`Downloaded ${selectedFiles.value.length} files`);
};

// Download single file
const downloadFile = async (file) => {
  try {
    const response = await api.get(
      `/project/${props.projectId}/file/${file.id}/content`,
      { responseType: 'blob' }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', file.file_name);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    toast.error(`Failed to download ${file.file_name}`);
    console.error(err);
  }
};

// Preview file
const previewFile = async (file) => {
  previewingFile.value = file;
  showPreviewModal.value = true;
  previewUrl.value = '';
  previewText.value = '';

  try {
    const response = await api.get(
      `/project/${props.projectId}/file/${file.id}/content?preview=true`,
      { responseType: 'blob' }
    );

    if (file.file_type === 'text/plain' || file.file_type === 'text/csv') {
      // For text files, read as text
      const text = await response.data.text();
      previewText.value = text;
      previewUrl.value = 'text';
    } else {
      // For other files, create blob URL
      previewUrl.value = URL.createObjectURL(response.data);
    }
  } catch (err) {
    toast.error('Failed to load preview');
    console.error('Failed to get file preview:', err);
  }
};

// Close preview
const closePreview = () => {
  showPreviewModal.value = false;
  if (previewUrl.value && previewUrl.value !== 'text') {
    URL.revokeObjectURL(previewUrl.value);
  }
  previewUrl.value = '';
  previewText.value = '';
  previewingFile.value = null;
};

const confirmBatchDelete = () => {
  if (selectedFiles.value.length === 0) {
    toast.warning('Please select files first');
    return;
  }

  filesToDelete.value = selectedFiles.value.map(id => files.value.find(f => f.id === id)).filter(Boolean);
  deleteMode.value = 'batch';
  deleteModalTitle.value = 'Delete Multiple Files';
  deleteModalMessage.value = `Are you sure you want to delete ${selectedFiles.value.length} files? This action cannot be undone.`;
  showDeleteModal.value = true;
};

// Confirm delete file(s)
const confirmDeleteFile = (file) => {
  filesToDelete.value = [file];
  deleteMode.value = 'single';
  deleteModalTitle.value = 'Delete File';
  deleteModalMessage.value = `Are you sure you want to delete "${file.file_name}"? This action cannot be undone.`;
  showDeleteModal.value = true;
};

// Show batch delete confirmation
const showBatchDelete = () => {
  filesToDelete.value = selectedFiles.value.map(id => files.value.find(f => f.id === id));
  deleteMode.value = 'batch';
  deleteModalTitle.value = 'Delete Multiple Files';
  deleteModalMessage.value = `Are you sure you want to delete ${selectedFiles.value.length} files? This action cannot be undone.`;
  showDeleteModal.value = true;
};

const executeDelete = async () => {
  isDeleting.value = true;

  try {
    if (deleteMode.value === 'single') {
      await api.delete(`/project/${props.projectId}/file/${filesToDelete.value[0].id}`);
      toast.success('File deleted successfully');
    } else {
      // Batch delete
      const response = await api.post(
        `/project/${props.projectId}/file/batch-delete`,
        {
          file_ids: filesToDelete.value.map(f => f.id),
          force: false
        }
      );

      if (response.data.total_deleted > 0) {
        toast.success(`Deleted ${response.data.total_deleted} files`);
      }

      if (response.data.errors && response.data.errors.length > 0) {
        response.data.errors.forEach(error => {
          toast.error(`Failed to delete file: ${error.error}`);
        });
      }

      selectedFiles.value = [];
    }

    await fetchFiles();
    await fetchStats();
    emit('files-changed');
  } catch (err) {
    if (err.response?.status === 409) {
      const detail = err.response?.data?.detail;
      if (detail && detail.links) {
        toast.error(`Cannot delete: File has ${detail.links.documents} linked documents and ${detail.links.preprocessing_tasks} preprocessing tasks`);
      } else {
        toast.error('Cannot delete file: it is linked to other resources');
      }
    } else {
      toast.error('Failed to delete file(s)');
    }
    console.error(err);
  } finally {
    isDeleting.value = false;
    showDeleteModal.value = false;
    filesToDelete.value = [];
    deleteMode.value = '';
  }
};

// Cancel delete
const cancelDelete = () => {
  showDeleteModal.value = false;
  filesToDelete.value = [];
  deleteMode.value = '';
};

// Fetch files with filters
const fetchFiles = async () => {
  isLoading.value = true;
  try {
    const params = new URLSearchParams();

    if (filters.value.search) params.append('search', filters.value.search);
    if (filters.value.fileType) params.append('file_type', filters.value.fileType);
    if (filters.value.fileCreator) params.append('file_creator', filters.value.fileCreator);
    if (filters.value.date_from) params.append('date_from', filters.value.date_from);
    if (filters.value.date_to) params.append('date_to', filters.value.date_to);
    if (filters.value.minSize) params.append('min_size', filters.value.minSize);
    if (filters.value.maxSize) params.append('max_size', filters.value.maxSize);

    const response = await api.get(`/project/${props.projectId}/file?${params}`);
    files.value = response.data;
  } catch (err) {
    error.value = 'Failed to load files';
    toast.error('Failed to load files');
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};


// Fetch file statistics
const fetchStats = async () => {
  try {
    const params = new URLSearchParams();
    if (filters.value.fileCreator) params.append('file_creator', filters.value.fileCreator);

    const response = await api.get(`/project/${props.projectId}/file/stats?${params}`);
    stats.value = response.data;
  } catch (err) {
    console.error('Failed to fetch file stats:', err);
  }
};


const showBatchDownload = () => {
  if (selectedFiles.value.length === 0) {
    toast.warning('Please select files first');
    return;
  }
  batchAction.value = 'download';
  showBatchActionsModal.value = true;
};

const showBatchMove = () => {
  if (selectedFiles.value.length === 0) {
    toast.warning('Please select files first');
    return;
  }
  batchAction.value = 'move';
  showBatchActionsModal.value = true;
};

const closeBatchActions = () => {
  showBatchActionsModal.value = false;
  batchAction.value = '';
};

const handleBatchComplete = () => {
  closeBatchActions();
  selectedFiles.value = [];
  fetchFiles();
  fetchStats();
  emit('files-changed');
};

onMounted(() => {
  fetchFiles();
  fetchStats();
});

// Cleanup on unmount
onUnmounted(() => {
  if (previewUrl.value && previewUrl.value !== 'text') {
    URL.revokeObjectURL(previewUrl.value);
  }
});
</script>
