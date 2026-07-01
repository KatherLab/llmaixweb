/**
 * Shared WebSocket entity-update merge helpers.
 *
 * The preprocessing and trial update composables both:
 *   - filter incoming WS messages by project_id,
 *   - find an existing entity by id and merge the payload into it (fixing the
 *     id field and deep-merging the `meta` object), and
 *   - trigger array reactivity.
 *
 * These helpers factor that shared logic out so the two consumers don't
 * copy-paste the merge-fixup / meta-merge / reactivity-trigger code.
 */
import type { WsMessage } from '@/types'

/**
 * Merge a WebSocket update payload into an existing entity object.
 *
 * - Spreads `data` over `existing`.
 * - Sets `id` to `idValue` and clears the WS-specific id field (`idKey`)
 *   so it doesn't leak into the entity shape.
 * - Deep-merges `data.meta` over `existing.meta` (preserving unrelated keys).
 *
 * @param existing - the current entity object
 * @param data     - the WS update payload
 * @param idValue  - the canonical id to assign to `.id`
 * @param idKey    - the WS payload field carrying the id (cleared after merge)
 * @returns the merged entity
 */
export function mergeWsEntity<T extends Record<string, unknown>>(
  existing: T,
  data: Partial<T> & Record<string, unknown>,
  idValue: string | number,
  idKey = 'task_id',
): T {
  const updated = {
    ...existing,
    ...data,
    id: idValue,
    [idKey]: undefined,
  } as T
  const dataMeta = (data as Record<string, unknown>).meta as Record<string, unknown> | undefined
  if (dataMeta) {
    const existingMeta = (existing as Record<string, unknown>).meta as
      Record<string, unknown> | undefined
    ;(updated as Record<string, unknown>).meta = { ...(existingMeta || {}), ...dataMeta }
  }
  return updated
}

/**
 * Returns true if the WS update belongs to the given project. Handles
 * string/number id comparison (the WS payload may send either).
 *
 * @param data - the WS update payload
 * @param projectId
 */
export function isForProject(data: WsMessage, projectId: string | number): boolean {
  return String(data.project_id) === String(projectId)
}
