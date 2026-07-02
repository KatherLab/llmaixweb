<template>
  <div class="relative">
    <!-- Bell Button -->
    <button
      ref="bellButton"
      aria-label="View activity"
      class="relative p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      :class="{ 'text-blue-600 dark:text-blue-400': hasActiveTasks }"
      @click="toggleDropdown"
    >
      <!-- Bell icon -->
      <Bell class="w-6 h-6 text-slate-600 dark:text-slate-400" />

      <!-- Active tasks badge -->
      <span
        v-if="activeCount > 0"
        class="absolute top-1 right-1 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-xs font-bold text-white bg-red-500 rounded-full animate-pulse"
      >
        {{ activeCount }}
      </span>

      <!-- Recent activity indicator (no active but has recent) -->
      <span
        v-else-if="recentCompletedCount > 0"
        class="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-white dark:border-slate-900"
      />
    </button>

    <!-- Dropdown Panel -->
    <transition name="fade-slide">
      <div
        v-if="showDropdown"
        ref="dropdown"
        class="absolute right-0 mt-2 w-[420px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl z-50 max-h-[500px] flex flex-col"
        @click.outside="closeDropdown"
      >
        <!-- Header -->
        <div
          class="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between"
        >
          <h3 class="font-semibold text-slate-900 dark:text-white">Activity</h3>
          <div class="flex items-center gap-2">
            <span
              v-if="hasActiveTasks"
              class="text-xs text-blue-600 dark:text-blue-400 font-medium"
            >
              {{ activeCount }} running
            </span>
            <button
              v-if="displayTasks.length > 0"
              class="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              title="Dismiss all"
              @click="dismissAll"
            >
              Dismiss all
            </button>
          </div>
        </div>

        <!-- Content -->
        <div ref="scrollContainer" class="flex-1 overflow-y-auto">
          <!-- Loading state (only on initial load) -->
          <div v-if="isLoading && !hasLoadedOnce" class="flex items-center justify-center py-12">
            <LoadingSpinner size="medium" />
          </div>

          <!-- Empty state -->
          <div v-else-if="displayTasks.length === 0" class="text-center py-12">
            <CircleCheckBig class="mx-auto h-12 w-12 text-slate-300 dark:text-slate-700" />
            <p class="mt-3 text-sm text-slate-500 dark:text-slate-400">No recent activity</p>
          </div>

          <!-- Task list grouped by type -->
          <div v-else class="divide-y divide-slate-100 dark:divide-slate-800">
            <!-- Preprocessing Tasks Section -->
            <div v-if="preprocessingTasks.length > 0">
              <div
                class="px-3 py-2 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800"
              >
                <div class="flex items-center gap-2">
                  <Clipboard class="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  <h4
                    class="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide"
                  >
                    Preprocessing ({{ preprocessingTasks.length }})
                  </h4>
                </div>
              </div>
              <div>
                <div
                  v-for="task in preprocessingTasks"
                  :key="`preprocess-${task.id}`"
                  class="px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group"
                  @click="navigateToPreprocessing(task)"
                >
                  <div class="flex items-start gap-3">
                    <!-- Status indicator -->
                    <div class="flex-shrink-0 mt-0.5">
                      <div
                        v-if="isTaskActive(task)"
                        class="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse"
                      />
                      <div
                        v-else-if="task.status === 'completed'"
                        class="w-2.5 h-2.5 rounded-full bg-green-500"
                      />
                      <div
                        v-else-if="task.status === 'failed'"
                        class="w-2.5 h-2.5 rounded-full bg-red-500"
                      />
                      <div
                        v-else-if="task.status === 'cancelled'"
                        class="w-2.5 h-2.5 rounded-full bg-yellow-500"
                      />
                    </div>

                    <!-- Task info -->
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <p class="text-sm font-medium text-slate-900 dark:text-white truncate">
                          {{ task.configuration?.name || `Task #${task.id}` }}
                        </p>
                        <!-- Cancel button (visible on hover, active tasks only) -->
                        <button
                          v-if="isTaskActive(task)"
                          class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                          title="Cancel task"
                          @click.stop="cancelPreprocessing(task)"
                        >
                          <CircleStop class="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                        </button>
                        <!-- Dismiss button (visible on hover) -->
                        <button
                          class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                          title="Dismiss"
                          @click.stop="dismissTask('preprocess', task.id)"
                        >
                          <X class="w-3.5 h-3.5 text-slate-400" />
                        </button>
                      </div>
                      <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        {{ getPreprocessingSummary(task) }}
                      </p>

                      <!-- Progress bar for active tasks -->
                      <div v-if="isTaskActive(task) && task.meta" class="mt-2">
                        <div
                          class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1"
                        >
                          <span>Processing...</span>
                          <span>{{ getProgressPercent(task) }}%</span>
                        </div>
                        <div
                          class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden"
                        >
                          <div
                            class="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                            :style="{ width: `${getProgressPercent(task)}%` }"
                          />
                        </div>
                      </div>

                      <!-- Time info -->
                      <p class="text-xs text-slate-400 dark:text-slate-500 mt-1.5">
                        {{ formatTaskTime(task) }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Trials Section -->
            <div v-if="trialTasks.length > 0">
              <div
                class="px-3 py-2 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800"
              >
                <div class="flex items-center gap-2">
                  <FlaskConical class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <h4
                    class="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide"
                  >
                    Trials ({{ trialTasks.length }})
                  </h4>
                </div>
              </div>
              <div>
                <div
                  v-for="task in trialTasks"
                  :key="`trial-${task.id}`"
                  class="px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group"
                  @click="navigateToTrial(task)"
                >
                  <div class="flex items-start gap-3">
                    <!-- Status indicator -->
                    <div class="flex-shrink-0 mt-0.5">
                      <div
                        v-if="isTrialActive(task)"
                        class="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse"
                      />
                      <div
                        v-else-if="task.status === 'completed'"
                        class="w-2.5 h-2.5 rounded-full bg-green-500"
                      />
                      <div
                        v-else-if="task.status === 'failed'"
                        class="w-2.5 h-2.5 rounded-full bg-red-500"
                      />
                      <div
                        v-else-if="task.status === 'cancelled'"
                        class="w-2.5 h-2.5 rounded-full bg-yellow-500"
                      />
                    </div>

                    <!-- Task info -->
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <p class="text-sm font-medium text-slate-900 dark:text-white truncate">
                          {{ task.name || `Trial #${task.id}` }}
                        </p>
                        <!-- Dismiss button (visible on hover) -->
                        <button
                          class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded"
                          title="Dismiss"
                          @click.stop="dismissTask('trial', task.id)"
                        >
                          <X class="w-3.5 h-3.5 text-slate-400" />
                        </button>
                      </div>
                      <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        {{ getTrialSummary(task) }}
                      </p>

                      <!-- Progress bar for active tasks -->
                      <div v-if="isTrialActive(task)" class="mt-2">
                        <div
                          class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1"
                        >
                          <span>{{ task.docs_done || 0 }}/{{ task.documents_count }} docs</span>
                          <span>{{ Math.round((task.progress || 0) * 100) }}%</span>
                        </div>
                        <div
                          class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden"
                        >
                          <div
                            class="bg-emerald-600 h-1.5 rounded-full transition-all duration-300"
                            :style="{ width: `${Math.round((task.progress || 0) * 100)}%` }"
                          />
                        </div>
                      </div>

                      <!-- Time info -->
                      <p class="text-xs text-slate-400 dark:text-slate-500 mt-1.5">
                        {{ formatTaskTime(task) }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div
          v-if="displayTasks.length > 0"
          class="px-4 py-2 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 rounded-b-xl"
        >
          <button
            class="w-full text-center text-sm text-blue-600 dark:text-blue-400 font-medium hover:underline"
            @click="viewAllActivity"
          >
            View all activity
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, CircleCheckBig, CircleStop, Clipboard, FlaskConical, X } from '@lucide/vue'
import type {
  PreprocessingTask,
  TrialSummary,
  WsMessage,
  WsPreprocessingUpdate,
  WsTrialUpdate,
} from '@/types'
import { projectsApi } from '@/services/projectsApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { useToast } from '@/composables/useToast'
import { websocketService } from '@/services/websocket'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatRelativeTime } from '@/utils/formatters'
import { mergeWsEntity } from '@/composables/useWsEntityUpdates'

