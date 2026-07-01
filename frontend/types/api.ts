/**
 * Shared API response shape helpers.
 *
 * Backend Pydantic response models serialize `datetime` as ISO 8601 strings,
 * so all date/time fields are typed as `string` on the frontend.
 */
import type { AxiosResponse } from 'axios'

/** ISO 8601 datetime string, as serialized by Pydantic. */
export type ISODateString = string

/** A standard JSON API response body. */
export type ApiBody<T> = AxiosResponse<T>

/** A response whose body is a binary Blob (downloads). */
export type BlobResponse = AxiosResponse<Blob>

/** Generic paginated list envelope. */
export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** Loose query-param objects passed to axios `{ params }`. */
export type QueryParams = Record<string, unknown>

/** Loose request-body objects. */
export type RequestBody = Record<string, unknown>
