import type { PreprocessingStatus, TrialStatus } from './enums'

/** Base shape of any WebSocket activity message broadcast by the backend. */
export interface WsMessage {
  type: string
  project_id?: string | number
  [key: string]: unknown
}

/**
 * `preprocessing_update` message. Field names mirror the backend broadcast
 * payload (celery/task_signals.py, utils/preprocessing.py, celery/preprocessing.py)
 * exactly — the merge composables spread the raw payload, so a mismatched name
 * (e.g. the old `skipped_files`) would silently never update.
 */
export interface WsPreprocessingUpdate extends WsMessage {
  type: 'preprocessing_update'
  task_id: number | string
  status?: PreprocessingStatus | string
  project_id: string | number
  /** Present only on the celery/preprocessing.py completion broadcast. */
  configuration?: Record<string, unknown> | null
  configuration_name?: string | null
  meta?: Record<string, unknown> | null
  processed_files?: number
  total_files?: number
  failed_files?: number
  /** The backend field is `cancelled_files` (task.skipped_files under the hood). */
  cancelled_files?: number
  /** Lifecycle event tag, e.g. 'started' | 'progress' | 'completed' | 'failed'. */
  event?: string
  [key: string]: unknown
}

/** `trial_update` message. */
export interface WsTrialUpdate extends WsMessage {
  type: 'trial_update'
  trial_id: number | string
  status?: TrialStatus | string
  project_id: string | number
  docs_done?: number
  progress?: number
  meta?: Record<string, unknown> | null
  /** Per-project sequence number; present on created/progress broadcasts. */
  project_trial_number?: number
  [key: string]: unknown
}

export type WsEventType =
  | 'preprocessing_update'
  | 'trial_update'
  | 'connected'
  | 'disconnected'
  | 'error'
  | 'message'
  | 'maxReconnectAttemptsReached'

export type WsListener = (data: WsMessage) => void
