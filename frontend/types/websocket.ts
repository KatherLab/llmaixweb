import type { PreprocessingStatus, TrialStatus } from './enums'

/** Base shape of any WebSocket activity message broadcast by the backend. */
export interface WsMessage {
  type: string
  project_id?: string | number
  [key: string]: unknown
}

/** `preprocessing_update` message. */
export interface WsPreprocessingUpdate extends WsMessage {
  type: 'preprocessing_update'
  task_id: number | string
  status?: PreprocessingStatus | string
  project_id: string | number
  configuration?: Record<string, unknown> | null
  meta?: Record<string, unknown> | null
  processed_files?: number
  total_files?: number
  failed_files?: number
  skipped_files?: number
  message?: string | null
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
