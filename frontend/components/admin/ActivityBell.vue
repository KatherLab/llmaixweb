<template>
  <div ref="bellRoot" class="relative">
    <!-- Bell Button -->
    <button
      ref="bellButton"
      type="button"
      :aria-label="$t('admin.activity.view_activity')"
      :aria-expanded="showDropdown"
      aria-haspopup="true"
      class="relative p-2 rounded-full hover:bg-surface-sunken transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
      :class="{ 'text-primary': hasActiveTasks }"
      @click="toggleDropdown"
    >
      <!-- Bell icon -->
      <Bell class="w-6 h-6 text-content-subtle" />

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
        class="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-surface"
      />
    </button>

    <!-- Dropdown Panel -->
    <transition name="fade-slide">
      <div
        v-if="showDropdown"
        class="absolute right-0 mt-2 w-[420px] bg-surface border border-default rounded-modal shadow-2xl z-50 max-h-[500px] flex flex-col"
      >
        <!-- Header -->
        <div class="px-4 py-3 border-b border-default flex items-center justify-between">
          <h3 class="font-semibold text-content">{{ $t('admin.activity.title') }}</h3>
          <div class="flex items-center gap-2">
            <span v-if="hasActiveTasks" class="text-xs text-primary font-medium">
              {{ $t('admin.activity.running', { count: activeCount }) }}
            </span>
            <button
              v-if="displayTasks.length > 0"
              type="button"
              class="text-xs text-content-subtle hover:text-content-muted"
              :title="$t('admin.activity.dismiss_all')"
              @click="dismissAll"
            >
              {{ $t('admin.activity.dismiss_all') }}
            </button>
          </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto">
          <!-- Loading state (only on initial load) -->
          <div v-if="isLoading && !hasLoadedOnce" class="flex items-center justify-center py-12">
            <LoadingSpinner size="medium" />
          </div>

          <!-- Empty state -->
          <div v-else-if="displayTasks.length === 0" class="text-center py-12">
            <CircleCheckBig class="mx-auto h-12 w-12 text-content-subtle" />
            <p class="mt-3 text-sm text-content-subtle">{{ $t('admin.activity.no_recent') }}</p>
          </div>

          <!-- Task list grouped by type -->
          <div v-else class="divide-y divide-default">
            <!-- Preprocessing Tasks Section -->
            <div v-if="preprocessingTasks.length > 0">
              <div class="px-3 py-2 bg-surface-muted border-b border-default">
                <div class="flex items-center gap-2">
                  <Clipboard class="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  <h4 class="text-xs font-semibold text-content-muted uppercase tracking-wide">
                    {{
                      $t('admin.activity.preprocessing_count', { count: preprocessingTasks.length })
                    }}
                  </h4>
                </div>
              </div>
              <div>
                <div
                  v-for="task in preprocessingTasks"
                  :key="`preprocess-${task.id}`"
                  role="button"
                  tabindex="0"
                  :aria-label="
                    $t('admin.activity.view_preprocessing_task', {
                      name: task.configuration?.name || `#${task.id}`,
                    })
                  "
                  class="px-4 py-3 hover:bg-surface-muted transition-colors cursor-pointer group focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                  @click="navigateToPreprocessing(task)"
                  @keydown.enter.self.prevent="navigateToPreprocessing(task)"
                  @keydown.space.self.prevent="navigateToPreprocessing(task)"
                >
                  <div class="flex items-start gap-3">
                    <!-- Status indicator -->
                    <div class="flex-shrink-0 mt-0.5">
                      <div
                        v-if="isTaskActive(task)"
                        class="w-2.5 h-2.5 rounded-full bg-primary animate-pulse"
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
                        <p class="text-sm font-medium text-content truncate">
                          {{
                            task.configuration?.name ||
                            $t('admin.activity.task_number', { id: task.id })
                          }}
                        </p>
                        <!-- Cancel button (visible on hover, active tasks only) -->
                        <button
                          v-if="isTaskActive(task)"
                          type="button"
                          class="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100 transition-opacity p-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                          :title="$t('admin.activity.cancel_task')"
                          :aria-label="$t('admin.activity.cancel_task')"
                          @click.stop="cancelPreprocessing(task)"
                        >
                          <CircleStop class="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                        </button>
                        <!-- Dismiss button (visible on hover/focus) -->
                        <button
                          type="button"
                          class="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100 transition-opacity p-0.5 hover:bg-surface-sunken rounded"
                          :title="$t('admin.activity.dismiss')"
                          :aria-label="$t('admin.activity.dismiss_task')"
                          @click.stop="dismissTask('preprocess', task.id)"
                        >
                          <X class="w-3.5 h-3.5 text-content-subtle" />
                        </button>
                      </div>
                      <p class="text-xs text-content-subtle mt-0.5">
                        {{ getPreprocessingSummary(task) }}
                      </p>

                      <!-- Progress bar for active tasks -->
                      <div v-if="isTaskActive(task) && task.meta" class="mt-2">
                        <div
                          class="flex items-center justify-between text-xs text-content-subtle mb-1"
                          aria-live="polite"
                        >
                          <span>{{ $t('admin.activity.processing') }}</span>
                          <span>{{ getProgressPercent(task) }}%</span>
                        </div>
                        <div
                          class="w-full bg-surface-sunken rounded-full h-1.5 overflow-hidden"
                          role="progressbar"
                          :aria-label="$t('admin.activity.preprocessing_progress')"
                          :aria-valuenow="getProgressPercent(task)"
                          aria-valuemin="0"
                          aria-valuemax="100"
                        >
                          <div
                            class="bg-primary h-1.5 rounded-full transition-all duration-300"
                            :style="{ width: `${getProgressPercent(task)}%` }"
                          />
                        </div>
                      </div>

                      <!-- Time info -->
                      <p class="text-xs text-content-subtle mt-1.5">
                        {{ formatTaskTime(task) }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Trials Section -->
            <div v-if="trialTasks.length > 0">
              <div class="px-3 py-2 bg-surface-muted border-b border-default">
                <div class="flex items-center gap-2">
                  <FlaskConical class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <h4 class="text-xs font-semibold text-content-muted uppercase tracking-wide">
                    {{ $t('admin.activity.trials_count', { count: trialTasks.length }) }}
                  </h4>
                </div>
              </div>
              <div>
                <div
                  v-for="task in trialTasks"
                  :key="`trial-${task.id}`"
                  role="button"
                  tabindex="0"
                  :aria-label="$t('admin.activity.view_trial', { name: trialLabel(task, task.id) })"
                  class="px-4 py-3 hover:bg-surface-muted transition-colors cursor-pointer group focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                  @click="navigateToTrial(task)"
                  @keydown.enter.self.prevent="navigateToTrial(task)"
                  @keydown.space.self.prevent="navigateToTrial(task)"
                >
                  <div class="flex items-start gap-3">
                    <!-- Status indicator -->
                    <div class="flex-shrink-0 mt-0.5">
                      <div
                        v-if="isTrialActive(task)"
                        class="w-2.5 h-2.5 rounded-full bg-primary animate-pulse"
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
                        <p class="text-sm font-medium text-content truncate">
                          {{ trialLabel(task, task.id) }}
                        </p>
                        <!-- Dismiss button (visible on hover/focus) -->
                        <button
                          type="button"
                          class="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100 transition-opacity p-0.5 hover:bg-surface-sunken rounded"
                          :title="$t('admin.activity.dismiss')"
                          :aria-label="$t('admin.activity.dismiss_trial')"
                          @click.stop="dismissTask('trial', task.id)"
                        >
                          <X class="w-3.5 h-3.5 text-content-subtle" />
                        </button>
                      </div>
                      <p class="text-xs text-content-subtle mt-0.5">
                        {{ getTrialSummary(task) }}
                      </p>

                      <!-- Progress bar for active tasks -->
                      <div v-if="isTrialActive(task)" class="mt-2">
                        <div
                          class="flex items-center justify-between text-xs text-content-subtle mb-1"
                        >
                          <span>{{
                            $t('admin.activity.docs_progress', {
                              done: task.docs_done || 0,
                              total: task.documents_count,
                            })
                          }}</span>
                          <span>{{ Math.round((task.progress || 0) * 100) }}%</span>
                        </div>
                        <div class="w-full bg-surface-sunken rounded-full h-1.5 overflow-hidden">
                          <div
                            class="bg-emerald-600 h-1.5 rounded-full transition-all duration-300"
                            :style="{ width: `${Math.round((task.progress || 0) * 100)}%` }"
                          />
                        </div>
                      </div>

                      <!-- Time info -->
                      <p class="text-xs text-content-subtle mt-1.5">
                        {{ formatTaskTime(task) }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer (admin only: /admin/celery is behind the adminOnly guard) -->
        <div
          v-if="displayTasks.length > 0 && isAdmin"
          class="px-4 py-2 border-t border-default bg-surface-muted rounded-b-xl"
        >
          <button
            type="button"
            class="w-full text-center text-sm text-primary font-medium hover:underline"
            @click="viewAllActivity"
          >
            {{ $t('admin.activity.view_all') }}
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
import { useClickOutside } from '@/composables/useClickOutside'
import { useAuthStore } from '@/stores/auth'
import { websocketService } from '@/services/websocket'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatRelativeTime } from '@/utils/formatters'
import { trialLabel } from '@/utils/trialLabel'
import { mergeWsEntity } from '@/composables/useWsEntityUpdates'

const router = useRouter()
const { t } = useI18n({ useScope: 'global' })
const toast = useToast()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)

