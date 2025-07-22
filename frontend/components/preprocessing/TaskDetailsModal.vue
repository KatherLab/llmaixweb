<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 overflow-hidden">
      <!-- Semi-transparent backdrop with blur -->
      <div
        class="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        @click="$emit('close')"
      ></div>

      <!-- Modal content -->
      <div class="absolute inset-4 md:inset-8 bg-white rounded-lg shadow-2xl flex flex-col max-w-4xl mx-auto">
        <!-- Header -->
        <div class="flex items-center justify-between p-6 border-b rounded-t-lg">
          <div>
            <h3 class="text-lg font-semibold text-gray-900">
              Preprocessing Task #{{ task.id }}
            </h3>
            <p class="mt-1 text-sm text-gray-500">
              Created {{ formatDateTime(task.created_at) }}
            </p>
          </div>
          <div class="flex items-center space-x-3">
            <span
              :class="[
                'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium',
                getStatusClass(task.status)
              ]"
            >
              {{ task.status }}
            </span>
            <button
              @click="$emit('close')"
              class="text-gray-400 hover:text-gray-500"
              aria-label="Close"
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <!-- Content -->
        <div class="flex-1 overflow-y-auto">
          <!-- Summary Stats -->
          <div class="p-6 bg-gray-50 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-white rounded-lg p-4 flex flex-col items-center">
              <div class="text-2xl font-bold text-gray-900">{{ task.total_files }}</div>
              <div class="text-sm text-gray-500">Total Files</div>
            </div>
            <div class="bg-white rounded-lg p-4 flex flex-col items-center">
              <div class="text-2xl font-bold text-green-600">{{ successCount }}</div>
              <div class="text-sm text-gray-500">Succeeded</div>
            </div>
            <div class="bg-white rounded-lg p-4 flex flex-col items-center">
              <div class="text-2xl font-bold text-red-600">{{ failedCount }}</div>
              <div class="text-sm text-gray-500">Failed</div>
            </div>
            <div class="bg-white rounded-lg p-4 flex flex-col items-center">
              <div class="text-2xl font-bold text-yellow-600">{{ skippedCount }}</div>
              <div class="text-sm text-gray-500">Skipped</div>
            </div>
          </div>
          <!-- Configuration Details -->
          <div class="p-6 border-b">
            <h4 class="font-medium text-gray-900 mb-3">Configuration</h4>
            <div class="bg-gray-50 rounded-lg p-4">
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
            </div>
          </div>
          <!-- File Tasks List -->
          <div class="p-6">
            <div class="flex items-center justify-between mb-4">
              <h4 class="font-medium text-gray-900">File Processing Details</h4>
              <div class="flex items-center space-x-2">
                <button
                  @click="filterStatus = 'all'"
                  :class="[
                    'px-3 py-1 text-sm rounded-md',
                    filterStatus === 'all' ? 'bg-gray-200 text-gray-900' : 'text-gray-600 hover:text-gray-900'
                  ]"
                >
                  All
                </button>
                <button
                  @click="filterStatus = 'completed'"
                  :class="[
                    'px-3 py-1 text-sm rounded-md',
                    filterStatus === 'completed' ? 'bg-green-100 text-green-800' : 'text-gray-600 hover:text-gray-900'
                  ]"
                >
                  Completed
                </button>
                <button
                  @click="filterStatus = 'failed'"
                  :class="[
                    'px-3 py-1 text-sm rounded-md',
                    filterStatus === 'failed' ? 'bg-red-100 text-red-800' : 'text-gray-600 hover:text-gray-900'
                  ]"
                >
                  Failed
                </button>
                <button
                  @click="filterStatus = 'skipped'"
                  :class="[
                    'px-3 py-1 text-sm rounded-md',
                    filterStatus === 'skipped' ? 'bg-yellow-100 text-yellow-800' : 'text-gray-600 hover:text-gray-900'
                  ]"
                >
                  Skipped
                </button>
              </div>
            </div>
            <div class="space-y-2">
              <div
                v-for="fileTask in filteredFileTasks"
                :key="fileTask.id"
                class="border rounded-lg p-3 hover:bg-gray-50 flex items-center justify-between"
              >
                <div class="flex items-center space-x-3">
                  <div
                    :class="[
                      'h-8 w-8 rounded-full flex items-center justify-center',
                      fileTask.status === 'completed' ? 'bg-green-100' :
                      fileTask.status === 'failed' ? 'bg-red-100' :
                      fileTask.status === 'skipped' ? 'bg-yellow-100' :
                      'bg-gray-100'
                    ]"
                  >
                    <svg
                      v-if="fileTask.status === 'completed'"
                      class="h-5 w-5 text-green-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <svg
                      v-else-if="fileTask.status === 'failed'"
                      class="h-5 w-5 text-red-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    <svg
                      v-else-if="fileTask.status === 'skipped'"
                      class="h-5 w-5 text-yellow-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="#fef3c7"/>
                      <path stroke="#f59e42" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01" />
                    </svg>
                    <svg
                      v-else
                      class="h-5 w-5 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-gray-900">
                      {{ fileTask.file_name }}
                    </p>
                    <p class="text-xs text-gray-500">
                      <span v-if="fileTask.status === 'completed' && fileTask.processing_time">Processed in {{ fileTask.processing_time }}s</span>
                      <span v-else-if="fileTask.status === 'failed' && fileTask.processing_time">Failed after {{ fileTask.processing_time }}s</span>
                      <span v-else-if="fileTask.status === 'skipped'">Skipped (already processed)</span>
                      <span v-else>Pending</span>
                    </p>
                  </div>
                </div>
                <div v-if="fileTask.error_message" class="ml-4 max-w-xs truncate">
                  <p class="text-xs text-red-600 truncate" :title="fileTask.error_message">
                    {{ fileTask.error_message.length > 64 ? fileTask.error_message.slice(0, 64) + '…' : fileTask.error_message }}
                  </p>
                </div>
              </div>
              <div v-if="filteredFileTasks.length === 0" class="text-center text-gray-400 py-6">
                No files for this filter.
              </div>
            </div>
          </div>
        </div>
        <!-- Footer Actions -->
        <div class="p-6 border-t bg-gray-50 rounded-b-lg">
          <div class="flex justify-between items-center">
            <div v-if="failedCount > 0" class="text-sm text-gray-600">
              {{ failedCount }} file{{ failedCount !== 1 ? 's' : '' }} failed to process
            </div>
            <div v-else-if="skippedCount > 0" class="text-sm text-gray-600">
              {{ skippedCount }} file{{ skippedCount !== 1 ? 's' : '' }} skipped (already processed)
            </div>
            <div v-else></div>
            <div class="flex items-center space-x-3">
              <button
                v-if="task.status === 'processing'"
                @click="cancelTask"
                class="px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-lg hover:bg-red-50"
              >
                Cancel Task
              </button>
              <button
                v-if="failedCount > 0"
                @click="$emit('retry-failed', task.id)"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                Retry Failed Files
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
});
const emit = defineEmits(['close', 'retry-failed']);
const toast = useToast();
const filterStatus = ref('all');

