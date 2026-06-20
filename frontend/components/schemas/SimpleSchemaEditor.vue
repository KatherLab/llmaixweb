<template>
  <div class="simple-schema-editor flex flex-col h-full bg-white">
    <!-- Header -->
    <div class="border-b px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h3 class="text-base font-semibold text-gray-900">Extract Fields</h3>
        <p class="text-sm text-gray-500 mt-0.5">Drag to reorder • Click field to edit</p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-all hover:shadow"
        @click="addField"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        Add Field
      </button>
    </div>

    <!-- Fields List -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="fields.length === 0" class="text-center py-16">
        <div
          class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-50 mb-4"
        >
          <svg
            class="h-8 w-8 text-indigo-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <h4 class="text-lg font-medium text-gray-900 mb-1">No fields yet</h4>
        <p class="text-sm text-gray-500 mb-6">
          Add fields to define what information to extract from your documents
        </p>
        <button
          type="button"
          class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-all"
          @click="addField"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
          Add Your First Field
        </button>
      </div>

      <div v-else class="space-y-2">
        <!-- Read-only fields notice -->
        <div
          v-if="hasReadonlyFields"
          class="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800"
        >
          <svg class="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01M5 13l-1.5 7h15L17 13M5 13l1.5-7h11L19 13M5 13h14"
            />
          </svg>
          <span>
            Fields with nested groups, lists, or advanced settings are read-only here — edit them in
            <strong>Advanced mode</strong>.
          </span>
        </div>

        <div v-for="(field, index) in fields" :key="field.id">
          <!-- Read-only hint row (nested objects/arrays, enums, constraints, …) -->
          <div
            v-if="field.kind === 'readonly'"
            class="group flex items-center gap-3 p-3 rounded-xl border border-amber-200 bg-amber-50/60"
            :title="`Read-only — edit “${field.name}” in Advanced mode`"
          >
            <!-- Lock icon (in place of the drag handle) -->
            <div class="flex-shrink-0 p-2 text-amber-500 rounded-lg">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>

            <!-- Type badge -->
            <div
              class="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-amber-200 text-amber-800 text-[10px] font-semibold"
            >
              {{ readonlyTypeLabel(field) }}
            </div>

            <!-- Field name (read-only) -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-700 truncate">{{ field.name }}</p>
              <p v-if="field.description" class="text-xs text-gray-500 truncate">
                {{ field.description }}
              </p>
            </div>

            <!-- Hint to edit in Advanced mode -->
            <div class="flex-1 min-w-0 hidden lg:block">
              <p class="text-xs text-amber-700 truncate">Edit in Advanced mode</p>
            </div>

            <!-- Spacer to align with the editable rows' remove button -->
            <div class="flex-shrink-0 w-8"></div>
          </div>

          <!-- Editable row -->
          <div
            v-else
            :data-index="index"
            :class="[
              'group flex items-center gap-3 p-3 rounded-xl border transition-all duration-200',
              draggingIndex === index
                ? 'border-indigo-400 bg-indigo-50 shadow-md scale-[1.02]'
                : 'border-gray-200 hover:border-indigo-300 hover:shadow-sm bg-gray-50/50 hover:bg-white',
            ]"
            draggable
            @dragstart="handleDragStart"
            @dragend="handleDragEnd"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
            @drop="handleDrop"
          >
            <!-- Drag Handle -->
            <div
              class="flex-shrink-0 cursor-grab active:cursor-grabbing p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-200/50 transition-all"
              title="Drag to reorder"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 8h16M4 16h16"
                />
              </svg>
            </div>

            <!-- Field Number Badge -->
            <div
              :class="[
                'flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-xs font-semibold transition-all',
                draggingIndex === index
                  ? 'bg-indigo-200 text-indigo-800'
                  : 'bg-gray-200 text-gray-600',
              ]"
            >
              {{ index + 1 }}
            </div>

            <!-- Field Name Input -->
            <div class="flex-1 min-w-0">
              <input
                v-model="field.name"
                class="w-full bg-transparent border-0 border-b border-gray-300 focus:border-indigo-500 focus:ring-0 text-sm font-medium text-gray-900 placeholder-gray-400 transition-colors py-1.5"
                placeholder="field_name (e.g., patient_name)"
                @input="emitChange"
              />
            </div>

            <!-- Type Selector with Icon -->
            <div class="flex-shrink-0">
              <div class="relative">
                <select
                  v-model="field.type"
                  class="appearance-none bg-white border border-gray-300 hover:border-gray-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 rounded-lg text-sm font-medium py-2 pl-3 pr-8 cursor-pointer transition-all"
                  @change="emitChange"
                >
                  <option value="String">Text</option>
                  <option value="Number">Number</option>
                  <option value="Integer">Integer</option>
                  <option value="Boolean">Yes/No</option>
                  <option value="Date">Date</option>
                  <option value="DateTime">Date & Time</option>
                  <option value="Email">Email</option>
                </select>
                <svg
                  class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </div>
            </div>

            <!-- Description Input -->
            <div class="flex-1 min-w-0 hidden lg:block">
              <input
                v-model="field.description"
                class="w-full bg-transparent border-0 border-b border-gray-300 focus:border-indigo-500 focus:ring-0 text-xs text-gray-600 placeholder-gray-400 transition-colors py-1.5"
                placeholder="What is this field? (optional)"
                @input="emitChange"
              />
            </div>

            <!-- Remove Button -->
            <button
              type="button"
              class="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
              title="Remove field"
              @click="removeField(field.id)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Help Footer -->
    <div
      v-if="fields.length > 0"
      class="border-t px-6 py-4 bg-gradient-to-r from-indigo-50 to-purple-50"
    >
      <div class="flex items-start gap-3">
        <div
          class="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center mt-0.5"
        >
          <svg class="h-3 w-3 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
        <div class="text-sm text-indigo-900">
          <p class="font-medium mb-1.5">Quick Tips</p>
          <ul class="space-y-1 text-indigo-700">
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-indigo-400"></span>
              Use clear names like
              <code class="px-1.5 py-0.5 bg-white/60 rounded text-xs font-mono">patient_name</code>
              or
              <code class="px-1.5 py-0.5 bg-white/60 rounded text-xs font-mono">date_of_birth</code>
            </li>
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-indigo-400"></span>
              The schema is automatically included in the prompt sent to the LLM
            </li>
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-indigo-400"></span>
              Need nested objects or arrays? Switch to <strong>Advanced Mode</strong>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  schema: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:schema'])