interface DismissedTasks {
  preprocess: Set<number>
  trial: Set<number>
}

// State
const showDropdown = ref(false)
const bellRoot = ref<HTMLElement | null>(null)
const bellButton = ref<HTMLButtonElement | null>(null)
const preprocessingTasks = ref<PreprocessingTask[]>([])
const trialTasks = ref<TrialSummary[]>([])
const isLoading = ref(false)
const hasLoadedOnce = ref(false)
const dismissedTasks = ref<DismissedTasks>({
  preprocess: new Set<number>(),
  trial: new Set<number>(),
})
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

// Close on outside click (wrapper contains both the bell button and the panel).
useClickOutside(bellRoot, closeDropdown)

// Escape closes the dropdown and returns focus to the bell button.
const handleKeydown = (e: KeyboardEvent): void => {
  if (e.key === 'Escape' && showDropdown.value) {
    closeDropdown()
    bellButton.value?.focus()
  }
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
    return t('admin.activity.files_processing', { completed, total })
  } else if (task.status === 'completed') {
    return t('admin.activity.files_done', { total })
  } else if (task.status === 'failed') {
    return t('admin.activity.files_failed', { failed, total })
  } else if (task.status === 'cancelled') {
    return t('admin.activity.cancelled')
  }
  return t('admin.activity.files_count', { total })
}

