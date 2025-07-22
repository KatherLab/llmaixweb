<!-- Update FileBatchActionsModal.vue template - remove move action and fix delete -->
<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="$emit('close')"
      style="backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); background: rgba(30,30,40,0.27);"
    >
      <div
        class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[90vh] border border-gray-200"
        tabindex="0"
        ref="modalRef"
        @keydown.esc="$emit('close')"
      >
        <!-- Header -->
        <div class="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b rounded-t-2xl">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                <svg
                  v-if="action === 'download'"
                  class="w-5 h-5 mr-2 text-blue-600"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                </svg>
                {{ actionTitle }}
              </h3>
              <p class="mt-1 text-sm text-gray-500">
                {{ fileCount }} file{{ fileCount !== 1 ? 's' : '' }} selected ({{ formatTotalSize(totalSize) }})
              </p>
            </div>
            <button
              @click="$emit('close')"
              class="text-gray-400 hover:text-gray-600 transition-colors p-1 hover:bg-gray-100 rounded-lg"
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-6">
          <!-- Download Action -->
          <div v-if="action === 'download'" class="space-y-4">
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p class="text-sm text-blue-800">
                The selected files will be downloaded to your default download location.
                Large files may take some time to process.
              </p>
            </div>

            <div class="space-y-3">
              <h4 class="text-sm font-medium text-gray-900">Download Options</h4>
              <label class="flex items-center">
                <input
                  v-model="downloadAsZip"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span class="ml-2 text-sm text-gray-700">
                  Download as ZIP archive
                  <span class="text-gray-500">(recommended for multiple files)</span>
                </span>
              </label>
              <label v-if="downloadAsZip" class="flex items-center ml-6">
                <input
                  v-model="includeMetadata"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span class="ml-2 text-sm text-gray-700">
                  Include metadata file (JSON)
                </span>
              </label>
            </div>

            <!-- File List Preview -->
            <div class="mt-4">
              <h4 class="text-sm font-medium text-gray-900 mb-2">Files to download:</h4>
              <div class="max-h-48 overflow-y-auto space-y-2 border border-gray-200 rounded-lg p-3">
                <div
                  v-for="file in selectedFiles"
                  :key="file.id"
                  class="flex items-center justify-between text-sm"
                >
                  <div class="flex items-center">
                    <FileIcon :fileType="file.file_type" :size="24" />
                    <span class="ml-2 text-gray-700 truncate max-w-xs">{{ file.file_name }}</span>
                  </div>
                  <span class="text-gray-500">{{ formatFileSize(file.file_size) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-6 py-4 bg-gray-50 border-t rounded-b-2xl flex justify-between items-center">
          <div class="text-sm text-gray-500">
            <span v-if="isProcessing">
              Processing {{ processedCount }} of {{ fileCount }}...
            </span>
          </div>
          <div class="flex space-x-3">
            <button
              @click="$emit('close')"
              :disabled="isProcessing"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              @click="performAction"
              :disabled="!canPerformAction || isProcessing"
              class="px-4 py-2 text-sm font-medium rounded-lg transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed flex items-center"
            >
              <svg v-if="isProcessing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ actionButtonText }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>


<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import FileIcon from '../common/FileIcon.vue';

const props = defineProps({
  action: {
    type: String,
    required: true
  },
  selectedFiles: {
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
const modalRef = ref(null);

// State
const isProcessing = ref(false);
const processedCount = ref(0);

// Download options
const downloadAsZip = ref(true);
const includeMetadata = ref(true);

// Move options
const projects = ref([]);
const targetProjectId = ref(null);
const projectSearch = ref('');

// Delete options
const confirmDelete = ref(false);
const forceDelete = ref(false);
const linkedDocuments = ref(0);
const linkedTasks = ref(0);

// Computed
const fileCount = computed(() => props.selectedFiles.length);
const totalSize = computed(() => props.selectedFiles.reduce((sum, file) => sum + (file.file_size || 0), 0));
const currentProjectId = computed(() => parseInt(props.projectId));

const hasLinkedFiles = computed(() => {
  return props.selectedFiles.some(file => file.is_linked);
});

const actionTitle = computed(() => {
  switch (props.action) {
    case 'download': return 'Download Files';
    case 'move': return 'Move Files';
    case 'delete': return 'Delete Files';
    default: return 'Batch Action';
  }
});

const actionButtonText = computed(() => {
  if (isProcessing.value) return 'Processing...';
  switch (props.action) {
    case 'download':
      return downloadAsZip.value ? 'Download as ZIP' : `Download ${fileCount.value} Files`;
    case 'move': return 'Move Files';
    case 'delete': return 'Delete Files';
    default: return 'Confirm';
  }
});

const canPerformAction = computed(() => {
  switch (props.action) {
    case 'download': return true;
    case 'move': return targetProjectId.value !== null && targetProjectId.value !== currentProjectId.value;
    case 'delete': return confirmDelete.value && (!hasLinkedFiles.value || forceDelete.value);
    default: return false;
  }
});

const filteredProjects = computed(() => {
  if (!projectSearch.value) return projects.value;
  const search = projectSearch.value.toLowerCase();
  return projects.value.filter(p => p.name.toLowerCase().includes(search));
});

// Methods
const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const formatTotalSize = (bytes) => {
  return formatFileSize(bytes);
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
};

const performAction = async () => {
  if (!canPerformAction.value) return;

  isProcessing.value = true;
  processedCount.value = 0;

  try {
    switch (props.action) {
      case 'download':
        await downloadFiles();
        break;
      case 'move':
        await moveFiles();
        break;
      case 'delete':
        await deleteFiles();
        break;
    }

    emit('complete');
  } catch (error) {
    toast.error(`Failed to ${props.action} files: ${error.message}`);
    console.error(error);
  } finally {
    isProcessing.value = false;
  }
};

const downloadFiles = async () => {
  if (downloadAsZip.value) {
    // Download as ZIP
    const fileIds = props.selectedFiles.map(f => f.id);
    const response = await api.post(
      `/project/${props.projectId}/file/download-zip`,
      {
        file_ids: fileIds,
        include_metadata: includeMetadata.value
      },
      { responseType: 'blob' }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `files_${new Date().getTime()}.zip`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    toast.success('Files downloaded as ZIP');
  } else {
    // Download individually
    for (const file of props.selectedFiles) {
      await downloadSingleFile(file);
      processedCount.value++;
    }
    toast.success(`Downloaded ${fileCount.value} files`);
  }
};

const downloadSingleFile = async (file) => {
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
};

const moveFiles = async () => {
  const fileIds = props.selectedFiles.map(f => f.id);
  await api.post(`/project/${props.projectId}/file/move`, {
    file_ids: fileIds,
    target_project_id: targetProjectId.value
  });

  toast.success(`Moved ${fileCount.value} files to another project`);
};

const deleteFiles = async () => {
  const response = await api.post(
    `/project/${props.projectId}/file/batch-delete`,
    {
      file_ids: props.selectedFiles.map(f => f.id),
      force: forceDelete.value
    }
  );

  if (response.data.total_deleted > 0) {
    toast.success(`Deleted ${response.data.total_deleted} files`);
  }

  if (response.data.errors.length > 0) {
    response.data.errors.forEach(error => {
      toast.error(`Failed to delete file: ${error.error}`);
    });
  }
};

const fetchProjects = async () => {
  try {
    const response = await api.get('/project/');
    projects.value = response.data.map(p => ({
      ...p,
      file_count: p.files?.length || 0
    }));
  } catch (error) {
    console.error('Failed to fetch projects:', error);
  }
};

const checkLinkedResources = async () => {
  // This would be an API call to check linked resources
  // For now, we'll use the is_linked property from files
  linkedDocuments.value = props.selectedFiles.filter(f => f.is_linked).length;
  linkedTasks.value = props.selectedFiles.filter(f => f.is_linked).length;
};

// Lifecycle
onMounted(() => {
  document.body.style.overflow = 'hidden';
  nextTick(() => {
    modalRef.value?.focus();
  });

  if (props.action === 'move') {
    fetchProjects();
  } else if (props.action === 'delete') {
    checkLinkedResources();
  }
});

onUnmounted(() => {
  document.body.style.overflow = '';
});
</script>
