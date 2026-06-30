/**
 * Flatten a JSON-schema definition into a friendly, display-ready field list.
 *
 * Used by the schema view modal, the schema list expanded row, and the trial
 * schema-select preview — so non-technical users see field names + types instead
 * of raw `{"type":"object","properties":{...}}` JSON.
 *
 * Each entry: { path, name, type, description, required, format, enum, depth }
 *  - path:   dot/`[]`-separated path (e.g. `patient.medications[].name`)
 *  - name:   the final path segment, pretty-printed when no `title` is set
 *  - type:   canonical JSON-schema type ('string'|'number'|'integer'|'boolean'|
 *            'object'|'array'), falling back to 'any' when absent
 *  - depth:  nesting depth (0 = top-level), for indentation
 */

/** Human-readable label for a raw field key (snake_case → "Snake Case"). */
function prettifyName(key) {
  if (!key) return ''
  // Handle dot/bracket path segments — only prettify the final segment.
  const last =
    String(key)
      .split(/[.[\]]/)
      .filter(Boolean)
      .pop() || key
  return last
    .replace(/[_-]+/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function typeOf(def) {
  if (!def || typeof def !== 'object') return 'any'
  if (Array.isArray(def.type)) return def.type.find((t) => t !== 'null') || def.type[0] || 'any'
  if (def.type) return def.type
  // Infer from shape when `type` is omitted (common in real schemas).
  if (def.properties) return 'object'
  if (def.items) return 'array'
  if (def.enum) return 'string'
  return 'any'
}

/**
 * Recursively walk a schema definition, collecting fields.
 * @param {object} def   - the JSON-schema node (e.g. schema_definition)
 * @param {string} prefix - current dot-path (no trailing separator)
 * @param {number} depth  - current nesting depth
 * @param {string[]} requiredAncestors - paths known to be required (for parent objects)
 * @returns {object[]}
 */
function walk(def, prefix, depth, requiredAncestors) {
  const fields = []
  if (!def || typeof def !== 'object') return fields

  const props = def.properties || {}
  const required = Array.isArray(def.required) ? def.required : []

  for (const [key, child] of Object.entries(props)) {
    const path = prefix ? `${prefix}.${key}` : key
    const type = typeOf(child)
    const isRequired = required.includes(key)
    const title = child && child.title
    const name = title || prettifyName(key)

    fields.push({
      path,
      name,
      type,
      description: child?.description || '',
      required: isRequired,
      format: child?.format || '',
      enum: Array.isArray(child?.enum) ? child.enum : [],
      depth,
    })

    if (type === 'object' && child?.properties) {
      fields.push(...walk(child, path, depth + 1, requiredAncestors))
    } else if (type === 'array' && child?.items) {
      // Represent array items as a nested group under `path[]`.
      const itemPath = `${path}[]`
      const itemType = typeOf(child.items)
      fields.push({
        path: itemPath,
        name: `${name} (list items)`,
        type: itemType,
        description: child.items?.description || child?.description || '',
        required: false,
        format: child.items?.format || '',
        enum: Array.isArray(child.items?.enum) ? child.items.enum : [],
        depth: depth + 1,
      })
      if (itemType === 'object' && child.items?.properties) {
        fields.push(...walk(child.items, itemPath, depth + 2, requiredAncestors))
      }
    }
  }

  return fields
}

/**
 * Flatten a full schema definition into a display-ready field list.
 * @param {object|string} schemaDefinition - the `schema_definition` object (or JSON string)
 * @returns {object[]} flat list of field entries
 */
export function flattenSchemaFields(schemaDefinition) {
  let schema = schemaDefinition
  if (typeof schema === 'string') {
    try {
      schema = JSON.parse(schema)
    } catch {
      return []
    }
  }
  if (!schema || typeof schema !== 'object') return []
  return walk(schema, '', 0, [])
}

/**
 * A one-line summary of a schema for compact previews, e.g.
 * "3 fields: Patient Name, Date Of Birth, Medical Record Number"
 * @param {object|string} schemaDefinition
 * @param {number} [maxNames=5] - max field names to list before "…"
 * @returns {string}
 */
export function summarizeSchema(schemaDefinition, maxNames = 5) {
  const fields = flattenSchemaFields(schemaDefinition)
  const top = fields.filter((f) => f.depth === 0)
  if (top.length === 0) return 'No fields defined'
  const shown = top.slice(0, maxNames).map((f) => f.name)
  const more = top.length > maxNames ? `, +${top.length - maxNames} more` : ''
  return `${top.length} field${top.length === 1 ? '' : 's'}: ${shown.join(', ')}${more}`
}
