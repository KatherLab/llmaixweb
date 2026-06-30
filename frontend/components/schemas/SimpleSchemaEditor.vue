<template>
  <div class="simple-schema-editor flex flex-col h-full bg-white dark:bg-slate-900">
    <!-- Header -->
    <div class="border-b px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h3 class="text-base font-semibold text-slate-900 dark:text-slate-100">Extract Fields</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Drag to reorder • Click field to edit
        </p>
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
          class="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300"
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
            class="group flex items-center gap-3 p-3 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50/60 dark:bg-amber-900/20"
            :title="`Read-only — edit “${field.name}” in Advanced mode`"
          >
            <!-- Lock icon (in place of the drag handle) -->
            <div class="flex-shrink-0 p-2 text-amber-500 rounded-lg">
              <Lock class="h-5 w-5" />
            </div>

            <!-- Type badge -->
            <div
              class="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-amber-200 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 text-[10px] font-semibold"
            >
              {{ readonlyTypeLabel(field) }}
            </div>

            <!-- Field name (read-only) -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
                {{ field.name }}
              </p>
              <p
                v-if="field.description"
                class="text-xs text-slate-500 dark:text-slate-400 truncate"
              >
                {{ field.description }}
              </p>
            </div>

            <!-- Hint to edit in Advanced mode -->
            <div class="flex-1 min-w-0 hidden lg:block">
              <p class="text-xs text-amber-700 dark:text-amber-400 truncate">
                Edit in Advanced mode
              </p>
            </div>

            <!-- Spacer to align with the editable rows' remove button -->
            <div class="flex-shrink-0 w-8"></div>
          </div>

          <!-- Editable row -->
          <div
            v-else
            :data-index="index"
            :class="[
              'group flex flex-wrap items-center gap-3 p-3 rounded-xl border transition-all duration-200',
              draggingIndex === index
                ? 'border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-900/30 shadow-md scale-[1.02]'
                : 'border-slate-200 dark:border-slate-700 hover:border-blue-300 hover:shadow-sm bg-slate-50/50 dark:bg-slate-800/50 hover:bg-white dark:hover:bg-slate-800',
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
              class="flex-shrink-0 cursor-grab active:cursor-grabbing p-2 text-slate-400 hover:text-slate-600 dark:hover:bg-slate-700 rounded-lg hover:bg-slate-200/50 transition-all"
              title="Drag to reorder"
            >
              <GripVertical class="h-5 w-5" />
            </div>

            <!-- Field Number Badge -->
            <div
              :class="[
                'flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-xs font-semibold transition-all',
                draggingIndex === index
                  ? 'bg-blue-200 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300'
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300',
              ]"
            >
              {{ index + 1 }}
            </div>

            <!-- Field Name Input -->
            <div class="flex-1 min-w-0">
              <input
                v-model="field.name"
                class="w-full bg-transparent border-0 border-b border-slate-300 dark:border-slate-600 focus:border-blue-500 focus:ring-0 text-sm font-medium text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 transition-colors py-1.5"
                placeholder="field_name (e.g., patient_name)"
                @input="emitChange"
              />
            </div>

            <!-- Type Selector with Icon -->
            <div class="flex-shrink-0">
              <div class="relative">
                <select
                  v-model="field.type"
                  :class="[selectClass, 'appearance-none pl-3 pr-8 cursor-pointer']"
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
                  class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500"
                />
              </div>
            </div>

            <!-- Description Input -->
            <div class="flex-1 min-w-0 hidden lg:block">
              <input
                v-model="field.description"
                class="w-full bg-transparent border-0 border-b border-slate-300 dark:border-slate-600 focus:border-blue-500 focus:ring-0 text-xs text-slate-600 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 transition-colors py-1.5"
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

            <!-- Pre-defined options (string enum). Only for plain Text fields. -->
            <div
              v-if="field.type === 'String'"
              class="basis-full w-full flex flex-wrap items-center gap-1.5 pt-1.5 mt-0.5 border-t border-slate-200/70 dark:border-slate-700"
            >
              <span class="text-xs font-medium text-slate-500 dark:text-slate-400 mr-0.5"
                >Options</span
              >
              <span
                v-for="(opt, i) in field.options"
                :key="i"
                class="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-md bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 text-xs font-medium"
              >
                {{ opt }}
                <button
                  type="button"
                  class="text-blue-500 hover:text-blue-700 transition-colors"
                  aria-label="Remove option"
                  @click="removeOption(field, i)"
                >
                  <X class="h-3 w-3" aria-hidden="true" />
                </button>
              </span>
              <input
                :value="pendingOptions[field.id] || ''"
                class="flex-1 min-w-[120px] bg-transparent border-0 border-b border-dashed border-slate-300 dark:border-slate-600 focus:border-blue-500 focus:ring-0 text-xs text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 transition-colors py-0.5"
                placeholder="add option — press Enter"
                @input="setPendingOption(field.id, $event.target.value)"
                @keydown="onOptionKeydown(field, $event)"
                @blur="commitOption(field)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Help Footer -->
    <div
      v-if="fields.length > 0"
      class="border-t px-6 py-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20"
    >
      <div class="flex items-start gap-3">
        <div
          class="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center mt-0.5"
        >
          <Info class="h-3 w-3 text-blue-600 dark:text-blue-300" />
        </div>
        <div class="text-sm text-blue-900 dark:text-blue-200">
          <p class="font-medium mb-1.5">Quick Tips</p>
          <ul class="space-y-1 text-blue-700 dark:text-blue-300">
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-blue-400"></span>
              Use clear names like
              <code class="px-1.5 py-0.5 bg-white/60 dark:bg-slate-800/60 rounded text-xs font-mono"
                >patient_name</code
              >
              or
              <code class="px-1.5 py-0.5 bg-white/60 dark:bg-slate-800/60 rounded text-xs font-mono"
                >date_of_birth</code
              >
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
import { ChevronDown, GripVertical, Info, Lock, Plus, ShieldAlert, Trash2, X } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { selectClass } from '@/utils/formStyles'

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
  // `enum` is allowed only on string fields — it represents the
  // pre-defined options feature (e.g. side: left/right/center).
  const isStringWithEnum = propSchema.type === 'string' && Array.isArray(propSchema.enum)
  const allowedKeys = new Set([
    'type',
    'title',
    'description',
    'format',
    ...(isStringWithEnum ? ['enum'] : []),
  ])
  for (const key of Object.keys(propSchema)) {
    if (!allowedKeys.has(key)) return false
  }
  // A string field with a format (date, email, …) and an enum is ambiguous —
  // treat it as advanced so we don't silently drop the format.
  if (isStringWithEnum && propSchema.format) return false
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
        // Pre-defined options (string enum). Stored as a list of strings.
        options: Array.isArray(propSchema.enum) ? [...propSchema.enum] : [],
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

    // Pre-defined options: emit as a string enum. Only applies to Text fields;
    // a format (date/email/…) and enum are mutually exclusive — the simple
    // editor never produces both at once.
    if (mapping.type === 'string' && !propSchema.format && Array.isArray(field.options)) {
      const options = field.options.map((o) => (o ?? '').toString().trim()).filter(Boolean)
      if (options.length > 0) {
        propSchema.enum = options
      }
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
    options: [],
  })
  emitChange()
}

