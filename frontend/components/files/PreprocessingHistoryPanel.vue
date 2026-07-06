<template>
  <BaseModal
    :open="open"
    placement="right"
    panel-class="w-screen max-w-md"
    header-class="bg-surface-muted"
    body-class="p-6"
    @close="emit('close')"
  >
    <template #header>
      <div class="min-w-0">
        <h3 class="text-lg font-semibold text-content">Preprocessing History</h3>
        <p v-if="historyFile" class="text-sm text-content-muted truncate mt-0.5">
          {{ historyFile.file_name }}
        </p>
      </div>
    </template>

    <!-- Panel Content -->
    <div>
      <!-- Preprocessing Runs (Accordion) -->
      <div v-if="historyFile?.preprocessing_tasks?.length" class="space-y-3">
        <div
          v-for="task in historyFile.preprocessing_tasks"
          :key="task.id"
          :class="[
            'bg-surface rounded-card border transition-all overflow-hidden',
            expandedTasks.has(task.id)
              ? 'border-primary shadow-md'
              : 'border-default hover:border-primary',
          ]"
        >
          <!-- Accordion Header (clickable) -->
          <div
            class="px-4 py-3 cursor-pointer flex items-center justify-between bg-surface-muted"
            @click="toggleTaskAccordion(task.id)"
          >
            <div class="flex items-center gap-3 flex-1 min-w-0">
              <!-- Status indicator -->
              <span
                :class="[
                  'w-2.5 h-2.5 rounded-full flex-shrink-0',
                  getStatusDotClass(task.status),
                  isTaskActive(task) ? 'animate-pulse' : '',
                ]"
              />
              <!-- Task info -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <p class="text-sm font-medium text-content truncate">
                    Run #{{ task.id }} • {{ getEngineName(task) }}
                  </p>
                  <!-- Expand/collapse chevron -->
                  <ChevronRight
                    :class="[
                      'w-4 h-4 text-content-subtle transition-transform flex-shrink-0',
                      expandedTasks.has(task.id) ? 'rotate-90' : '',
                    ]"
                  />
                </div>
                <p class="text-xs text-content-muted mt-0.5 truncate">
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
                'inline-flex items-center px-2 py-1 rounded-card text-xs font-medium flex-shrink-0 ml-2',
                getStatusBadgeClass(task.status),
              ]"
            >
              {{ taskStatusLabel(task) }}
            </span>
          </div>

          <!-- Accordion Content (expanded) -->
          <div
            v-show="expandedTasks.has(task.id)"
            class="border-t border-default bg-surface-muted px-4 py-3 space-y-3"
          >
            <!-- Progress bar for active tasks -->
            <div
              v-if="isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')"
              class="space-y-1"
            >
              <div class="flex items-center justify-between text-xs text-content-muted">
                <span>Processing...</span>
                <span v-if="(task.meta?.eta_seconds ?? 0) > 0" class="text-content-muted">
                  ≈ {{ formatDuration(task.meta?.eta_seconds) }} left
                </span>
              </div>
              <div class="w-full bg-surface-sunken rounded-full h-2 overflow-hidden">
                <div
                  :style="{
                    width: `${Math.min((task.processed_files / task.total_files) * 100, 100)}%`,
                  }"
                  class="bg-primary h-2 rounded-full transition-all duration-300"
                />
              </div>
              <p class="text-xs text-content-muted">
                {{ task.processed_files }} of {{ task.total_files }} files processed
                <span v-if="task.failed_files > 0" class="text-red-600 dark:text-red-400">
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
                    'rounded-card border p-2 text-sm',
                    getStatusBannerClass(fileTask.status),
                  ]"
                >
                  <!-- File task header -->
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex items-center gap-2 flex-1 min-w-0">
                      <!-- Status icon -->
                      <Check
                        v-if="fileTask.status === 'completed'"
                        class="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5"
                      />
                      <X
                        v-else-if="fileTask.status === 'failed'"
                        class="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5"
                      />
                      <Ban
                        v-else-if="fileTask.status === 'cancelled'"
                        class="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5"
                      />
                      <Clock v-else class="w-4 h-4 text-content-subtle flex-shrink-0 mt-0.5" />
                      <span class="font-medium text-content truncate">
                        {{ fileTask.file_name || 'Unknown file' }}
                      </span>
                    </div>
                    <!-- Processing time -->
                    <span
                      v-if="fileTask.processing_time"
                      class="text-xs text-content-muted whitespace-nowrap"
                    >
                      {{ formatProcessingTime(fileTask.processing_time) }}
                    </span>
                  </div>

                  <!-- Error message (nested accordion) -->
                  <div v-if="fileTask.status === 'failed' && fileTask.error_message" class="mt-2">
                    <details class="group">
                      <summary
                        class="text-xs text-red-700 dark:text-red-400 cursor-pointer hover:text-red-900 dark:hover:text-red-300 flex items-center gap-1"
                      >
                        <ChevronRight class="w-3 h-3 transition-transform group-open:rotate-90" />
                        View error
                      </summary>
                      <p
                        class="mt-1 text-xs text-red-600 dark:text-red-300 dark:bg-red-900/30 bg-red-100 rounded p-2"
                      >
                        {{ fileTask.error_message }}
                      </p>
                    </details>
                  </div>

                  <!-- Warnings (nested accordion for skipped rows) -->
                  <div
                    v-if="
                      getWarnings(fileTask) &&
                      (getWarnings(fileTask)?.messages || getWarnings(fileTask)?.skipped_rows)
                    "
                    class="mt-2"
                  >
                    <details class="group">
                      <summary
                        class="text-xs text-amber-700 dark:text-amber-400 cursor-pointer hover:text-amber-900 dark:hover:text-amber-300 flex items-center gap-1"
                      >
                        <ChevronRight class="w-3 h-3 transition-transform group-open:rotate-90" />
                        <AlertTriangle class="w-3 h-3 inline" />
                        {{ getWarnings(fileTask)?.skipped_rows?.count || 0 }} skipped rows
                      </summary>
                      <div
                        class="mt-1 text-xs text-amber-600 dark:text-amber-300 dark:bg-amber-900/30 bg-amber-100 rounded p-2 max-h-32 overflow-y-auto"
                      >
                        <div v-if="getWarnings(fileTask)?.skipped_rows?.details" class="space-y-1">
                          <div
                            v-for="(row, idx) in getWarnings(
                              fileTask,
                            )?.skipped_rows?.details?.slice(0, 10)"
                            :key="idx"
                            class="flex justify-between"
                          >
                            <span>Row {{ row.row_index }}</span>
                            <span class="truncate max-w-[150px]">{{ row.reason }}</span>
                          </div>
                          <p
                            v-if="(getWarnings(fileTask)?.skipped_rows?.details?.length ?? 0) > 10"
                            class="text-amber-500 dark:text-amber-400"
                          >
                            ...and
                            {{ (getWarnings(fileTask)?.skipped_rows?.details?.length ?? 0) - 10 }}
                            more
                          </p>
                        </div>
                        <div v-else>
                          <p v-for="(msg, idx) in getWarnings(fileTask)?.messages" :key="idx">
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
                    <span
                      class="text-xs text-green-700 dark:text-green-400 inline-flex items-center gap-1"
                    >
                      <Check class="w-3 h-3" />
                      {{ fileTask.document_ids.length }} document{{
                        fileTask.document_ids.length !== 1 ? 's' : ''
                      }}
                    </span>
                    <BaseButton
                      v-if="fileTask.document_ids.length === 1"
                      variant="ghost"
                      size="sm"
                      class="text-xs font-medium underline"
                      @click.stop="emit('navigate', fileTask.document_ids[0]!)"
                    >
                      <ExternalLink class="w-3 h-3" />
                      Go to Document
                    </BaseButton>
                    <BaseButton
                      v-else
                      variant="ghost"
                      size="sm"
                      class="text-xs font-medium underline"
                      @click.stop="emit('navigate', fileTask.document_ids[0]!)"
                    >
                      <ExternalLink class="w-3 h-3" />
                      Go to Documents ({{ fileTask.document_ids.length }})
                    </BaseButton>
                  </div>
                </div>
              </template>
              <div v-else class="text-center text-content-subtle py-4 text-sm">
                No file tasks recorded
              </div>
            </div>

            <!-- Task-level error message -->
            <Callout
              v-if="task.message && isTaskStatus(task, 'failed')"
              variant="danger"
              class="text-xs"
            >
              {{ task.message }}
            </Callout>

            <!-- Actions -->
            <div class="flex items-center justify-end gap-2 pt-2 border-t border-default">
              <BaseButton
                v-if="isTaskStatus(task, 'failed')"
                variant="ghost"
                size="sm"
                class="text-xs font-medium"
                @click.stop="emit('retry', task.id)"
              >
                Retry failed files
              </BaseButton>
              <BaseButton
                v-if="
                  isTaskStatus(task, 'processing') ||
                  isTaskStatus(task, 'pending') ||
                  isTaskStatus(task, 'in_progress')
                "
                variant="ghost"
                size="sm"
                class="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium"
                @click.stop="emit('cancel', task)"
              >
                <X class="w-3 h-3" />
                Cancel
              </BaseButton>
              <BaseButton
                variant="ghost"
                size="sm"
                class="text-xs"
                @click.stop="toggleTaskAccordion(task.id)"
              >
                Close
              </BaseButton>
            </div>
          </div>
        </div>
      </div>

      <!-- No Runs Yet -->
      <EmptyState v-else title="No preprocessing runs yet">
        <template #icon>
          <FilePlus class="h-12 w-12 mx-auto text-content-subtle" aria-hidden="true" />
        </template>
        <template v-if="historyFile" #action>
          <BaseButton class="shadow-sm" @click="emit('process', historyFile)">
            <Rocket class="w-4 h-4" />
            Process this file
          </BaseButton>
        </template>
      </EmptyState>
    </div>

    <!-- Panel Footer -->
    <div class="px-6 py-4 border-t border-default bg-surface-muted flex-shrink-0">
      <div class="flex items-center justify-between">
        <BaseButton
          v-if="historyFile"
          variant="ghost"
          size="sm"
          class="font-medium"
          @click="emit('process-panel', historyFile)"
        >
          + Run new preprocessing
        </BaseButton>
        <BaseButton variant="secondary" size="sm" class="ml-auto" @click="emit('close')">
          Close
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  AlertTriangle,
  Ban,
  Check,
  ChevronRight,
  Clock,
  ExternalLink,
  FilePlus,
  Rocket,
  X,
} from '@lucide/vue'
import { formatDuration, formatRelativeTime as sharedFormatRelativeTime } from '@/utils/formatters'
import { getStatusDotClass, getStatusBadgeClass, getStatusBannerClass } from '@/utils/statusStyles'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import Callout from '@/components/common/Callout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { FilePreprocessingTask, PreprocessingTask } from '@/types'
import type { FileWithTasks } from '@/composables/usePreprocessingUpdates'