// Defensive: support both "file_tasks" (array of file results) or legacy demo code
const fileTasks = computed(() => {
  if (props.task.file_tasks && Array.isArray(props.task.file_tasks)) {
    return props.task.file_tasks;
  }
  // fallback: mock demo data (if you want to demo without backend)
  if (props.task.demo) {
    return [
      { id: 1, file_name: 'document1.pdf', status: 'completed', processing_time: 2.5 },
      { id: 2, file_name: 'document2.pdf', status: 'failed', error_message: 'OCR failed: Unable to process image' },
      { id: 3, file_name: 'document3.pdf', status: 'skipped' },
    ];
  }
  // fallback: empty
  return [];
});

const filteredFileTasks = computed(() => {
  if (filterStatus.value === 'all') return fileTasks.value;
  return fileTasks.value.filter(task => task.status === filterStatus.value);
});

const getStatusClass = (status) => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'processing':
      return 'bg-blue-100 text-blue-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    case 'skipped':
      return 'bg-yellow-100 text-yellow-800';
    case 'cancelled':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-yellow-100 text-yellow-800';
  }
};

const formatDateTime = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString();
};

const cancelTask = async () => {
  // This should call your real cancel endpoint if you have one.
  toast.info('Task cancellation would be implemented here');
};

// Calculate counts from fileTasks:
const successCount = computed(() => fileTasks.value.filter(t => t.status === 'completed').length);
const failedCount = computed(() => fileTasks.value.filter(t => t.status === 'failed').length);
const skippedCount = computed(() => fileTasks.value.filter(t => t.status === 'skipped').length);
</script>