const router = useRouter()
const toast = useToast()

interface DismissedTasks {
  preprocess: Set<number>
  trial: Set<number>
}

// State
const showDropdown = ref(false)
const preprocessingTasks = ref<PreprocessingTask[]>([])
const trialTasks = ref<TrialSummary[]>([])
const isLoading = ref(false)
const hasLoadedOnce = ref(false)
const dismissedTasks = ref<DismissedTasks>({
  preprocess: new Set<number>(),
  trial: new Set<number>(),
})
const scrollContainer = ref<HTMLElement | null>(null)
const wsUnsubscribe = ref<(() => void) | null>(null)

// Load dismissed tasks from localStorage
const loadDismissedTasks = (): void => {
  try {
    const stored = localStorage.getItem('dismissedActivityTasks')
    if (stored) {
      const parsed = JSON.parse(stored) as { preprocess?: number[]; trial?: number[] }
      dismissedTasks.value.preprocess = new Set<number>(parsed.preprocess || [])
      dismissedTasks.value.trial = new Set<number>(parsed.trial || [])
    }
  } catch (e) {
    console.error('Failed to load dismissed tasks:', e)
  }
}

// Save dismissed tasks to localStorage
const saveDismissedTasks = (): void => {
  try {
    const toStore = {
      preprocess: Array.from(dismissedTasks.value.preprocess),
      trial: Array.from(dismissedTasks.value.trial),
    }
    localStorage.setItem('dismissedActivityTasks', JSON.stringify(toStore))
  } catch (e) {
    console.error('Failed to save dismissed tasks:', e)
  }
}

