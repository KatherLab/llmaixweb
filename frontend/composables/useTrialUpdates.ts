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
 * @param opts
 * @param opts.projectId
 * @param opts.trials
 * @param opts.resetAndFetch - refetch the full trial list (terminal / new trial case)
 * @returns {{ start: () => void, stop: () => void }}
 */
import type { Ref } from 'vue'
import { websocketService } from '@/services/websocket'
import { isForProject, mergeWsEntity } from '@/composables/useWsEntityUpdates'
import type { TrialSummary, WsTrialUpdate, WsMessage } from '@/types'

const TERMINAL_STATES = ['completed', 'failed', 'cancelled']
const REFRESH_DEBOUNCE_MS = 500 // Wait 500ms after last trigger before refetching

/** Options object passed to `useTrialUpdates`. */
interface UseTrialUpdatesOptions {
  projectId: Ref<string | number>
  trials: Ref<TrialSummary[]>
  /** Refetch the full trial list (terminal / new trial case). */
  resetAndFetch: () => void
}

/** Return type of `useTrialUpdates`. */
interface UseTrialUpdatesReturn {
  start: () => void
  stop: () => void
}

export function useTrialUpdates({
  projectId,
  trials,
  resetAndFetch,
}: UseTrialUpdatesOptions): UseTrialUpdatesReturn {
  let wsTrialUnsubscribe: (() => void) | null = null
  let wsConnectedUnsubscribe: (() => void) | null = null
  let refreshDebounceTimer: ReturnType<typeof setTimeout> | null = null

  const debouncedResetAndFetch = (): void => {
    if (refreshDebounceTimer) clearTimeout(refreshDebounceTimer)
    refreshDebounceTimer = setTimeout(() => {
      resetAndFetch()
      refreshDebounceTimer = null
    }, REFRESH_DEBOUNCE_MS)
  }

  const start = (): void => {
    wsTrialUnsubscribe = websocketService.onTrialUpdate((data) => {
      const update = data as WsTrialUpdate
      if (!isForProject(update as WsMessage, projectId.value)) return

      // Terminal state (via event or status) → authoritative server refetch.
      // This recovers `results_count`/`status` that the WS payload doesn't
      // carry reliably, and survives a missed terminal broadcast.
      const isTerminal =
        TERMINAL_STATES.includes(String(update.event || '')) ||
        TERMINAL_STATES.includes(String(update.status || '').toLowerCase())

      const idx = trials.value.findIndex((t) => t.id === update.trial_id)
      if (idx === -1) {
        // New trial not yet in the list → refetch (debounced).
        debouncedResetAndFetch()
        return
      }

      // Merge the update first so progress/status reflect immediately...
      trials.value[idx] = mergeWsEntity(
        trials.value[idx] as unknown as Record<string, unknown>,
        update as Record<string, unknown>,
        update.trial_id,
        'trial_id',
      ) as unknown as TrialSummary
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

  const stop = (): void => {
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
