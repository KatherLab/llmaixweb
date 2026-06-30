/**
 * WebSocket subscription for trial updates.
 *
 * Subscribes to trial updates via the shared websocketService, filters to the
 * current project, and either:
 *   - merges progress updates directly into the trials array (in-flight trial), or
 *   - triggers a debounced full refetch on terminal states (completed/failed/
 *     cancelled) and for brand-new trials not yet in the list.
 *
 * The debounced refetch on terminal states mirrors `usePreprocessingUpdates` and
 * is what makes the table reliable: the WS payload carries `docs_done` (not
 * `results_count`, which the table badge reads) and a single terminal broadcast
 * can be missed (WS drop / Redis pub/sub blip). Refetching from the server on
 * completion guarantees authoritative `status` + `results_count`.
 *
 * @param {Object} opts
 * @param {import('vue').Ref<string|number>} opts.projectId
 * @param {import('vue').Ref<Array>} opts.trials
 * @param {() => void} opts.resetAndFetch - refetch the full trial list (terminal / new trial case)
 * @returns {{ start: () => void, stop: () => void }}
 */
import { websocketService } from '@/services/websocket.js'
import { isForProject, mergeWsEntity } from '@/composables/useWsEntityUpdates'

const TERMINAL_STATES = ['completed', 'failed', 'cancelled']
const REFRESH_DEBOUNCE_MS = 500 // Wait 500ms after last trigger before refetching

export function useTrialUpdates({ projectId, trials, resetAndFetch }) {
  let wsTrialUnsubscribe = null
  let wsConnectedUnsubscribe = null
  let refreshDebounceTimer = null

  const debouncedResetAndFetch = () => {
    if (refreshDebounceTimer) clearTimeout(refreshDebounceTimer)
    refreshDebounceTimer = setTimeout(() => {
      resetAndFetch()
      refreshDebounceTimer = null
    }, REFRESH_DEBOUNCE_MS)
  }

  const start = () => {
    wsTrialUnsubscribe = websocketService.onTrialUpdate((data) => {
      if (!isForProject(data, projectId.value)) return

      // Terminal state (via event or status) → authoritative server refetch.
      // This recovers `results_count`/`status` that the WS payload doesn't
      // carry reliably, and survives a missed terminal broadcast.
      const isTerminal =
        TERMINAL_STATES.includes(String(data.event || '')) ||
        TERMINAL_STATES.includes(String(data.status || '').toLowerCase())

      const idx = trials.value.findIndex((t) => t.id === data.trial_id)
      if (idx === -1) {
        // New trial not yet in the list → refetch (debounced).
        debouncedResetAndFetch()
        return
      }

      // Merge the update first so progress/status reflect immediately...
      trials.value[idx] = mergeWsEntity(trials.value[idx], data, data.trial_id, 'trial_id')
      trials.value = [...trials.value]

      // ...then, for terminal states, also refetch to reconcile fields the
      // payload doesn't carry (e.g. results_count).
      if (isTerminal) {
        debouncedResetAndFetch()
      }
    })

    // Resync after a WS reconnect — any updates emitted while disconnected
    // were missed, so pull the authoritative list.
    wsConnectedUnsubscribe = websocketService.subscribe('connected', () => {
      debouncedResetAndFetch()
    })
  }

  const stop = () => {
    if (wsTrialUnsubscribe) {
      wsTrialUnsubscribe()
      wsTrialUnsubscribe = null
    }
    if (wsConnectedUnsubscribe) {
      wsConnectedUnsubscribe()
      wsConnectedUnsubscribe = null
    }
    if (refreshDebounceTimer) {
      clearTimeout(refreshDebounceTimer)
      refreshDebounceTimer = null
    }
  }

  return { start, stop }
}
