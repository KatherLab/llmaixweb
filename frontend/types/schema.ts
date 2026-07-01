import type { ISODateString } from './api'
import type { FieldType } from './enums'

/**
 * A JSON-schema-style extraction schema definition. Stored as a free-form
 * JSON object on the backend; the frontend's schema editors read/write the
 * `type`/`properties`/`items`/`required` keys.
 */
export type SchemaDefinition = Record<string, unknown> & {
  type?: string
  properties?: Record<string, SchemaProperty>
  items?: SchemaProperty
  required?: string[]
}

/** A node in the visual schema tree editor. */
export interface SchemaProperty {
  type: FieldType | string
  name?: string
  description?: string
  properties?: Record<string, SchemaProperty>
  items?: SchemaProperty
  required?: string[]
  enum?: unknown[]
  default?: unknown
  [key: string]: unknown
}

export interface Schema {
  id: number
  project_id: number
  schema_name: string | null
  schema_definition: SchemaDefinition | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface SchemaCreate {
  schema_name: string
  schema_definition: SchemaDefinition
}

export interface SchemaUpdate {
  schema_name?: string | null
  schema_definition?: SchemaDefinition | null
}

/** Response for `GET /schema/{id}/field-types`. */
export interface SchemaFieldTypes {
  [fieldName: string]: FieldType | string
}
