<template>
  <div class="simple-schema-editor flex flex-col h-full bg-white">
    <!-- Header -->
    <div class="border-b px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h3 class="text-base font-semibold text-slate-900">Extract Fields</h3>
        <p class="text-sm text-slate-500 mt-0.5">Drag to reorder • Click field to edit</p>
      </div>
      <BaseButton class="shadow-sm hover:shadow" @click="addField">
        <Plus class="h-4 w-4" />
        Add Field
      </BaseButton>
    </div>

    <!-- Fields List -->
    <div class="flex-1 overflow-y-auto p-6">
      <EmptyState
        v-if="fields.length === 0"
        title="No fields yet"
        description="Add fields to define what information to extract from your documents"
      >
        <template #action>
          <BaseButton class="shadow-sm" @click="addField">
            <Plus class="h-4 w-4" aria-hidden="true" />
            Add Your First Field
          </BaseButton>
        </template>
      </EmptyState>

      <div v-else class="space-y-2">
        <!-- Read-only fields notice -->
        <div
          v-if="hasReadonlyFields"
          class="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800"
        >
          <ShieldAlert class="h-4 w-4 flex-shrink-0" />
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
              <Lock class="h-5 w-5" />
            </div>

            <!-- Type badge -->
            <div
              class="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-amber-200 text-amber-800 text-[10px] font-semibold"
            >
              {{ readonlyTypeLabel(field) }}
            </div>

            <!-- Field name (read-only) -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-slate-700 truncate">{{ field.name }}</p>
              <p v-if="field.description" class="text-xs text-slate-500 truncate">
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
                ? 'border-blue-400 bg-blue-50 shadow-md scale-[1.02]'
                : 'border-slate-200 hover:border-blue-300 hover:shadow-sm bg-slate-50/50 hover:bg-white',
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
              class="flex-shrink-0 cursor-grab active:cursor-grabbing p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50 transition-all"
              title="Drag to reorder"
            >
              <GripVertical class="h-5 w-5" />
            </div>

            <!-- Field Number Badge -->
            <div
              :class="[
                'flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-xs font-semibold transition-all',
                draggingIndex === index
                  ? 'bg-blue-200 text-blue-800'
                  : 'bg-slate-200 text-slate-600',
              ]"
            >
              {{ index + 1 }}
            </div>

            <!-- Field Name Input -->
            <div class="flex-1 min-w-0">
              <input
                v-model="field.name"
                class="w-full bg-transparent border-0 border-b border-slate-300 focus:border-blue-500 focus:ring-0 text-sm font-medium text-slate-900 placeholder-slate-400 transition-colors py-1.5"
                placeholder="field_name (e.g., patient_name)"
                @input="emitChange"
              />
            </div>

            <!-- Type Selector with Icon -->
            <div class="flex-shrink-0">
              <div class="relative">
                <select
                  v-model="field.type"
                  class="appearance-none bg-white border border-slate-300 hover:border-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 rounded-lg text-sm font-medium py-2 pl-3 pr-8 cursor-pointer transition-all"
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
                <ChevronDown
                  class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
                />
              </div>
            </div>

            <!-- Description Input -->
            <div class="flex-1 min-w-0 hidden lg:block">
              <input
                v-model="field.description"
                class="w-full bg-transparent border-0 border-b border-slate-300 focus:border-blue-500 focus:ring-0 text-xs text-slate-600 placeholder-slate-400 transition-colors py-1.5"
                placeholder="What is this field? (optional)"
                @input="emitChange"
              />
            </div>

            <!-- Remove Button -->
            <BaseButton
              variant="icon"
              tone="red"
              class="flex-shrink-0 p-2 opacity-0 group-hover:opacity-100"
              title="Remove field"
              aria-label="Remove field"
              @click="removeField(field.id)"
            >
              <Trash2 class="h-4 w-4" aria-hidden="true" />
            </BaseButton>
          </div>
        </div>
      </div>
    </div>

    <!-- Help Footer -->
    <div
      v-if="fields.length > 0"
      class="border-t px-6 py-4 bg-gradient-to-r from-blue-50 to-purple-50"
    >
      <div class="flex items-start gap-3">
        <div
          class="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center mt-0.5"
        >
          <Info class="h-3 w-3 text-blue-600" />
        </div>
        <div class="text-sm text-blue-900">
          <p class="font-medium mb-1.5">Quick Tips</p>
          <ul class="space-y-1 text-blue-700">
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-blue-400"></span>
              Use clear names like
              <code class="px-1.5 py-0.5 bg-white/60 rounded text-xs font-mono">patient_name</code>
              or
              <code class="px-1.5 py-0.5 bg-white/60 rounded text-xs font-mono">date_of_birth</code>
            </li>
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-blue-400"></span>
              The schema is automatically included in the prompt sent to the LLM
            </li>
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-blue-400"></span>
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
import { ChevronDown, GripVertical, Info, Lock, Plus, ShieldAlert, Trash2 } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import EmptyState from '@/components/common/EmptyState.vue'

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