// Computed
const activeCount = computed(() => {
  const activePreprocess = preprocessingTasks.value.filter((t) => isTaskActive(t)).length
  const activeTrials = trialTasks.value.filter((t) => isTrialActive(t)).length
  return activePreprocess + activeTrials
})

const recentCompletedCount = computed(() => {
  const completedPreprocess = preprocessingTasks.value.filter(
    (t) => t.status === 'completed',
  ).length
  const completedTrials = trialTasks.value.filter((t) => t.status === 'completed').length
  return completedPreprocess + completedTrials
})

const hasActiveTasks = computed(() => activeCount.value > 0)

const displayTasks = computed(() => {
  return [...preprocessingTasks.value, ...trialTasks.value]
})

// Methods
const toggleDropdown = (): void => {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value && displayTasks.value.length === 0) {
    fetchAllTasks(false)
  }
}

const closeDropdown = (): void => {
  showDropdown.value = false
}

const isTaskActive = (task: PreprocessingTask): boolean => {
  return ['pending', 'in_progress', 'processing'].includes(task.status)
}

const isTrialActive = (task: TrialSummary): boolean => {
  return ['pending', 'processing'].includes(task.status)
}

const getPreprocessingSummary = (task: PreprocessingTask): string => {
  const total = task.meta?.total_files || task.total_files || 0
  const completed = task.meta?.completed_files || task.processed_files || 0
  const failed = task.meta?.failed_files || task.failed_files || 0

  if (isTaskActive(task)) {
    return `${completed}/${total} files processed`
  } else if (task.status === 'completed') {
    return `✓ ${total} files processed`
  } else if (task.status === 'failed') {
    return `✗ ${failed} of ${total} files failed`
  } else if (task.status === 'cancelled') {
    return `Cancelled`
  }
  return `${total} files`
}

