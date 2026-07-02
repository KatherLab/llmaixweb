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
 * @param opts
 * @param opts.projectId
 * @param opts.files
 * @param opts.historyFile
 * @param opts.getFileStatus
 * @param opts.fetchFiles
 * @param opts.invalidateTaskCache - clear the cached preprocessing tasks
 * @returns {{ start: () => void, stop: () => void }}
 */
import { watch, type Ref } from 'vue'
import { websocketService } from '@/services/websocket'
import { isForProject, mergeWsEntity } from '@/composables/useWsEntityUpdates'
import type { File, PreprocessingTask, WsPreprocessingUpdate } from '@/types'

/**
 * A `File` augmented with the preprocessing-task joins and computed status that
 * `FilesAndProcessing` attaches to list rows. These fields are added client-side
 * after fetch (not part of the backend `File` model) but are read/written here.
 */
export interface FileWithTasks extends File {
  preprocessing_tasks: PreprocessingTask[]
  _status?: string
}

/** Options object passed to `usePreprocessingUpdates`. */
interface UsePreprocessingUpdatesOptions {
  projectId: Ref<string | number>
  files: Ref<FileWithTasks[]>
  historyFile: Ref<FileWithTasks | null>
  getFileStatus: (file: FileWithTasks) => string
  fetchFiles: (opts?: { forceRefreshTasks?: boolean }) => Promise<void>
  /** Clear the cached preprocessing tasks. */
  invalidateTaskCache: () => void
}

/** Return type of `usePreprocessingUpdates`. */
interface UsePreprocessingUpdatesReturn {
  start: () => void
  stop: () => void
}

export function usePreprocessingUpdates({
  projectId,
  files,
  historyFile,
  getFileStatus,
  fetchFiles,
  invalidateTaskCache,
}: UsePreprocessingUpdatesOptions): UsePreprocessingUpdatesReturn {
  let wsPreprocessingUnsubscribe: (() => void) | null = null
  const seenTaskIds = new Set<string | number>()

  let refreshDebounceTimer: ReturnType<typeof setTimeout> | null = null
  const REFRESH_DEBOUNCE_MS = 500 // Wait 500ms after last trigger before refetching

  const start = (): void => {
    wsPreprocessingUnsubscribe = websocketService.onPreprocessingUpdate((data) => {
      // Only update if the task belongs to this project
      if (!isForProject(data as WsPreprocessingUpdate, projectId.value)) return

      const update = data as WsPreprocessingUpdate

      // Check if this is a new task we haven't seen before
      const taskId = update.task_id
      const isNewTask = !seenTaskIds.has(taskId)
      if (taskId) {
        seenTaskIds.add(taskId)
      }

      // Check for terminal states via event field or status
      const isTerminalState =
        ['completed', 'failed', 'cancelled'].includes(String(update.event || '')) ||
        ['completed', 'failed', 'cancelled'].includes(String(update.status || '').toLowerCase())

      if (isTerminalState || isNewTask) {
        // Invalidate task cache immediately for terminal states to force fresh fetch
        if (isTerminalState) {
          invalidateTaskCache()
        }
        // Use debounced refresh to prevent rapid refetches when multiple tasks complete
        debouncedFetchFiles()
      } else {
        // For progress updates, merge the WebSocket data directly into files
        mergePreprocessingUpdate(update)
      }
    })
  }

  // Merge WebSocket preprocessing update into files array
  const mergePreprocessingUpdate = (data: WsPreprocessingUpdate): void => {
    const taskId = data.task_id
    if (!taskId) return

    // Find the file that has this task in its preprocessing_tasks
    const fileIndex = files.value.findIndex((f) =>
      f.preprocessing_tasks?.some((t) => t.id === taskId),
    )

    if (fileIndex >= 0) {
      const file = files.value[fileIndex]
      if (!file) return

      // Update historyFile first if this file is currently being shown
      const isHistoryFile = historyFile.value?.id === file.id

      const taskIndex = file.preprocessing_tasks.findIndex((t) => t.id === taskId)

      if (taskIndex >= 0) {
        // Merge the update into the existing task (shared id-fixup + meta-merge)
        const existingTask = file.preprocessing_tasks[taskIndex]
        const updatedTask = mergeWsEntity(
          existingTask as unknown as Record<string, unknown>,
          data as Record<string, unknown>,
          taskId,
          'task_id',
        ) as unknown as PreprocessingTask

        // Preserve and merge configuration
        if (data.configuration) {
          updatedTask.configuration =
            data.configuration as unknown as PreprocessingTask['configuration']
        }

        // Calculate progress percentage if not provided but we have the data
        const meta = updatedTask.meta ?? {}
        if (!meta.progress && (meta.total_files ?? 0) > 0) {
          const completed = meta.completed_files || 0
          const total = meta.total_files || 0
          updatedTask.meta = {
            ...meta,
            progress: total > 0 ? (completed / total) * 100 : 0,
          }
        } else if (
          !meta.progress &&
          updatedTask.processed_files > 0 &&
          updatedTask.total_files > 0
        ) {
          // Fallback: calculate from processed_files/total_files
          updatedTask.meta = {
            ...meta,
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

  const stop = (): void => {
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
  const debouncedFetchFiles = (): void => {
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
