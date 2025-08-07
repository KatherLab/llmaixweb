<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50">
      <!-- Modal backdrop: disables background scrolling and closes on click -->
      <div
        class="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        @click="onClose"
      ></div>

      <!-- Modal content: scrollable, but fits on screen -->
      <div
        class="absolute inset-0 flex items-center justify-center px-2 py-6 pointer-events-none"
        style="z-index: 60;"
      >
        <div
          class="relative bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[96vh] flex flex-col pointer-events-auto"
          @click.stop
          ref="modalRef"
        >
          <!-- Header -->
          <div class="flex items-center justify-between p-6 border-b rounded-t-xl">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">
                Preprocessing Task #{{ task.id }}
              </h3>
              <p class="mt-1 text-sm text-gray-500">
                Created {{ formatDateTime(task.created_at) }}
              </p>
            </div>
            <button
              aria-label="Close"
              class="text-gray-400 hover:text-gray-500"
              @click="onClose"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
            </button>
          </div>

          <!-- Progress (Live) -->
          <div
            v-if="isActive"
            class="px-6 pt-4 pb-2 bg-blue-50 border-b flex flex-col gap-1"
          >
            <div class="flex items-center justify-between text-xs text-blue-900 mb-1">
              <span>Progress</span>
              <span v-if="task.meta?.eta_seconds > 0">≈ {{ prettyEta(task.meta.eta_seconds) }} left</span>
              <span v-else>Finishing…</span>
            </div>
            <div class="w-full bg-blue-200/40 rounded-full h-2 overflow-hidden">
              <div
                class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                :style="{ width: `${progress * 100}%` }"
              />
            </div>
            <div class="mt-1 flex items-center gap-4 text-xs text-blue-800">
              <span>{{ actualProcessed }} of {{ total }} processed</span>
              <span v-if="failed > 0" class="text-red-600">• {{ failed }} failed</span>
              <span v-if="cancelled > 0" class="text-yellow-600">• {{ cancelled }} cancelled</span>
            </div>
          </div>

          <!-- Modal body: scrollable -->
          <div class="flex-1 min-h-0 overflow-y-auto px-6 py-6 space-y-8">
            <!-- Summary Stats -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div class="bg-white rounded-lg p-4 flex flex-col items-center">
                <div class="text-2xl font-bold text-gray-900">{{ total }}</div>
                <div class="text-sm text-gray-500">Total Files</div>
              </div>
              <div class="bg-white rounded-lg p-4 flex flex-col items-center">
                <div class="text-2xl font-bold text-green-600">{{ completed }}</div>
                <div class="text-sm text-gray-500">Succeeded</div>
              </div>
              <div class="bg-white rounded-lg p-4 flex flex-col items-center">
                <div class="text-2xl font-bold text-red-600">{{ failed }}</div>
                <div class="text-sm text-gray-500">Failed</div>
              </div>
              <div class="bg-white rounded-lg p-4 flex flex-col items-center">
                <div class="text-2xl font-bold text-yellow-600">{{ cancelled }}</div>
                <div class="text-sm text-gray-500">Cancelled</div>
              </div>
            </div>

            <!-- Configuration Details + Message -->
            <div>
              <h4 class="text-base font-semibold text-gray-900 mb-2">Configuration</h4>
              <div class="bg-gray-50 rounded-lg p-4 mb-3">
                <dl class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt class="text-gray-500">Configuration Name</dt>
                    <dd class="font-medium text-gray-900">
                      {{ task.configuration?.name || 'Custom Configuration' }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">PDF Backend</dt>
                    <dd class="font-medium text-gray-900">
                      {{ task.configuration?.pdf_backend || 'Default' }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">OCR Enabled</dt>
                    <dd class="font-medium text-gray-900">
                      {{ task.configuration?.use_ocr ? 'Yes' : 'No' }}
                    </dd>
                  </div>
                  <div v-if="task.configuration?.use_ocr">
                    <dt class="text-gray-500">OCR Languages</dt>
                    <dd class="font-medium text-gray-900">
                      {{ task.configuration?.ocr_languages?.join(', ') || 'Default' }}
                    </dd>
                  </div>
                </dl>
                <div class="mt-4 pt-4 border-t border-gray-200">
                  <h5 class="text-sm font-medium text-gray-900 mb-2">Message</h5>
                  <p class="text-sm text-gray-800 leading-6 whitespace-pre-wrap">
                    {{ task.message || 'No message available.' }}
                  </p>
                </div>
              </div>
            </div>

            <!-- File Tasks List -->
            <div>
              <h4 class="text-base font-semibold text-gray-900 mb-3">File Processing Details</h4>
              <div v-if="fileTasks.length > 0">
                <div
                  v-for="fileTask in fileTasks"
                  :key="fileTask.id"
                  class="border rounded-lg p-3 flex items-center justify-between mb-2"
                >
                  <div class="flex items-center gap-3">
                    <div
                      :class="[
                        'h-8 w-8 rounded-full flex items-center justify-center',
                        fileTask.status === 'completed' ? 'bg-green-100' :
                        fileTask.status === 'failed' ? 'bg-red-100' :
                        fileTask.status === 'cancelled' ? 'bg-yellow-100' : 'bg-gray-100'
                      ]"
                    >
                      <svg v-if="fileTask.status === 'completed'" class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                      </svg>
                      <svg v-else-if="fileTask.status === 'failed'" class="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                      </svg>
                      <svg v-else-if="fileTask.status === 'cancelled'" class="h-5 w-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                        <path d="M12 9v2m0 4h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                      </svg>
                      <svg v-else class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                      </svg>
                    </div>
                    <div>
                      <p class="text-sm font-medium text-gray-900">{{ fileTask.file_name }}</p>
                      <p class="text-xs text-gray-500">
                        <span v-if="fileTask.status === 'completed' && fileTask.processing_time">Processed in {{ fileTask.processing_time }}s</span>
                        <span v-else-if="fileTask.status === 'failed' && fileTask.processing_time">Failed after {{ fileTask.processing_time }}s</span>
                        <span v-else-if="fileTask.status === 'cancelled'">Cancelled</span>
                        <span v-else>Pending</span>
                      </p>
                    </div>
                  </div>
                  <div v-if="fileTask.error_message" class="ml-4 max-w-xs group relative">
                    <p
                      :title="fileTask.error_message"
                      class="text-xs text-red-600 truncate cursor-pointer group-hover:underline"
                    >
                      {{
                        fileTask.error_message.length > 64
                          ? fileTask.error_message.slice(0, 64) + '…'
                          : fileTask.error_message
                      }}
                    </p>
                  </div>
                </div>
              </div>
              <div v-else class="text-center text-gray-400 py-6">
                No file-tasks recorded.
              </div>
            </div>
          </div>

          <!-- Footer Actions -->
          <div class="p-6 border-t bg-gray-50 rounded-b-xl flex justify-end gap-2">
            <button
              v-if="failed > 0"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              @click="$emit('retry-failed', task.id)"
            >
              Retry Failed Files
            </button>
            <button
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              @click="onClose"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
});
const emit = defineEmits(['close', 'retry-failed']);

