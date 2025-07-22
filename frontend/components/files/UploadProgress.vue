<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
    <div class="flex items-center justify-between mb-2">
      <h4 class="text-sm font-medium text-gray-900">Uploading Files</h4>
      <button
        @click="$emit('cancel')"
        class="text-gray-400 hover:text-gray-600"
        title="Cancel upload"
      >
        <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="space-y-3">
      <div
        v-for="(file, index) in queue"
        :key="file"
        class="space-y-1"
      >
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-700 truncate max-w-xs">{{ file }}</span>
          <span class="text-gray-500">
            {{ currentFile === file ? `${progress}%` : index < queue.indexOf(currentFile) ? 'Complete' : 'Waiting' }}
          </span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            class="bg-blue-600 h-2 rounded-full transition-all duration-300"
            :style="{
              width: currentFile === file ? `${progress}%` : index < queue.indexOf(currentFile) ? '100%' : '0%'
            }"
          ></div>
        </div>
      </div>
    </div>

    <div class="mt-3 text-xs text-gray-500">
      {{ queue.indexOf(currentFile) + 1 }} of {{ queue.length }} files
    </div>
  </div>
</template>

<script setup>
defineProps({
  queue: {
    type: Array,
    required: true
  },
  currentFile: {
    type: String,
    required: true
  },
  progress: {
    type: Number,
    required: true
  }
});

defineEmits(['cancel']);
</script>
