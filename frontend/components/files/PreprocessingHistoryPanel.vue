<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 overflow-hidden bg-black/30 backdrop-blur-md transition-opacity"
      @click="emit('close')"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0"></div>

      <!-- Panel -->
      <div class="absolute inset-0 flex justify-end">
        <div class="w-screen max-w-md panel-slide-enter">
          <div class="h-full flex flex-col bg-white shadow-xl" @click.stop>
            <!-- Panel Header -->
            <div
              class="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50"
            >
              <div class="min-w-0">
                <h3 class="text-lg font-semibold text-gray-900">Preprocessing History</h3>
                <p v-if="historyFile" class="text-sm text-gray-500 truncate mt-0.5">
                  {{ historyFile.file_name }}
                </p>
              </div>
              <button
                class="text-gray-400 hover:text-gray-600 transition-colors"
                @click="emit('close')"
              >
                <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <!-- Panel Content -->
            <div class="flex-1 overflow-y-auto p-6">
              <!-- Preprocessing Runs (Accordion) -->
              <div v-if="historyFile?.preprocessing_tasks?.length" class="space-y-3">
                <div
                  v-for="task in historyFile.preprocessing_tasks"
                  :key="task.id"
                  :class="[
                    'bg-white rounded-lg border transition-all overflow-hidden',
                    expandedTasks.has(task.id)
                      ? 'border-blue-300 shadow-md'
                      : 'border-gray-200 hover:border-blue-300',
                  ]"
                >
                  <!-- Accordion Header (clickable) -->
                  <div
                    class="px-4 py-3 cursor-pointer flex items-center justify-between bg-gradient-to-r from-gray-50 to-white"
                    @click="toggleTaskAccordion(task.id)"
                  >
                    <div class="flex items-center gap-3 flex-1 min-w-0">
                      <!-- Status indicator -->
                      <span
                        :class="[
                          'w-2.5 h-2.5 rounded-full flex-shrink-0',
                          isTaskStatus(task, 'completed')
                            ? 'bg-green-500'
                            : isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')
                              ? 'bg-blue-500 animate-pulse'
                              : isTaskStatus(task, 'failed')
                                ? 'bg-red-500'
                                : isTaskStatus(task, 'cancelled')
                                  ? 'bg-yellow-500'
                                  : 'bg-gray-400',
                        ]"
                      />
                      <!-- Task info -->
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                          <p class="text-sm font-medium text-gray-900 truncate">
                            Run #{{ task.id }} • {{ getEngineName(task) }}
                          </p>
                          <!-- Expand/collapse chevron -->
                          <svg
                            :class="[
                              'w-4 h-4 text-gray-400 transition-transform flex-shrink-0',
                              expandedTasks.has(task.id) ? 'rotate-90' : '',
                            ]"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </div>
                        <p class="text-xs text-gray-500 mt-0.5 truncate">
                          {{ formatRelativeTime(task.created_at) }}
                          <span v-if="task.completed_at">
                            • {{ formatRelativeTime(task.completed_at) }}
                          </span>
                        </p>
                      </div>
                    </div>
                    <!-- Mini status badge -->
                    <span
                      :class="[
                        'inline-flex items-center px-2 py-1 rounded text-xs font-medium flex-shrink-0 ml-2',
                        isTaskStatus(task, 'completed')
                          ? 'bg-green-100 text-green-700'
                          : isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')
                            ? 'bg-blue-100 text-blue-700'
                            : isTaskStatus(task, 'failed')
                              ? 'bg-red-100 text-red-700'
                              : isTaskStatus(task, 'cancelled')
                                ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-gray-100 text-gray-700',
                      ]"
                    >
                      {{
                        isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')
                          ? `${Math.round(task.meta?.progress || 0)}%`
                          : isTaskStatus(task, 'completed')
                            ? 'Done'
                            : isTaskStatus(task, 'failed')
                              ? 'Failed'
                              : isTaskStatus(task, 'cancelled')
                                ? 'Cancelled'
                                : 'Pending'
                      }}
                    </span>
                  </div>

                  <!-- Accordion Content (expanded) -->
                  <div
                    v-show="expandedTasks.has(task.id)"
                    class="border-t border-gray-200 bg-gray-50 px-4 py-3 space-y-3"
                  >
                    <!-- Progress bar for active tasks -->
                    <div
                      v-if="isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')"
                      class="space-y-1"
                    >
                      <div class="flex items-center justify-between text-xs text-gray-600">
                        <span>Processing...</span>
                        <span v-if="task.meta?.eta_seconds > 0" class="text-gray-500">
                          ≈ {{ formatDuration(task.meta.eta_seconds) }} left
                        </span>
                      </div>
                      <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div
                          :style="{
                            width: `${Math.min((task.processed_files / task.total_files) * 100, 100)}%`,
                          }"
                          class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        />
                      </div>
                      <p class="text-xs text-gray-500">
                        {{ task.processed_files }} of {{ task.total_files }} files processed
                        <span v-if="task.failed_files > 0" class="text-red-600">
                          • {{ task.failed_files }} failed
                        </span>
                      </p>
                    </div>

                    <!-- File task details -->
                    <div class="space-y-2">
                      <template v-if="task.file_tasks && task.file_tasks.length > 0">
                        <div
                          v-for="fileTask in task.file_tasks"
                          :key="fileTask.id"
                          :class="[
                            'rounded-md border p-2 text-sm',
                            fileTask.status === 'completed'
                              ? 'bg-green-50 border-green-200'
                              : fileTask.status === 'failed'
                                ? 'bg-red-50 border-red-200'
                                : fileTask.status === 'cancelled'
                                  ? 'bg-yellow-50 border-yellow-200'
                                  : 'bg-gray-50 border-gray-200',
                          ]"
                        >
                          <!-- File task header -->
                          <div class="flex items-start justify-between gap-2">
                            <div class="flex items-center gap-2 flex-1 min-w-0">
                              <!-- Status icon -->
                              <svg
                                v-if="fileTask.status === 'completed'"
                                class="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M5 13l4 4L19 7"
                                />
                              </svg>
                              <svg
                                v-else-if="fileTask.status === 'failed'"
                                class="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M6 18L18 6M6 6l12 12"
                                />
                              </svg>
                              <svg
                                v-else-if="fileTask.status === 'cancelled'"
                                class="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <circle
                                  cx="12"
                                  cy="12"
                                  r="10"
                                  stroke="currentColor"
                                  stroke-width="2"
                                />
                                <path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M12 9v2m0 4h.01"
                                />
                              </svg>
                              <svg
                                v-else
                                class="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                              </svg>
                              <span class="font-medium text-gray-900 truncate">
                                {{ fileTask.file_name || 'Unknown file' }}
                              </span>
                            </div>
                            <!-- Processing time -->
                            <span
                              v-if="fileTask.processing_time"
                              class="text-xs text-gray-500 whitespace-nowrap"
                            >
                              {{ formatProcessingTime(fileTask.processing_time) }}
                            </span>
                          </div>

                          <!-- Error message (nested accordion) -->
                          <div
                            v-if="fileTask.status === 'failed' && fileTask.error_message"
                            class="mt-2"
                          >
                            <details class="group">
                              <summary
                                class="text-xs text-red-700 cursor-pointer hover:text-red-900 flex items-center gap-1"
                              >
                                <svg
                                  class="w-3 h-3 transition-transform group-open:rotate-90"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M9 5l7 7-7 7"
                                  />
                                </svg>
                                View error
                              </summary>
                              <p class="mt-1 text-xs text-red-600 bg-red-100 rounded p-2">
                                {{ fileTask.error_message }}
                              </p>
                            </details>
                          </div>

                          <!-- Warnings (nested accordion for skipped rows) -->
                          <div
                            v-if="
                              fileTask.warnings &&
                              (fileTask.warnings.messages || fileTask.warnings.skipped_rows)
                            "
                            class="mt-2"
                          >
                            <details class="group">
                              <summary
                                class="text-xs text-amber-700 cursor-pointer hover:text-amber-900 flex items-center gap-1"
                              >
                                <svg
                                  class="w-3 h-3 transition-transform group-open:rotate-90"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M9 5l7 7-7 7"
                                  />
                                </svg>
                                ⚠ {{ fileTask.warnings.skipped_rows?.count || 0 }} skipped rows
                              </summary>
                              <div
                                class="mt-1 text-xs text-amber-600 bg-amber-100 rounded p-2 max-h-32 overflow-y-auto"
                              >
                                <div
                                  v-if="fileTask.warnings.skipped_rows?.details"
                                  class="space-y-1"
                                >
                                  <div
                                    v-for="(
                                      row, idx
                                    ) in fileTask.warnings.skipped_rows.details.slice(0, 10)"
                                    :key="idx"
                                    class="flex justify-between"
                                  >
                                    <span>Row {{ row.row_index }}</span>
                                    <span class="truncate max-w-[150px]">{{ row.reason }}</span>
                                  </div>
                                  <p
                                    v-if="fileTask.warnings.skipped_rows.details.length > 10"
                                    class="text-amber-500"
                                  >
                                    ...and
                                    {{ fileTask.warnings.skipped_rows.details.length - 10 }} more
                                  </p>
                                </div>
                                <div v-else>
                                  <p v-for="(msg, idx) in fileTask.warnings.messages" :key="idx">
                                    {{ msg }}
                                  </p>
                                </div>
                              </div>
                            </details>
                          </div>

                          <!-- Document link for completed tasks -->
                          <div
                            v-if="
                              fileTask.status === 'completed' &&
                              fileTask.document_ids &&
                              fileTask.document_ids.length > 0
                            "
                            class="mt-2 flex items-center justify-between"
                          >
                            <span class="text-xs text-green-700">
                              ✓ {{ fileTask.document_ids.length }} document{{
                                fileTask.document_ids.length !== 1 ? 's' : ''
                              }}
                            </span>
                            <button
                              v-if="fileTask.document_ids.length === 1"
                              class="text-xs text-blue-600 hover:text-blue-800 font-medium underline flex items-center gap-1"
                              @click.stop="emit('navigate', fileTask.document_ids[0])"
                            >
                              <svg
                                class="w-3 h-3"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                />
                              </svg>
                              Go to Document
                            </button>
                            <button
                              v-else
                              class="text-xs text-blue-600 hover:text-blue-800 font-medium underline flex items-center gap-1"
                              @click.stop="emit('navigate', fileTask.document_ids[0])"
                            >
                              <svg
                                class="w-3 h-3"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  stroke-linecap="round"
                                  stroke-linejoin="round"
                                  stroke-width="2"
                                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                />
                              </svg>
                              Go to Documents ({{ fileTask.document_ids.length }})
                            </button>
                          </div>
                        </div>
                      </template>
                      <div v-else class="text-center text-gray-400 py-4 text-sm">
                        No file tasks recorded
                      </div>
                    </div>

                    <!-- Task-level error message -->
                    <div
                      v-if="task.message && isTaskStatus(task, 'failed')"
                      class="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700"
                    >
                      {{ task.message }}
                    </div>

                    <!-- Actions -->
                    <div class="flex items-center justify-end gap-2 pt-2 border-t border-gray-200">
                      <button
                        v-if="isTaskStatus(task, 'failed')"
                        class="text-xs text-blue-600 hover:text-blue-800 font-medium"
                        @click.stop="emit('retry', task.id)"
                      >
                        Retry failed files
                      </button>
                      <button
                        v-if="
                          isTaskStatus(task, 'processing') ||
                          isTaskStatus(task, 'pending') ||
                          isTaskStatus(task, 'in_progress')
                        "
                        class="text-xs text-red-600 hover:text-red-800 font-medium flex items-center gap-1"
                        @click.stop="emit('cancel', task)"
                      >
                        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                        Cancel
                      </button>
                      <button
                        class="text-xs text-gray-600 hover:text-gray-800"
                        @click.stop="toggleTaskAccordion(task.id)"
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- No Runs Yet -->
              <div v-else class="text-center py-12">
                <svg
                  class="mx-auto h-12 w-12 text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p class="mt-4 text-sm text-gray-500">No preprocessing runs yet</p>
                <button
                  v-if="historyFile"
                  class="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                  @click="emit('process', historyFile)"
                >
                  🚀 Process this file
                </button>
              </div>
            </div>

            <!-- Panel Footer -->
            <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
              <div class="flex items-center justify-between">
                <button
                  v-if="historyFile"
                  class="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  @click="emit('process-panel', historyFile)"
                >
                  + Run new preprocessing
                </button>
                <button
                  class="ml-auto px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                  @click="emit('close')"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { formatDuration } from '@/utils/formatters'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  open: { type: Boolean, required: true },
  historyFile: { type: Object, default: null },
  // Task id to auto-expand when the panel opens (used by ActivityBell "expand task" events).
  highlightTaskId: { type: [String, Number], default: null },
})

