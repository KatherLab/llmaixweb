<script setup>
import { computed } from 'vue';
import { formatDate } from '@/utils/formatters';

const props = defineProps({
  trial: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['view', 'retry', 'delete']);

// Format progress as percentage
const progressPercentage = computed(() => {
  if (!props.trial.progress && props.trial.progress !== 0) return null;
  return Math.round(props.trial.progress * 100);
});

// Determine if the trial is active (in progress)
const isActive = computed(() => {
  return !['completed', 'failed'].includes(props.trial.status);
});

// Compute status display classes
const statusClass = computed(() => {
  const statusMap = {
    'pending': 'bg-yellow-100 text-yellow-800',
    'processing': 'bg-blue-100 text-blue-800',
    'completed': 'bg-green-100 text-green-800',
    'failed': 'bg-red-100 text-red-800'
  };
  return statusMap[props.trial.status] || 'bg-gray-100 text-gray-800';
});

// Get trial results summary
const resultSummary = computed(() => {
  if (!props.trial.results || props.trial.results.length === 0) {
    return null;
  }
  return props.trial.results.length === 1
    ? '1 document processed'
    : `${props.trial.results.length} documents processed`;
});
</script>

<template>
  <div class="border rounded-lg overflow-hidden bg-white shadow-sm">
    <div class="p-4">
      <div class="flex flex-col md:flex-row md:justify-between md:items-center">
        <div>
          <h3 class="font-medium flex items-center">
            Trial #{{ trial.id }}
            <span :class="['ml-2 text-xs px-2 py-1 rounded-full', statusClass]">
              {{ trial.status }}
            </span>
          </h3>
          <p class="text-sm text-gray-500">
            {{ trial.document_ids.length }} document(s) • Started {{ formatDate(trial.created_at) }}
          </p>
          <p class="text-sm mt-1">
            Model: {{ trial.llm_model }}
          </p>
        </div>

        <div class="mt-3 md:mt-0 space-y-3 md:text-right md:flex md:flex-col md:items-end">
          <div v-if="resultSummary" class="text-sm text-green-600">
            {{ resultSummary }}
          </div>

          <div v-if="isActive" class="md:w-32 space-y-1">
            <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                class="h-full bg-blue-500 transition-all duration-300 ease-out"
                :style="{ width: progressPercentage !== null ? `${progressPercentage}%` : '0%' }"
              ></div>
            </div>
            <p class="text-xs text-gray-500">
              {{ progressPercentage !== null ? `${progressPercentage}%` : 'Processing...' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="mt-4 flex justify-end gap-2">
        <button
          v-if="trial.results && trial.results.length > 0"
          @click="emit('view', trial)"
          class="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
        >
          View Results
        </button>

        <button
          v-if="trial.status === 'completed' || trial.status === 'failed'"
          @click="emit('retry', trial)"
          class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm"
        >
          Retry
        </button>

        <button
          @click="emit('delete', trial)"
          class="px-3 py-1.5 bg-white hover:bg-gray-100 text-red-600 rounded-md border border-gray-300 text-sm"
        >
          Delete
        </button>
      </div>
    </div>
  </div>
</template>
