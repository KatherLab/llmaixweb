/**
 * WebSocket subscription for trial updates.
 *
 * Extracted from TrialsManagement.vue. Subscribes to trial updates via the shared
 * websocketService, filters to the current project, and either:
 *   - merges the update directly into the trials array (existing trial), or
 *   - triggers a full refetch (new trial not yet in the list).
 *
 * Preserves the original merge fixup ({ ...existing, ...data, id: data.trial_id }),
 * project-id filtering, and meta-object merge from the inline WebSocket code.
 *
 * @param {Object} opts
 * @param {import('vue').Ref<string|number>} opts.projectId
 * @param {import('vue').Ref<Array>} opts.trials
 * @param {() => void} opts.resetAndFetch - refetch the full trial list (new trial case)
 * @returns {{ start: () => void, stop: () => void }}
 */
import { websocketService } from '@/services/websocket.js'

export function useTrialUpdates({ projectId, trials, resetAndFetch }) {
  let wsTrialUnsubscribe = null

  const start = () => {
    wsTrialUnsubscribe = websocketService.onTrialUpdate((data) => {
      // Only update if the trial belongs to this project (handle string/number comparison)
      if (String(data.project_id) !== String(projectId.value)) return

      // Update the trial in the list
      const idx = trials.value.findIndex((t) => t.id === data.trial_id)
      if (idx !== -1) {
        const existingTrial = trials.value[idx]
        const updatedTrial = {
          ...existingTrial,
          ...data,
          id: data.trial_id,
          trial_id: undefined,
        }

        // Preserve and merge meta object
        if (data.meta) {
          updatedTrial.meta = { ...(existingTrial.meta || {}), ...data.meta }
        }

        // Trigger reactivity
        trials.value[idx] = updatedTrial
        trials.value = [...trials.value]
      } else {
        // New trial - fetch full list
        resetAndFetch()
      }
    })
  }

  const stop = () => {
    if (wsTrialUnsubscribe) {
      wsTrialUnsubscribe()
      wsTrialUnsubscribe = null
    }
  }

  return { start, stop }
}
