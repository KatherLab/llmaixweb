<template>
  <div
    :class="[
      'relative border-2 border-dashed rounded-lg transition-all duration-200',
      isDragging
        ? 'border-blue-500 bg-blue-50'
        : 'border-gray-300 hover:border-gray-400',
      disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
    ]"
    @drop="handleDrop"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @click="!disabled && $refs.fileInput.click()"
  >
    <input
      ref="fileInput"
      type="file"
      :accept="accept"
      :multiple="multiple"
      class="hidden"
      @change="handleFileSelect"
      :disabled="disabled"
    />

    <div class="p-8 text-center">
      <svg
        :class="[
          'mx-auto h-12 w-12 transition-colors',
          isDragging ? 'text-blue-500' : 'text-gray-400'
        ]"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
        />
      </svg>

      <p class="mt-2 text-sm font-medium text-gray-900">
        {{ isDragging ? 'Drop files here' : 'Drop files or click to upload' }}
      </p>

      <p class="mt-1 text-xs text-gray-500">
        {{ acceptLabel }}
      </p>

      <div v-if="maxSize" class="mt-2 text-xs text-gray-500">
        Maximum file size: {{ formatFileSize(maxSize) }}
      </div>
    </div>

    <!-- Upload overlay when dragging -->
    <div
      v-if="isDragging"
      class="absolute inset-0 bg-blue-500 bg-opacity-10 rounded-lg pointer-events-none"
    >
      <div class="flex items-center justify-center h-full">
        <div class="bg-white rounded-lg shadow-lg p-4">
          <svg class="h-8 w-8 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { getAcceptedFileTypes } from '@/utils/fileTypes';

const props = defineProps({
  accept: {
    type: String,
    default: () => getAcceptedFileTypes()
  },
  multiple: {
    type: Boolean,
    default: true
  },
  maxSize: {
    type: Number,
    default: 100 * 1024 * 1024 // 100MB
  },
  disabled: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['files-selected']);

const isDragging = ref(false);
const fileInput = ref(null);

const acceptLabel = computed(() => {
  const types = props.accept.split(',').map(t => {
    const parts = t.split('/');
    return parts[1] || parts[0];
  });

  if (types.length > 5) {
    return `${types.slice(0, 5).join(', ')} and more`;
  }
  return types.join(', ');
});

const formatFileSize = (bytes) => {
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const validateFiles = (files) => {
  const validFiles = [];
  const errors = [];

  for (const file of files) {
    if (props.maxSize && file.size > props.maxSize) {
      errors.push({
        file: file.name,
        error: `File size exceeds ${formatFileSize(props.maxSize)}`
      });
      continue;
    }

    validFiles.push(file);
  }

  return { validFiles, errors };
};

const handleDrop = (event) => {
  event.preventDefault();
  isDragging.value = false;

  if (props.disabled) return;

  const files = Array.from(event.dataTransfer.files);
  const { validFiles, errors } = validateFiles(files);

  if (validFiles.length > 0) {
    emit('files-selected', validFiles, errors);
  }
};

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  const { validFiles, errors } = validateFiles(files);

  if (validFiles.length > 0) {
    emit('files-selected', validFiles, errors);
  }

  // Reset input
  event.target.value = null;
};
</script>
