<template>
  <div
    class="bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow cursor-pointer"
    @click="$emit('view-details', task)"
    tabindex="0"
    @keydown.enter="$emit('view-details', task)"
    :aria-label="`View details for Task #${task.id}`"
  >
    <div class="p-4">
      <!-- Task Header -->
      <div class="flex items-start justify-between mb-3">
        <div class="flex items-center space-x-3">
          <div class="flex-shrink-0">
            <div v-if="isActive" class="relative">
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
            <div v-else-if="task.status === 'cancelled'" class="h-8 w-8 rounded-full bg-yellow-100 flex items-center justify-center">
              <svg class="h-5 w-5 text-yellow-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                <path d="M12 8v4m0 4h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
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
              {{ total }} file{{ total !== 1 ? 's' : '' }}
              <span v-if="task.started_at">• Started {{ formatRelativeTime(task.started_at) }}</span>
            </p>
          </div>
        </div>
        <!-- Actions -->
        <div class="flex items-center space-x-2">
          <button
            v-if="isActive"
            @click.stop="handleCancel"
            :disabled="isCancelling"
            class="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-yellow-100 text-yellow-800 font-semibold border border-yellow-200 shadow hover:bg-yellow-200 transition disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Cancel task"
          >
            <svg v-if="isCancelling" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor"></path>
            </svg>
            <span v-else>Cancel</span>
          </button>
          <button
            v-if="task.status === 'failed'"
            @click.stop="$emit('retry', task)"
            class="text-sm text-blue-600 hover:text-blue-800 font-medium rounded px-2 py-1 transition-colors"
            aria-label="Retry failed task"
          >
            Retry
          </button>
          <button
            @click.stop="$emit('view-details', task)"
            class="text-sm text-gray-600 hover:text-gray-800 font-medium rounded px-2 py-1 transition-colors"
            aria-label="View details"
          >
            Details
          </button>
        </div>
      </div>

      <!-- ETA above Progress Bar -->
      <div v-if="isActive && task.meta && typeof task.meta.eta_seconds === 'number'" class="text-xs text-gray-600 mb-1">
        <span v-if="task.meta.eta_seconds > 0">≈ {{ prettyEta(task.meta.eta_seconds) }} left</span>
        <span v-else>Finishing…</span>
      </div>

      <!-- Progress Bar -->
      <div v-if="isActive" class="mb-3">
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
        <div class="mt-1 text-xs text-gray-500 flex items-center gap-4">
          <span>{{ actualProcessed }} of {{ total }} processed</span>
          <span v-if="failed > 0" class="text-red-600">• {{ failed }} failed</span>
          <span v-if="cancelled > 0" class="text-yellow-600">• {{ cancelled }} cancelled</span>
        </div>
      </div>

      <!-- Status Summary (Completed/Failed/Cancelled) -->
      <div v-if="task.status === 'completed'" class="flex flex-wrap gap-4 items-center text-sm mt-2 mb-1">
        <span v-if="completed > 0" class="flex items-center text-green-700 font-medium">
          <svg class="h-4 w-4 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ completed }} succeeded
        </span>
        <span
          v-if="failed > 0"
          class="flex items-center text-red-600 font-medium"
          :title="`${failed} failed`"
        >
          <svg class="h-4 w-4 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ failed }} failed
        </span>
        <span
          v-if="cancelled > 0"
          class="flex items-center text-yellow-600 font-medium"
          :title="`${cancelled} cancelled during processing`"
        >
          <svg class="h-4 w-4 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
            <path d="M12 9v2m0 4h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
          </svg>
          {{ cancelled }} cancelled
        </span>
        <span class="text-gray-500 ml-auto" v-if="task.completed_at">
          Completed in {{ formatDuration(task.started_at, task.completed_at) }}
        </span>
      </div>
      <div v-else-if="task.status === 'failed'" class="mt-3 p-3 bg-red-50 rounded-md">
        <p class="text-sm text-red-800">{{ task.message }}</p>
      </div>
      <div v-else-if="task.status === 'cancelled'" class="mt-3 p-3 bg-yellow-50 rounded-md">
        <p class="text-sm text-yellow-800">{{ task.message }}</p>
      </div>
      <div v-else-if="task.message && isActive" class="mt-3 p-3 bg-blue-50 rounded-md">
        <p class="text-sm text-blue-900">{{ task.message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
});
const emit = defineEmits(['cancel', 'retry', 'view-details']);

const isActive = computed(() =>
  ['pending', 'processing', 'in_progress'].includes(props.task.status)
);

const isCancelling = ref(false);

function handleCancel() {
  if (isCancelling.value) return;
  isCancelling.value = true;
  emit('cancel', props.task, () => { isCancelling.value = false });
}

// Progress and status breakdown
const total = computed(() => props.task.meta?.total_files || props.task.total_files || 1);
const completed = computed(() => props.task.meta?.completed_files || props.task.processed_files || 0);
const failed = computed(() => props.task.meta?.failed_files || props.task.failed_files || 0);
const cancelled = computed(() => props.task.meta?.cancelled_files || props.task.skipped_files || 0);

const actualProcessed = computed(() => completed.value + failed.value + cancelled.value);
const progress = computed(() => Math.min(actualProcessed.value / total.value, 1.0));

function prettyEta(sec) {
  if (!sec || isNaN(sec)) return "00:00:00";
  return new Date(sec * 1000).toISOString().substring(11, 19);
}

function formatRelativeTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}

function formatDuration(start, end) {
  if (!start || !end) return '';
  const diff = new Date(end) - new Date(start);
  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}
</script>

<style scoped>
:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}
.cursor-pointer { cursor: pointer; }
button { transition: all 0.2s ease-in-out; }
@media (max-width: 640px) {
  .flex-wrap { gap: 0.5rem; }
}
</style>
