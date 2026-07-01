import type { ISODateString } from './api'
import type { ProjectStatus } from './enums'
import type { UserPublic } from './user'
import type { Document } from './document'

export interface Project {
  id: number
  name: string | null
  description: string | null
  status: ProjectStatus | null
  owner_id: number | null
  owner: UserPublic | null
  /** Excluded on the list endpoint via response_model_exclude. */
  documents?: Document[]
  document_count: number
  created_at: ISODateString
  updated_at: ISODateString
}

export interface ProjectCreate {
  name: string
  description?: string | null
  status?: ProjectStatus | null
  owner_id?: number | null
}

export interface ProjectUpdate {
  name?: string | null
  description?: string | null
  status?: ProjectStatus | null
  owner_id?: number | null
}
