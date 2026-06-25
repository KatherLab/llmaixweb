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

/**
 * Merge a WebSocket update payload into an existing entity object.
 *
 * - Spreads `data` over `existing`.
 * - Sets `id` to `idValue` and clears the WS-specific id field (`idKey`)
 *   so it doesn't leak into the entity shape.
 * - Deep-merges `data.meta` over `existing.meta` (preserving unrelated keys).
 *
 * @param {Object} existing - the current entity object
 * @param {Object} data     - the WS update payload
 * @param {*} idValue       - the canonical id to assign to `.id`
 * @param {string} [idKey='task_id'] - the WS payload field carrying the id (cleared after merge)
 * @returns {Object} the merged entity
 */
export function mergeWsEntity(existing, data, idValue, idKey = 'task_id') {
  const updated = {
    ...existing,
    ...data,
    id: idValue,
    [idKey]: undefined,
  }
  if (data.meta) {
    updated.meta = { ...(existing.meta || {}), ...data.meta }
  }
  return updated
}

/**
 * Returns true if the WS update belongs to the given project. Handles
 * string/number id comparison (the WS payload may send either).
 *
 * @param {Object} data - the WS update payload
 * @param {string|number} projectId
 * @returns {boolean}
 */
export function isForProject(data, projectId) {
  return String(data.project_id) === String(projectId)
}
