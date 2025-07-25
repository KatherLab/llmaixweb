<template>
  <div
    :class="[
      'relative group bg-white rounded-lg border-2 p-4 transition-all cursor-pointer',
      selected ? 'border-blue-500 shadow-md' : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
    ]"
    @click="$emit('toggle-selection', document.id)"
  >
    <!-- Selection Checkbox -->
    <div class="absolute top-2 right-2">
      <input
        type="checkbox"
        :checked="selected"
        @click.stop
        @change="$emit('toggle-selection', document.id)"
        class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
      />
    </div>

    <!-- Document Icon -->
    <div class="flex items-start space-x-3 mb-3">
      <div class="flex-shrink-0">
        <FileIcon :fileType="document.original_file?.file_type" :size="48" />
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-medium text-gray-900 truncate" :title="documentTitle">
          {{ documentTitle }}
        </h3>
        <p class="text-xs text-gray-500 mt-1">
          {{ formatDate(document.created_at) }}
        </p>
      </div>
    </div>

    <!-- Text Preview -->
    <div class="mb-3">
      <p class="text-xs text-gray-600 line-clamp-3">
        {{ document.text || 'No text content available' }}
      </p>
    </div>

    <!-- Preprocessing Info -->
    <div class="flex items-center justify-between text-xs">
      <div class="flex items-center space-x-2">
        <span
          :class="[
            'inline-flex items-center px-2 py-0.5 rounded-full font-medium',
            getStatusClass(document.preprocessing_status)
          ]"
        >
          {{ document.preprocessing_status || 'Processed' }}
        </span>
        <span v-if="document.preprocessing_config?.name" class="text-gray-500">
          {{ document.preprocessing_config.name }}
        </span>
      </div>
    </div>

    <!-- Actions -->
    <div class="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-2">
      <button
        @click.stop="$emit('view', document)"
        class="p-1 text-blue-600 hover:text-blue-800"
        title="View"
      >
        <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      </button>
      <button
        @click.stop="$emit('download', document)"
        class="p-1 text-gray-600 hover:text-gray-800"
        title="Download"
      >
        <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import FileIcon from '../common/FileIcon.vue';

const props = defineProps({
  document: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['toggle-selection', 'view', 'download']);

const documentTitle = computed(() => {
  return props.document.document_name || props.document.original_file?.file_name || `Document #${props.document.id}`;
});

const getStatusClass = (status) => {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800';
    case 'partial':
      return 'bg-yellow-100 text-yellow-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
};
</script>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
