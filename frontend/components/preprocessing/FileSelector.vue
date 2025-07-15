<template>
  <div class="space-y-3">
    <!-- Search and Actions Bar -->
    <div class="flex items-center justify-between">
      <div class="flex-1 max-w-sm">
        <div class="relative">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search files..."
            class="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <svg class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <button
          @click="$emit('select-all')"
          class="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          Select All
        </button>
        <button
          v-if="selected.length > 0"
          @click="$emit('clear-selection')"
          class="text-sm text-gray-600 hover:text-gray-800"
        >
          Clear
        </button>
      </div>
    </div>

    <!-- File Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
      <div
        v-for="file in filteredFiles"
        :key="file.id"
        @click="toggleSelection(file.id)"
        :class="[
          'relative group cursor-pointer rounded-lg border-2 p-4 transition-all',
          isSelected(file.id)
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-200 hover:border-gray-300 bg-white'
        ]"
      >
        <!-- Selection Checkbox -->
        <div class="absolute top-2 right-2">
          <input
            type="checkbox"
            :checked="isSelected(file.id)"
            @click.stop
            @change="toggleSelection(file.id)"
            class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
        </div>

        <!-- File Icon -->
        <div class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <FileIcon :fileType="file.file_type" :size="32" />
          </div>

          <div class="flex-1 min-w-0">
            <h4 class="text-sm font-medium text-gray-900 truncate" :title="file.file_name">
              {{ file.file_name }}
            </h4>
            <p class="text-xs text-gray-500 mt-1">
              {{ formatFileSize(file.file_size) }} • {{ formatDate(file.created_at) }}
            </p>

            <!-- Processing Status -->
            <div v-if="file.preprocessing_status" class="mt-2">
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                  file.preprocessing_status === 'processed'
                    ? 'bg-green-100 text-green-800'
                    : file.preprocessing_status === 'processing'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                ]"
              >
                {{ file.preprocessing_status }}
              </span>
            </div>
          </div>
        </div>

        <!-- Preview Button -->
        <button
          v-if="showPreview"
          @click.stop="previewFile(file)"
          class="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <svg class="h-5 w-5 text-gray-400 hover:text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="filteredFiles.length === 0" class="text-center py-8">
      <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="mt-2 text-sm text-gray-600">
        {{ searchQuery ? 'No files match your search' : 'No files available' }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import FileIcon from '../common/FileIcon.vue';

const props = defineProps({
  files: {
    type: Array,
    required: true
  },
  selected: {
    type: Array,
    default: () => []
  },
  showPreview: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:selected', 'select-all', 'clear-selection', 'preview']);

const searchQuery = ref('');

const filteredFiles = computed(() => {
  if (!searchQuery.value) return props.files;

  const query = searchQuery.value.toLowerCase();
  return props.files.filter(file =>
    file.file_name.toLowerCase().includes(query)
  );
});

const isSelected = (fileId) => {
  return props.selected.includes(fileId);
};

const toggleSelection = (fileId) => {
  const newSelection = isSelected(fileId)
    ? props.selected.filter(id => id !== fileId)
    : [...props.selected, fileId];

  emit('update:selected', newSelection);
};

const previewFile = (file) => {
  emit('preview', file);
};

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown size';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
};
</script>
