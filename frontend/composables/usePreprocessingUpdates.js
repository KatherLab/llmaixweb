/**
 * WebSocket subscription for preprocessing task updates.
 *
 * Extracted from FilesAndProcessing.vue. Subscribes to preprocessing updates via the
 * shared websocketService, filters to the current project, and either:
 *   - merges progress updates directly into the files array (for in-flight tasks), or
 *   - debounces a full refetch (for new/terminal tasks).
 *
 * Preserves the original merge fixup ({ ...existing, ...data, id: taskId }), project-id
 * filtering, seen-task tracking, terminal-state cache invalidation, and 500ms refresh
 * debounce.
 *
 * @param {Object} opts
 * @param {import('vue').Ref<string|number>} opts.projectId
 * @param {import('vue').Ref<Array>} opts.files
 * @param {import('vue').Ref<Object|null>} opts.historyFile
 * @param {(file: Object) => string} opts.getFileStatus
 * @param {(opts?: Object) => Promise<void>} opts.fetchFiles
 * @param {() => void} opts.invalidateTaskCache - clear the cached preprocessing tasks
 * @returns {{ start: () => void, stop: () => void }}
 */
import { watch } from 'vue'
import { websocketService } from '@/services/websocket.js'
import { isForProject, mergeWsEntity } from '@/composables/useWsEntityUpdates'

export function usePreprocessingUpdates({
  projectId,
  files,
  historyFile,
  getFileStatus,
  fetchFiles,
  invalidateTaskCache,
}) {
  let wsPreprocessingUnsubscribe = null
  const seenTaskIds = new Set()

  let refreshDebounceTimer = null
  const REFRESH_DEBOUNCE_MS = 500 // Wait 500ms after last trigger before refetching

  const start = () => {
    wsPreprocessingUnsubscribe = websocketService.onPreprocessingUpdate((data) => {
      // Only update if the task belongs to this project
      if (!isForProject(data, projectId.value)) return

      // Check if this is a new task we haven't seen before
      const taskId = data.task_id
      const isNewTask = !seenTaskIds.has(taskId)
      if (taskId) {
        seenTaskIds.add(taskId)
      }

      // Check for terminal states via event field or status
      const isTerminalState =
        ['completed', 'failed', 'cancelled'].includes(String(data.event || '')) ||
        ['completed', 'failed', 'cancelled'].includes(String(data.status || '').toLowerCase())

      if (isTerminalState || isNewTask) {
        // Invalidate task cache immediately for terminal states to force fresh fetch
        if (isTerminalState) {
          invalidateTaskCache()
        }
        // Use debounced refresh to prevent rapid refetches when multiple tasks complete
        debouncedFetchFiles()
      } else {
        // For progress updates, merge the WebSocket data directly into files
        mergePreprocessingUpdate(data)
      }
    })
  }

  // Merge WebSocket preprocessing update into files array
  const mergePreprocessingUpdate = (data) => {
    const taskId = data.task_id
    if (!taskId) return

    // Find the file that has this task in its preprocessing_tasks
    const fileIndex = files.value.findIndex((f) =>
      f.preprocessing_tasks?.some((t) => t.id === taskId),
    )

    if (fileIndex >= 0) {
      const file = files.value[fileIndex]

      // Update historyFile first if this file is currently being shown
      const isHistoryFile = historyFile.value?.id === file.id

      const taskIndex = file.preprocessing_tasks.findIndex((t) => t.id === taskId)

      if (taskIndex >= 0) {
        // Merge the update into the existing task (shared id-fixup + meta-merge)
        const existingTask = file.preprocessing_tasks[taskIndex]
        const updatedTask = mergeWsEntity(existingTask, data, taskId, 'task_id')

        // Preserve and merge configuration
        if (data.configuration) {
          updatedTask.configuration = data.configuration
        }

        // Calculate progress percentage if not provided but we have the data
        if (!updatedTask.meta?.progress && updatedTask.meta?.total_files > 0) {
          const completed = updatedTask.meta.completed_files || 0
          const total = updatedTask.meta.total_files
          updatedTask.meta = {
            ...(updatedTask.meta || {}),
            progress: (completed / total) * 100,
          }
        } else if (
          !updatedTask.meta?.progress &&
          updatedTask.processed_files > 0 &&
          updatedTask.total_files > 0
        ) {
          // Fallback: calculate from processed_files/total_files
          updatedTask.meta = {
            ...(updatedTask.meta || {}),
            progress: (updatedTask.processed_files / updatedTask.total_files) * 100,
          }
        }

        file.preprocessing_tasks[taskIndex] = updatedTask
        file._status = getFileStatus(file)

        // Trigger reactivity
        files.value = [...files.value]

        // Also update historyFile if this file is currently being shown
        if (isHistoryFile) {
          historyFile.value = { ...file }
        }
      }
    }
  }

  const stop = () => {
    if (wsPreprocessingUnsubscribe) {
      wsPreprocessingUnsubscribe()
      wsPreprocessingUnsubscribe = null
    }
    if (refreshDebounceTimer) {
      clearTimeout(refreshDebounceTimer)
      refreshDebounceTimer = null
    }
  }

  // Debounced refresh to prevent rapid refetches when multiple tasks update simultaneously
  const debouncedFetchFiles = () => {
    if (refreshDebounceTimer) {
      clearTimeout(refreshDebounceTimer)
    }
    refreshDebounceTimer = setTimeout(() => {
      // Always force refresh tasks when triggered by terminal state
      fetchFiles({ forceRefreshTasks: true })
      refreshDebounceTimer = null
    }, REFRESH_DEBOUNCE_MS)
  }

  // Connect the WebSocket when there are active tasks.
  watch(
    () =>
      files.value.some((f) =>
        f.preprocessing_tasks?.some((t) =>
          ['pending', 'processing', 'in_progress'].includes(String(t.status || '').toLowerCase()),
        ),
      ),
    (hasActiveTasks) => {
      // With WebSocket, we don't need to start/stop anything
      // The connection is already established and listening
      if (hasActiveTasks && !websocketService.isConnected) {
        websocketService.connect()
      }
    },
    { immediate: true },
  )

  return { start, stop }
}