const emit = defineEmits(['close', 'navigate', 'retry', 'cancel', 'process', 'process-panel'])

// Ref-counted scroll lock — unlocks only when no panel/modal holds the lock.
useScrollLock({ watch: () => props.open })

// Multi-expand accordion state
const expandedTasks = ref(new Set())

const toggleTaskAccordion = (taskId) => {
  if (expandedTasks.value.has(taskId)) {
    expandedTasks.value.delete(taskId)
  } else {
    expandedTasks.value.add(taskId)
  }
}

// Auto-expand a task when requested (e.g. from ActivityBell).
watch(
  () => props.highlightTaskId,
  (taskId) => {
    if (taskId !== null && taskId !== undefined) {
      expandedTasks.value.add(Number(taskId))
    }
  },
  { immediate: true },
)

// Get engine name from task
const getEngineName = (task) => {
  const settings = task.configuration?.additional_settings || {}
  const engine = settings.ocr_engine || 'local'

  if (engine === 'mistral_ocr') return 'Mistral OCR'
  if (engine === 'llm_vision') return 'Vision LLM'
  if (settings.force_ocr) return 'Local OCR + Force'
  return 'Local OCR'
}

// Helper to check task status (handles enum or string)
const isTaskStatus = (task, expectedStatus) => {
  if (!task || !task.status) return false
  return String(task.status).toLowerCase() === String(expectedStatus).toLowerCase()
}

// Format relative time
const formatRelativeTime = (dateString) => {
  if (!dateString) return ''
  const diff = new Date() - new Date(dateString)
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return new Date(dateString).toLocaleDateString()
}

// Format processing time in seconds to human readable
const formatProcessingTime = (seconds) => {
  if (!seconds && seconds !== 0) return ''
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}
</script>

<style scoped>
/* Panel slide-in animation */
.panel-slide-enter {
  transform: translateX(100%);
  animation: slideIn 0.3s ease-in-out forwards;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}
</style>