// Remove field
const removeField = (id) => {
  fields.value = fields.value.filter((f) => f.id !== id)
  emitChange()
}

// --- Pre-defined options (string enum) ---
// In-flight text for the "add option" input, keyed by field id so each
// field tracks its own draft independently.
const pendingOptions = ref({})

const setPendingOption = (fieldId, value) => {
  pendingOptions.value[fieldId] = value
}

const commitOption = (field) => {
  const raw = (pendingOptions.value[field.id] || '').trim()
  pendingOptions.value[field.id] = ''
  if (!raw) return
  if (!Array.isArray(field.options)) field.options = []
  if (!field.options.includes(raw)) {
    field.options.push(raw)
    emitChange()
  }
}

const removeOption = (field, index) => {
  if (!Array.isArray(field.options)) return
  field.options.splice(index, 1)
  emitChange()
}

const onOptionKeydown = (field, e) => {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    commitOption(field)
  } else if (
    e.key === 'Backspace' &&
    !(pendingOptions.value[field.id] || '') &&
    Array.isArray(field.options) &&
    field.options.length > 0
  ) {
    e.preventDefault()
    field.options.pop()
    emitChange()
  }
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

/* Dark mode scrollbar override */
:global(.dark) ::-webkit-scrollbar-thumb {
  background: #475569;
}

:global(.dark) ::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}
</style>