interface Props {
  open: boolean
  historyFile?: FileWithTasks | null
  // Task id to auto-expand when the panel opens (used by ActivityBell "expand task" events).
  highlightTaskId?: string | number | null
}

const props = withDefaults(defineProps<Props>(), {
  historyFile: null,
  highlightTaskId: null,
})

const emit = defineEmits<{
  close: []
  navigate: [documentId: number]
  retry: [taskId: number]
  cancel: [task: PreprocessingTask]
  process: [file: FileWithTasks]
  'process-panel': [file: FileWithTasks]
}>()

// Multi-expand accordion state
const expandedTasks = ref(new Set<number>())

const toggleTaskAccordion = (taskId: number): void => {
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
const getEngineName = (task: PreprocessingTask): string => {
  const settings = (task.configuration?.additional_settings || {}) as Record<string, unknown>
  const engine = settings.ocr_engine || 'local'

  if (engine === 'mistral_ocr') return 'Mistral OCR'
  if (engine === 'llm_vision') return 'Vision LLM'
  if (settings.force_ocr) return 'Local OCR + Force'
  return 'Local OCR'
}

// Helper to check task status (handles enum or string)
const isTaskStatus = (task: PreprocessingTask | null, expectedStatus: string): boolean => {
  if (!task || !task.status) return false
  return String(task.status).toLowerCase() === String(expectedStatus).toLowerCase()
}

// Whether a task is actively running (processing / in_progress). Used to pulse
// the status dot and show the progress % in the mini badge.
const isTaskActive = (task: PreprocessingTask): boolean =>
  isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')

// Mini badge label for a task's current status.
const taskStatusLabel = (task: PreprocessingTask): string => {
  if (isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress'))
    return `${Math.round(task.meta?.progress || 0)}%`
  if (isTaskStatus(task, 'completed')) return 'Done'
  if (isTaskStatus(task, 'failed')) return 'Failed'
  if (isTaskStatus(task, 'cancelled')) return 'Cancelled'
  return 'Pending'
}

// Typed accessors for the warnings payload (typed loosely as Record<string,
// unknown> on the model). Keep the shape the template expects.
interface SkippedRowDetail {
  row_index: number | string
  reason: string
}
interface SkippedRows {
  count?: number
  details?: SkippedRowDetail[]
}
interface FileTaskWarnings {
  messages?: string[]
  skipped_rows?: SkippedRows
}

function getWarnings(fileTask: FilePreprocessingTask): FileTaskWarnings | null {
  if (!fileTask.warnings) return null
  return fileTask.warnings as unknown as FileTaskWarnings
}

// Format relative time. Delegates the just-now/m/h tiers to the shared
// formatter; runs older than 24h fall back to a locale date (preserves the
// original 24h cutoff vs the shared 30-day "Xd ago" tier).
const formatRelativeTime = (dateString: string | null | undefined): string => {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return ''
  if (Date.now() - date.getTime() >= 86400000) return date.toLocaleDateString()
  return sharedFormatRelativeTime(dateString)
}

// Format processing time in seconds to human readable
const formatProcessingTime = (seconds: number | null): string => {
  if (!seconds && seconds !== 0) return ''
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}
</script>
