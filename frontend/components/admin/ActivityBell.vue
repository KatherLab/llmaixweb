<template>
  <div class="relative">
    <!-- Bell Button -->
    <button
      ref="bellButton"
      aria-label="View activity"
      class="relative p-2 rounded-full hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      :class="{ 'text-blue-600 dark:text-blue-400': hasActiveTasks }"
      @click="toggleDropdown"
    >
      <!-- Bell icon -->
      <svg
        class="w-6 h-6 text-gray-600 dark:text-slate-400"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>

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
        class="absolute right-0 mt-2 w-[420px] bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-2xl z-50 max-h-[500px] flex flex-col"
        @click.outside="closeDropdown"
      >
        <!-- Header -->
        <div
          class="px-4 py-3 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between"
        >
          <h3 class="font-semibold text-gray-900 dark:text-white">Activity</h3>
          <div class="flex items-center gap-2">
            <span
              v-if="hasActiveTasks"
              class="text-xs text-blue-600 dark:text-blue-400 font-medium"
            >
              {{ activeCount }} running
            </span>
            <button
              v-if="displayTasks.length > 0"
              class="text-xs text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
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
            <svg class="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          </div>

          <!-- Empty state -->
          <div v-else-if="displayTasks.length === 0" class="text-center py-12">
            <svg
              class="mx-auto h-12 w-12 text-gray-300 dark:text-slate-700"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p class="mt-3 text-sm text-gray-500 dark:text-slate-400">No recent activity</p>
          </div>

          <!-- Task list grouped by type -->
          <div v-else class="divide-y divide-gray-100 dark:divide-slate-800">
            <!-- Preprocessing Tasks Section -->
            <div v-if="preprocessingTasks.length > 0">
              <div
                class="px-3 py-2 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-100 dark:border-slate-800"
              >
                <div class="flex items-center gap-2">
                  <svg
                    class="w-4 h-4 text-purple-600 dark:text-purple-400"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  <h4
                    class="text-xs font-semibold text-gray-700 dark:text-slate-300 uppercase tracking-wide"
                  >
                    Preprocessing ({{ preprocessingTasks.length }})
                  </h4>
                </div>
              </div>
              <div>
                <div
                  v-for="task in preprocessingTasks"
                  :key="`preprocess-${task.id}`"
                  class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group"
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
                        <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {{ task.configuration?.name || `Task #${task.id}` }}
                        </p>
                        <!-- Cancel button (visible on hover, active tasks only) -->
                        <button
                          v-if="isTaskActive(task)"
                          class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                          title="Cancel task"
                          @click.stop="cancelPreprocessing(task)"
                        >
                          <svg
                            class="w-3.5 h-3.5 text-red-600 dark:text-red-400"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"
                            />
                          </svg>
                        </button>
                        <!-- Dismiss button (visible on hover) -->
                        <button
                          class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-gray-200 dark:hover:bg-slate-700 rounded"
                          title="Dismiss"
                          @click.stop="dismissTask('preprocess', task.id)"
                        >
                          <svg
                            class="w-3.5 h-3.5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                      <p class="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                        {{ getPreprocessingSummary(task) }}
                      </p>

                      <!-- Progress bar for active tasks -->
                      <div v-if="isTaskActive(task) && task.meta" class="mt-2">
                        <div
                          class="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400 mb-1"
                        >
                          <span>Processing...</span>
                          <span>{{ getProgressPercent(task) }}%</span>
                        </div>
                        <div
                          class="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden"
                        >
                          <div
                            class="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                            :style="{ width: `${getProgressPercent(task)}%` }"
                          />
                        </div>
                      </div>

                      <!-- Time info -->
                      <p class="text-xs text-gray-400 dark:text-slate-500 mt-1.5">
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
                class="px-3 py-2 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-100 dark:border-slate-800"
              >
                <div class="flex items-center gap-2">
                  <svg
                    class="w-4 h-4 text-emerald-600 dark:text-emerald-400"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                    />
                  </svg>
                  <h4
                    class="text-xs font-semibold text-gray-700 dark:text-slate-300 uppercase tracking-wide"
                  >
                    Trials ({{ trialTasks.length }})
                  </h4>
                </div>
              </div>
              <div>
                <div
                  v-for="task in trialTasks"
                  :key="`trial-${task.id}`"
                  class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group"
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
                        <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {{ task.name || `Trial #${task.id}` }}
                        </p>
                        <!-- Dismiss button (visible on hover) -->
                        <button
                          class="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-gray-200 dark:hover:bg-slate-700 rounded"
                          title="Dismiss"
                          @click.stop="dismissTask('trial', task.id)"
                        >
                          <svg
                            class="w-3.5 h-3.5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            viewBox="0 0 24 24"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                      <p class="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                        {{ getTrialSummary(task) }}
                      </p>

                      <!-- Progress bar for active tasks -->
                      <div v-if="isTrialActive(task)" class="mt-2">
                        <div
                          class="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400 mb-1"
                        >
                          <span>{{ task.docs_done || 0 }}/{{ task.documents_count }} docs</span>
                          <span>{{ Math.round((task.progress || 0) * 100) }}%</span>
                        </div>
                        <div
                          class="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden"
                        >
                          <div
                            class="bg-emerald-600 h-1.5 rounded-full transition-all duration-300"
                            :style="{ width: `${Math.round((task.progress || 0) * 100)}%` }"
                          />
                        </div>
                      </div>

                      <!-- Time info -->
                      <p class="text-xs text-gray-400 dark:text-slate-500 mt-1.5">
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
          class="px-4 py-2 border-t border-gray-200 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/50 rounded-b-xl"
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

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { projectsApi } from '@/services/projectsApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { useToast } from 'vue-toastification'
import { websocketService } from '@/services/websocket.js'