// Internal field storage with unique IDs
const fields = ref([])
const draggingIndex = ref(-1)
const dragOverIndex = ref(-1)
const isInternalChange = ref(false)

// Last schema received from the parent (external). Kept so `buildSchema` can
// preserve root-level keys (e.g. `required`, `additionalProperties`) and any
// read-only properties verbatim, instead of rebuilding the whole schema from
// only the editable fields (which would silently drop advanced features).
const originalSchema = ref(null)

// Generate unique ID
let fieldIdCounter = 0
const generateId = () => `field_${Date.now()}_${fieldIdCounter++}`

// Type mapping: Simple type → JSON Schema type + format
const typeMapping = {
  String: { type: 'string' },
  Text: { type: 'string' },
  Number: { type: 'number' },
  Integer: { type: 'integer' },
  Float: { type: 'number' },
  Boolean: { type: 'boolean' },
  Date: { type: 'string', format: 'date' },
  Time: { type: 'string', format: 'time' },
  DateTime: { type: 'string', format: 'date-time' },
  Email: { type: 'string', format: 'email' },
}

// Types and formats the simple editor can represent losslessly. Anything else
// (nested objects/arrays, enums, constraints, unknown formats…) is shown as a
// read-only hint and passed through untouched on rebuild.
const SIMPLE_TYPES = ['string', 'number', 'integer', 'boolean']
const KNOWN_FORMATS = ['date', 'time', 'date-time', 'email']

const isSimpleEditable = (propSchema) => {
  if (!propSchema || !SIMPLE_TYPES.includes(propSchema.type)) return false
  const allowedKeys = new Set(['type', 'title', 'description', 'format'])
  for (const key of Object.keys(propSchema)) {
    if (!allowedKeys.has(key)) return false
  }
  if (propSchema.format && !KNOWN_FORMATS.includes(propSchema.format)) return false
  return true
}

// Human-readable label for a read-only property's type
const readonlyTypeLabel = (field) => {
  const t = field.rawSchema?.type
  if (t === 'object') return 'Group'
  if (t === 'array') return 'List'
  if (t === 'string') return 'Text'
  if (t === 'number') return 'Number'
  if (t === 'integer') return 'Integer'
  if (t === 'boolean') return 'Yes/No'
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : 'Advanced'
}

const hasReadonlyFields = computed(() => fields.value.some((f) => f.kind === 'readonly'))