const getTrialSummary = (task: TrialSummary): string => {
  const total = task.documents_count || 0
  const completed = task.results_count || task.docs_done || 0
  const errors = task.error_count || 0

  if (isTrialActive(task)) {
    return `${completed}/${total} docs extracted`
  } else if (task.status === 'completed') {
    if (errors > 0) {
      return `✓ ${total} docs extracted (${errors} errors)`
    }
    return `✓ ${total} docs extracted`
  } else if (task.status === 'failed') {
    return `✗ Extraction failed`
  } else if (task.status === 'cancelled') {
    return `Cancelled`
  }
  return `${total} docs`
}

const getProgressPercent = (task: PreprocessingTask): number => {
  const total = task.meta?.total_files || task.total_files || 1
  const completed = task.meta?.completed_files || task.processed_files || 0
  return Math.min(Math.round((completed / total) * 100), 100)
}

const formatTaskTime = (task: PreprocessingTask | TrialSummary): string => {
  if (!task?.created_at) return ''
  const taskDate = new Date(task.created_at)
  if (isNaN(taskDate.getTime())) return ''
  // Tasks older than 24h fall back to a locale date (matches the original
  // behavior; displayed tasks are fetched with a 24h window anyway).
  if (Date.now() - taskDate.getTime() >= 86400000) return taskDate.toLocaleDateString()
  // Delegates the "just now"/"m ago"/"h ago" tiers to the shared formatter;
  // ActivityBell capitalizes "Just now" in the UI.
  const result = formatRelativeTime(task.created_at)
  return result === 'just now' ? 'Just now' : result
}

const dismissTask = (type: 'preprocess' | 'trial', id: number): void => {
  dismissedTasks.value[type].add(id)
  saveDismissedTasks()

  // Remove from current lists
  if (type === 'preprocess') {
    preprocessingTasks.value = preprocessingTasks.value.filter((t) => t.id !== id)
  } else {
    trialTasks.value = trialTasks.value.filter((t) => t.id !== id)
  }
}

const dismissAll = (): void => {
  // Get all task IDs
  const preprocessIds = preprocessingTasks.value.map((t) => t.id)
  const trialIds = trialTasks.value.map((t) => t.id)

  // Add to dismissed
  preprocessIds.forEach((id) => dismissedTasks.value.preprocess.add(id))
  trialIds.forEach((id) => dismissedTasks.value.trial.add(id))
  saveDismissedTasks()

  // Clear lists
  preprocessingTasks.value = []
  trialTasks.value = []
}

const fetchAllTasks = async (isPolling = false): Promise<void> => {
  // Only show loading on initial load, not during polling
  if (!isPolling) {
    isLoading.value = true
  }
  try {
    // Fetch preprocessing tasks (active + last 24 hours)
    const preprocessResponse = await projectsApi.activityPreprocess({ limit: 10, hours: 24 })
    const allPreprocessTasks = preprocessResponse.data || []

    // Filter out dismissed
    preprocessingTasks.value = allPreprocessTasks.filter(
      (t) => !dismissedTasks.value.preprocess.has(t.id),
    )

    // Fetch trial tasks (active + last 24 hours)
    const trialResponse = await projectsApi.activityTrials({ limit: 10, hours: 24 })
    const allTrialTasks = trialResponse.data || []

    // Filter out dismissed
    trialTasks.value = allTrialTasks.filter((t) => !dismissedTasks.value.trial.has(t.id))

    hasLoadedOnce.value = true
  } catch (err) {
    console.error('Failed to fetch activity tasks:', err)
    toast.error('Failed to load activity')
  } finally {
    isLoading.value = false
  }
}