const router = useRouter()
const toast = useToast()

// State
const showDropdown = ref(false)
const preprocessingTasks = ref([])
const trialTasks = ref([])
const isLoading = ref(false)
const hasLoadedOnce = ref(false)
const dismissedTasks = ref({ preprocess: new Set(), trial: new Set() })
const scrollContainer = ref(null)
const wsUnsubscribe = ref(null)

// Load dismissed tasks from localStorage
const loadDismissedTasks = () => {
  try {
    const stored = localStorage.getItem('dismissedActivityTasks')
    if (stored) {
      const parsed = JSON.parse(stored)
      dismissedTasks.value.preprocess = new Set(parsed.preprocess || [])
      dismissedTasks.value.trial = new Set(parsed.trial || [])
    }
  } catch (e) {
    console.error('Failed to load dismissed tasks:', e)
  }
}

// Save dismissed tasks to localStorage
const saveDismissedTasks = () => {
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
const toggleDropdown = () => {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value && displayTasks.value.length === 0) {
    fetchAllTasks(false)
  }
}

const closeDropdown = () => {
  showDropdown.value = false
}

const isTaskActive = (task) => {
  return ['pending', 'in_progress', 'processing'].includes(task.status)
}

const isTrialActive = (task) => {
  return ['pending', 'processing'].includes(task.status)
}

const getPreprocessingSummary = (task) => {
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

const getTrialSummary = (task) => {
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

const getProgressPercent = (task) => {
  const total = task.meta?.total_files || task.total_files || 1
  const completed = task.meta?.completed_files || task.processed_files || 0
  return Math.min(Math.round((completed / total) * 100), 100)
}

const formatTaskTime = (task) => {
  const now = new Date()
  const taskDate = new Date(task.created_at)
  const diff = now - taskDate

  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return taskDate.toLocaleDateString()
}

const dismissTask = (type, id) => {
  dismissedTasks.value[type].add(id)
  saveDismissedTasks()

  // Remove from current lists
  if (type === 'preprocess') {
    preprocessingTasks.value = preprocessingTasks.value.filter((t) => t.id !== id)
  } else {
    trialTasks.value = trialTasks.value.filter((t) => t.id !== id)
  }
}

const dismissAll = () => {
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

const fetchAllTasks = async (isPolling = false) => {
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

const startWebSocket = () => {
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

const handlePreprocessingUpdate = (data) => {
  // Backend sends task_id, but we need to merge it properly
  // The data structure from backend: { task_id, project_id, status, meta, configuration, ... }
  const taskId = data.task_id || data.id

  // Find existing task by ID
  const existingIndex = preprocessingTasks.value.findIndex((t) => t.id === taskId)

  if (existingIndex >= 0) {
    // Update existing task - merge incoming data carefully
    const task = preprocessingTasks.value[existingIndex]
    const updatedTask = {
      ...task,
      ...data,
      id: taskId, // Ensure id is set correctly
      task_id: undefined, // Remove task_id to avoid confusion
    }

    // Preserve nested configuration object
    if (data.configuration) {
      updatedTask.configuration = data.configuration
    }

    preprocessingTasks.value[existingIndex] = updatedTask
  } else {
    // New task - fetch full data from server
    fetchAllTasks(true)
  }
}

const handleTrialUpdate = (data) => {
  const trialId = data.trial_id || data.id
  const existingIndex = trialTasks.value.findIndex((t) => t.id === trialId)

  if (existingIndex >= 0) {
    const task = trialTasks.value[existingIndex]
    const updatedTask = {
      ...task,
      ...data,
      id: trialId,
      trial_id: undefined,
    }

    // Preserve and merge meta object
    if (data.meta) {
      updatedTask.meta = { ...(task.meta || {}), ...data.meta }
    }

    trialTasks.value[existingIndex] = updatedTask
  } else {
    // New trial - fetch full data from server
    fetchAllTasks(true)
  }
}

const stopWebSocket = () => {
  wsUnsubscribe.value?.()
  wsUnsubscribe.value = null
}

const navigateToPreprocessing = (task) => {
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

const cancelPreprocessing = async (task) => {
  if (!task.project_id) {
    toast.error('Cannot cancel: missing project info')
    return
  }
  try {
    await preprocessingApi.cancel(task.project_id, task.id)
    toast.success('Preprocessing cancelled')
    // Update local state
    const idx = preprocessingTasks.value.findIndex((t) => t.id === task.id)
    if (idx >= 0) {
      preprocessingTasks.value[idx].status = 'cancelled'
      preprocessingTasks.value[idx].is_cancelled = true
    }
  } catch (err) {
    console.error('Failed to cancel preprocessing:', err)
    toast.error('Failed to cancel preprocessing')
  }
}

const navigateToTrial = (task) => {
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

const viewAllActivity = () => {
  router.push('/admin/celery')
  closeDropdown()
}

// Lifecycle
let wsCleanup = null

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
