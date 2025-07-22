<template>
  <div
    :class="[
      'bg-white border rounded-lg shadow-sm overflow-hidden transition-all duration-200',
      selected ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:shadow-md'
    ]"
  >
    <div class="p-4">
      <div class="flex items-start justify-between">
        <div class="flex items-center space-x-3">
          <input
            type="checkbox"
            :checked="selected"
            @change="$emit('toggle-selection', file.id)"
            class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            @click.stop
          />
          <FileIcon :fileType="file.file_type" :size="48" />
          <div class="flex-1 min-w-0">
            <h3 class="text-sm font-medium text-gray-900 truncate" :title="file.file_name">
              {{ file.file_name }}
            </h3>
            <p class="text-xs text-gray-500 mt-1">
              {{ formatFileSize(file.file_size) }} • {{ formatDate(file.created_at) }}
            </p>
            <p v-if="file.description" class="text-xs text-gray-600 mt-1 truncate">
              {{ file.description }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="bg-gray-50 px-4 py-3 border-t flex justify-between items-center">
      <span class="text-xs text-gray-500">
        {{ getFileTypeLabel(file.file_type) }}
      </span>
      <div class="flex items-center space-x-2">
        <button
          @click="$emit('preview', file)"
          class="text-blue-600 hover:text-blue-800 p-1"
          title="Preview"
        >
          <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        </button>
        <button
          @click="$emit('download', file)"
          class="text-gray-600 hover:text-gray-800 p-1"
          title="Download"
        >
          <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
          </svg>
        </button>
        <button
          @click="$emit('delete', file)"
          class="text-red-600 hover:text-red-800 p-1"
          title="Delete"
        >
          <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import FileIcon from '../common/FileIcon.vue';

defineProps({
  file: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
});

defineEmits(['toggle-selection', 'preview', 'download', 'delete']);

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
};

const getFileTypeLabel = (mimeType) => {
  const typeMap = {
    'application/pdf': 'PDF',
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'text/plain': 'Text',
    'text/csv': 'CSV',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word'
  };
  return typeMap[mimeType] || 'File';
};
</script>
