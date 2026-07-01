import type { ISODateString } from './api'

export interface Prompt {
  id: number
  project_id: number
  name: string | null
  description: string | null
  system_prompt: string | null
  user_prompt: string | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface PromptCreate {
  name: string
  project_id: number
  description?: string | null
  system_prompt?: string | null
  user_prompt?: string | null
}

export interface PromptUpdate {
  name?: string | null
  description?: string | null
  system_prompt?: string | null
  user_prompt?: string | null
}