// Convert JSON Schema → Simple fields
const parseSchema = (schema) => {
  const parsedFields = []
  const props = schema?.properties || {}

  for (const [name, propSchema] of Object.entries(props)) {
    if (isSimpleEditable(propSchema)) {
      // Find matching simple type
      let matchedType = 'String'
      for (const [simpleType, jsonSchema] of Object.entries(typeMapping)) {
        if (propSchema.type === jsonSchema.type && propSchema.format === jsonSchema.format) {
          matchedType = simpleType
          break
        }
      }

      // Special case: string with format
      if (propSchema.type === 'string' && propSchema.format) {
        if (propSchema.format === 'email') matchedType = 'Email'
        else if (propSchema.format === 'date') matchedType = 'Date'
        else if (propSchema.format === 'time') matchedType = 'Time'
        else if (propSchema.format === 'date-time') matchedType = 'DateTime'
      }

      parsedFields.push({
        id: generateId(),
        kind: 'simple',
        name,
        type: matchedType,
        description: propSchema.description || '',
      })
    } else {
      // Nested objects/arrays and anything the simple editor can't represent
      // losslessly become read-only hints, preserved verbatim on rebuild.
      parsedFields.push({
        id: generateId(),
        kind: 'readonly',
        name,
        description: propSchema.description || '',
        rawSchema: propSchema,
      })
    }
  }

  return parsedFields
}

// Convert Simple fields → JSON Schema.
// Rebuilds editable fields from scratch but preserves read-only (advanced)
// properties and root-level keys verbatim, so editing simple fields never
// drops nested structures, `required`, etc.
const buildSchema = () => {
  const schema = originalSchema.value
    ? JSON.parse(JSON.stringify(originalSchema.value))
    : { type: 'object' }
  if (!schema.type) schema.type = 'object'

  const properties = {}

  for (const field of fields.value) {
    if (!field.name || !field.name.trim()) continue

    if (field.kind === 'readonly') {
      properties[field.name.trim()] = JSON.parse(JSON.stringify(field.rawSchema))
      continue
    }

    const mapping = typeMapping[field.type] || typeMapping.String
    const propSchema = {
      type: mapping.type,
      title: field.name
        .trim()
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (l) => l.toUpperCase()),
    }

    if (mapping.format) {
      propSchema.format = mapping.format
    }

    if (field.description && field.description.trim()) {
      propSchema.description = field.description.trim()
    }

    properties[field.name.trim()] = propSchema
  }

  schema.properties = properties

  // Drop `required` entries for properties that no longer exist
  if (Array.isArray(schema.required)) {
    schema.required = schema.required.filter((name) =>
      Object.prototype.hasOwnProperty.call(properties, name),
    )
    if (schema.required.length === 0) {
      delete schema.required
    }
  }

  return schema
}

// Emit schema change
const emitChange = () => {
  isInternalChange.value = true
  const schema = buildSchema()
  emit('update:schema', schema)
}

// Add new field
const addField = () => {
  fields.value.push({
    id: generateId(),
    kind: 'simple',
    name: '',
    type: 'String',
    description: '',
  })
  emitChange()
}

// Remove field
const removeField = (id) => {
  fields.value = fields.value.filter((f) => f.id !== id)
  emitChange()
}

// Drag and Drop handlers
const handleDragStart = (e) => {
  draggingIndex.value = parseInt(e.target.dataset.index)
  e.target.style.opacity = '0.5'
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', draggingIndex.value)
}

const handleDragEnd = (e) => {
  e.target.style.opacity = '1'
  draggingIndex.value = -1
  dragOverIndex.value = -1
}

const handleDragOver = (e) => {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
  const currentIndex = parseInt(e.currentTarget.dataset.index)
  if (currentIndex !== draggingIndex.value) {
    dragOverIndex.value = currentIndex
  }
}

const handleDragLeave = () => {
  dragOverIndex.value = -1
}

const handleDrop = (e) => {
  e.preventDefault()
  const fromIndex = draggingIndex.value
  const toIndex = parseInt(e.currentTarget.dataset.index)

  if (fromIndex !== toIndex && fromIndex >= 0 && toIndex >= 0) {
    const newFields = [...fields.value]
    const [removed] = newFields.splice(fromIndex, 1)
    newFields.splice(toIndex, 0, removed)
    fields.value = newFields
    emitChange()
  }

  dragOverIndex.value = -1
}

// Watch for external schema changes (not from internal updates).
// The field list always mirrors `props.schema`, including an empty
// schema (so deletions made elsewhere are reflected here). Starter
// fields for new schemas are seeded by the parent, not on mount.
watch(
  () => props.schema,
  (newSchema) => {
    // Skip if this change came from our own emit
    if (isInternalChange.value) {
      isInternalChange.value = false
      return
    }
    if (newSchema && Object.keys(newSchema).length > 0) {
      originalSchema.value = newSchema
      fields.value = parseSchema(newSchema)
    }
  },
  { deep: true, immediate: true },
)
</script>

<style scoped>
.simple-schema-editor {
  font-family: inherit;
}

input[type='text'],
select {
  transition: all 0.15s ease-in-out;
}

input[type='text']:focus,
select:focus {
  outline: none;
}

/* Custom scrollbar for webkit */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>
