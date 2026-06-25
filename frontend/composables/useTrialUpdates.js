/**
 * WebSocket subscription for trial updates.
 *
 * Extracted from TrialsManagement.vue. Subscribes to trial updates via the shared
 * websocketService, filters to the current project, and either:
 *   - merges the update directly into the trials array (existing trial), or
 *   - triggers a full refetch (new trial not yet in the list).
 *
 * Preserves the original merge fixup, project-id filtering, and meta-object
 * merge (now shared via useWsEntityUpdates helpers).
 *
 * @param {Object} opts
 * @param {import('vue').Ref<string|number>} opts.projectId
 * @param {import('vue').Ref<Array>} opts.trials
 * @param {() => void} opts.resetAndFetch - refetch the full trial list (new trial case)
 * @returns {{ start: () => void, stop: () => void }}
 */
import { websocketService } from '@/services/websocket.js'
import { isForProject, mergeWsEntity } from '@/composables/useWsEntityUpdates'

export function useTrialUpdates({ projectId, trials, resetAndFetch }) {
  let wsTrialUnsubscribe = null

  const start = () => {
    wsTrialUnsubscribe = websocketService.onTrialUpdate((data) => {
      if (!isForProject(data, projectId.value)) return

      const idx = trials.value.findIndex((t) => t.id === data.trial_id)
      if (idx !== -1) {
        trials.value[idx] = mergeWsEntity(trials.value[idx], data, data.trial_id, 'trial_id')
        // Trigger reactivity
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