const startWebSocket = (): (() => void) => {
  // Subscribe to preprocessing updates
  wsUnsubscribe.value = websocketService.onPreprocessingUpdate((data) => {
    handlePreprocessingUpdate(data)
  })

  // Subscribe to trial updates
  const trialUnsubscribe = websocketService.onTrialUpdate((data) => {
    handleTrialUpdate(data)
  })

  // Store unsubscribe functions
  return () => {
    wsUnsubscribe.value?.()
    trialUnsubscribe()
  }
}

const handlePreprocessingUpdate = (data: WsMessage): void => {
  const update = data as WsPreprocessingUpdate
  // Backend sends task_id, but we need to merge it properly
  // The data structure from backend: { task_id, project_id, status, meta, configuration, ... }
  const taskId = update.task_id || (update.id as number | undefined)

  if (taskId === undefined) return

  // Find existing task by ID
  const existingIndex = preprocessingTasks.value.findIndex((t) => t.id === taskId)

  if (existingIndex >= 0) {
    // Merge incoming data into the existing task (shared WS merge helper).
    const task = preprocessingTasks.value[existingIndex]
    preprocessingTasks.value[existingIndex] = mergeWsEntity(
      task as unknown as Record<string, unknown>,
      update as Record<string, unknown>,
      taskId,
      'task_id',
    ) as unknown as PreprocessingTask
  } else {
    // New task - fetch full data from server
    fetchAllTasks(true)
  }
}

const handleTrialUpdate = (data: WsMessage): void => {
  const update = data as WsTrialUpdate
  const trialId = update.trial_id || (update.id as number | undefined)
  if (trialId === undefined) return

  const existingIndex = trialTasks.value.findIndex((t) => t.id === trialId)

  if (existingIndex >= 0) {
    const task = trialTasks.value[existingIndex]
    trialTasks.value[existingIndex] = mergeWsEntity(
      task as unknown as Record<string, unknown>,
      update as Record<string, unknown>,
      trialId,
      'trial_id',
    ) as unknown as TrialSummary
  } else {
    // New trial - fetch full data from server
    fetchAllTasks(true)
  }
}

const stopWebSocket = (): void => {
  wsUnsubscribe.value?.()
  wsUnsubscribe.value = null
}

const navigateToPreprocessing = (task: PreprocessingTask): void => {
  if (!task.project_id) {
    console.error('Preprocessing task missing project_id:', task)
    toast.error('Cannot navigate: missing project info')
    return
  }
  router.push({
    path: `/projects/${task.project_id}`,
    query: { tab: 'files', expandTask: task.id },
  })
  closeDropdown()
}

const cancelPreprocessing = async (task: PreprocessingTask): Promise<void> => {
  if (!task.project_id) {
    toast.error('Cannot cancel: missing project info')
    return
  }
  try {
    await preprocessingApi.cancel(task.project_id, task.id)
    toast.success('Preprocessing cancelled')
    // Update local state
    const idx = preprocessingTasks.value.findIndex((t) => t.id === task.id)
    const target = idx >= 0 ? preprocessingTasks.value[idx] : undefined
    if (target) {
      target.status = 'cancelled'
      target.is_cancelled = true
    }
  } catch (err) {
    console.error('Failed to cancel preprocessing:', err)
    toast.error('Failed to cancel preprocessing')
  }
}

const navigateToTrial = (task: TrialSummary): void => {
  if (!task.project_id) {
    console.error('Trial missing project_id:', task)
    toast.error('Cannot navigate: missing project info')
    return
  }
  router.push({
    path: `/projects/${task.project_id}`,
    query: { tab: 'trials', expandTrial: task.id },
  })
  closeDropdown()
}

const viewAllActivity = (): void => {
  router.push('/admin/celery')
  closeDropdown()
}

// Lifecycle
let wsCleanup: (() => void) | null = null

onMounted(() => {
  loadDismissedTasks()
  fetchAllTasks()
  wsCleanup = startWebSocket()
})

onUnmounted(() => {
  if (wsCleanup) wsCleanup()
  stopWebSocket()
})
</script>

<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity 0.15s,
    transform 0.15s;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}
</style>
