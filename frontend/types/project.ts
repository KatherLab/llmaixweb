import type { ISODateString } from './api'
import type { ProjectStatus } from './enums'
import type { UserPublic } from './user'
import type { Document } from './document'

/** What a collaborator may do with a project shared with them. */
export type ProjectPermission = 'read' | 'write'

/**
 * What the *requesting* user may do with a project: `owner` (they own it, or
 * are an admin with global project access), or the permission of the share
 * granted to them. Only the owner may delete the project or manage its shares.
 */
export type ProjectAccessLevel = 'owner' | ProjectPermission

export interface Project {
  id: number
  name: string | null
  description: string | null
  status: ProjectStatus | null
  owner_id: number | null
  owner: UserPublic | null
  /** Access the requesting user holds — drives which actions the UI offers. */
  access_level: ProjectAccessLevel
  /** Collaborators the project is shared with (the owner is not counted). */
  share_count: number
  /** Excluded on the list endpoint via response_model_exclude. */
  documents?: Document[]
  document_count: number
  /** Aggregate counts driving the project workflow progression cue. */
  file_count: number
  schema_count: number
  prompt_count: number
  trial_count: number
  evaluation_count: number
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

/** A standing grant of access to a project for a user who does not own it. */
export interface ProjectShare {
  id: number
  project_id: number
  user: UserPublic
  permission: ProjectPermission
  /** Who granted the share; null once that user has been deleted. */
  created_by: UserPublic | null
  created_at: ISODateString
  updated_at: ISODateString
}

/**
 * Collaborators are addressed by email: listing users is admin-only, so a
 * non-admin owner has no user directory to pick from.
 */
export interface ProjectShareCreate {
  email: string
  permission: ProjectPermission
}

export interface ProjectShareUpdate {
  permission: ProjectPermission
}