const getTrialSummary = (task: TrialSummary): string => {
  const total = task.documents_count || 0
  const completed = task.results_count || task.docs_done || 0
  const errors = task.error_count || 0

  if (isTrialActive(task)) {
    return t('admin.activity.docs_extracting', { completed, total })
  } else if (task.status === 'completed') {
    if (errors > 0) {
      return t('admin.activity.docs_done_errors', { total, errors })
    }
    return t('admin.activity.docs_done', { total })
  } else if (task.status === 'failed') {
    return t('admin.activity.extraction_failed')
  } else if (task.status === 'cancelled') {
    return t('admin.activity.cancelled')
  }
  return t('admin.activity.docs_count', { total })
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
  return result === 'just now' ? t('admin.activity.just_now') : result
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
    toast.error(t('admin.activity.errors.load_failed'))
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
    toast.error(t('admin.activity.errors.navigate_missing_project'))
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
    toast.error(t('admin.activity.errors.cancel_missing_project'))
    return
  }
  try {
    await preprocessingApi.cancel(task.project_id, task.id)
    toast.success(t('admin.activity.preprocessing_cancelled'))
    // Update local state
    const idx = preprocessingTasks.value.findIndex((t) => t.id === task.id)
    const target = idx >= 0 ? preprocessingTasks.value[idx] : undefined
    if (target) {
      target.status = 'cancelled'
      target.is_cancelled = true
    }
  } catch (err) {
    console.error('Failed to cancel preprocessing:', err)
    toast.error(t('admin.activity.errors.cancel_failed'))
  }
}

const navigateToTrial = (task: TrialSummary): void => {
  if (!task.project_id) {
    console.error('Trial missing project_id:', task)
    toast.error(t('admin.activity.errors.navigate_missing_project'))
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
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  if (wsCleanup) wsCleanup()
  stopWebSocket()
  document.removeEventListener('keydown', handleKeydown)
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