const modalRef = ref(null);

// Lock background scroll when modal is open
onMounted(() => {
  document.body.classList.add('overflow-hidden');
});
onUnmounted(() => {
  document.body.classList.remove('overflow-hidden');
});

// Helper: close
function onClose() {
  emit('close');
}

// Status/completion breakdown
const total = computed(() => props.task.meta?.total_files || props.task.total_files || 0);
const completed = computed(() => props.task.meta?.completed_files || props.task.processed_files || 0);
const failed = computed(() => props.task.meta?.failed_files || props.task.failed_files || 0);
const cancelled = computed(() => props.task.meta?.cancelled_files || props.task.skipped_files || 0);

const fileTasks = computed(() =>
  Array.isArray(props.task.file_tasks) ? props.task.file_tasks : []
);
const actualProcessed = computed(() => completed.value + failed.value + cancelled.value);

const progress = computed(() => {
  if (!total.value) return 0;
  return Math.min(actualProcessed.value / total.value, 1.0);
});

// Is the task running?
const isActive = computed(() =>
  ['pending', 'processing', 'in_progress'].includes(props.task.status)
);

function prettyEta(sec) {
  if (!sec || isNaN(sec)) return "00:00:00";
  return new Date(sec * 1000).toISOString().substring(11, 19);
}

function formatDateTime(dateString) {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString();
}
</script>

<style scoped>
/* Prevent background scroll when modal is open */
html, body {
  overscroll-behavior: none;
}

/* Ensure scroll only inside modal body */
.flex-1 {
  min-height: 0;
  /* Needed for flexbox scrolling */
}
</style>
