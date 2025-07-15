<template>
  <div class="bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow">
    <div class="p-4">
      <!-- Task Header -->
      <div class="flex items-start justify-between mb-3">
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <div v-if="task.status === 'processing'" class="relative">
              <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <div v-else-if="task.status === 'completed'" class="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
              <svg class="h-5 w-5 text-green-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div v-else-if="task.status === 'failed'" class="h-8 w-8 rounded-full bg-red-100 flex items-center justify-center">
              <svg class="h-5 w-5 text-red-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div v-else class="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center">
              <svg class="h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>

          <div>
            <h4 class="font-semibold text-gray-900">
              Task #{{ task.id }}
              <span v-if="task.configuration?.name" class="text-sm font-normal text-gray-500">
                - {{ task.configuration.name }}
              </span>
            </h4>
            <p class="text-sm text-gray-500">
              {{ task.total_files }} file{{ task.total_files !== 1 ? 's' : '' }}
              <span v-if="task.started_at">• Started {{ formatRelativeTime(task.started_at) }}</span>
            </p>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center space-x-2">
          <button
            v-if="task.status === 'processing'"
            @click="$emit('cancel', task)"
            class="text-sm text-red-600 hover:text-red-800 font-medium"
          >
            Cancel
          </button>
          <button
            v-if="task.status === 'failed'"
            @click="$emit('retry', task)"
            class="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Retry
          </button>
          <button
            @click="$emit('view-details', task)"
            class="text-sm text-gray-600 hover:text-gray-800"
          >
            Details
          </button>
        </div>
      </div>

      <!-- Progress Bar -->
      <div v-if="task.status === 'processing'" class="mb-3">
        <div class="flex items-center justify-between text-sm text-gray-600 mb-1">
          <span>Processing...</span>
          <span>{{ Math.round(progress * 100) }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            class="bg-blue-600 h-2 rounded-full transition-all duration-300"
            :style="{ width: `${progress * 100}%` }"
          />
        </div>
        <div class="mt-1 text-xs text-gray-500">
          {{ task.processed_files }} of {{ task.total_files }} processed
          <span v-if="task.failed_files > 0" class="text-red-600">
            • {{ task.failed_files }} failed
          </span>
        </div>
      </div>

      <!-- Status Summary -->
      <div v-if="task.status === 'completed'" class="flex items-center justify-between text-sm">
        <div class="flex items-center space-x-4">
          <span class="text-green-600">
            <svg class="h-4 w-4 inline mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ task.processed_files - task.failed_files }} succeeded
          </span>
          <span v-if="task.failed_files > 0" class="text-red-600">
            <svg class="h-4 w-4 inline mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ task.failed_files }} failed
          </span>
        </div>
        <span class="text-gray-500">
          Completed in {{ formatDuration(task.started_at, task.completed_at) }}
        </span>
      </div>

      <!-- Error Message -->
      <div v-if="task.message && task.status === 'failed'" class="mt-3 p-3 bg-red-50 rounded-md">
        <p class="text-sm text-red-800">{{ task.message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['cancel', 'retry', 'view-details']);

const progress = computed(() => {
  if (props.task.total_files === 0) return 0;
  return props.task.processed_files / props.task.total_files;
});

const formatRelativeTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
};

const formatDuration = (start, end) => {
  if (!start || !end) return '';
  const diff = new Date(end) - new Date(start);
  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
};
</script>
