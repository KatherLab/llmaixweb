<template>
  <div class="simple-schema-editor flex flex-col h-full bg-surface">
    <!-- Header -->
    <div class="border-b px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h3 class="text-base font-semibold text-content">Extract Fields</h3>
        <p class="text-sm text-content-muted mt-0.5">Drag to reorder • Click field to edit</p>
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
        <Callout v-if="hasReadonlyFields" variant="warning" class="text-xs">
          Fields with nested groups, lists, or advanced settings are read-only here — edit them in
          <strong>Advanced mode</strong>.
        </Callout>

        <div v-for="(field, index) in fields" :key="field.id">
          <!-- Read-only hint row (nested objects/arrays, enums, constraints, …) -->
          <div
            v-if="field.kind === 'readonly'"
            class="group flex items-center gap-3 p-3 rounded-modal border border-amber-200 dark:border-amber-800 bg-amber-50/60 dark:bg-amber-900/20"
            :title="`Read-only — edit “${field.name}” in Advanced mode`"
          >
            <!-- Lock icon (in place of the drag handle) -->
            <div class="flex-shrink-0 p-2 text-amber-500 rounded-card">
              <Lock class="h-5 w-5" />
            </div>

            <!-- Type badge -->
            <div
              class="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-card bg-amber-200 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 text-[10px] font-semibold"
            >
              {{ readonlyTypeLabel(field) }}
            </div>

            <!-- Field name (read-only) -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-content-muted truncate">
                {{ field.name }}
              </p>
              <p v-if="field.description" class="text-xs text-content-muted truncate">
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

          <!-- Editable row. Only draggable while the grip handle is pressed —
               a permanently-draggable row hijacks text selection in the inputs. -->
          <div
            v-else
            :data-index="index"
            :class="[
              'group flex flex-wrap items-center gap-3 p-3 rounded-modal border transition-all duration-200',
              draggingIndex === index
                ? 'border-primary bg-primary-soft shadow-md scale-[1.02]'
                : fieldError(field)
                  ? 'border-red-300 dark:border-red-700 bg-surface-muted'
                  : 'border-default hover:border-primary hover:shadow-sm bg-surface-muted hover:bg-surface',
            ]"
            :draggable="dragArmedIndex === index"
            @dragstart="handleDragStart"
            @dragend="handleDragEnd"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
            @drop="handleDrop"
          >
            <!-- Drag Handle (arms dragging for this row) -->
            <div
              class="flex-shrink-0 cursor-grab active:cursor-grabbing p-2 text-content-subtle hover:text-content-muted hover:bg-surface-sunken rounded-card transition-all"
              title="Drag to reorder"
              @mousedown="dragArmedIndex = index"
            >
              <GripVertical class="h-5 w-5" />
            </div>

            <!-- Field Number Badge -->
            <div
              :class="[
                'flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-card text-xs font-semibold transition-all',
                draggingIndex === index
                  ? 'bg-primary-soft text-primary'
                  : 'bg-surface-sunken text-content-muted',
              ]"
            >
              {{ index + 1 }}
            </div>

            <!-- Field Name Input -->
            <div class="flex-1 min-w-0">
              <input
                v-model="field.name"
                :class="[
                  'w-full bg-transparent border-0 border-b focus:ring-0 text-sm font-medium text-content placeholder-content-subtle transition-colors py-1.5',
                  fieldError(field)
                    ? 'border-red-400 dark:border-red-600 focus:border-red-500'
                    : 'border-strong focus:border-primary',
                ]"
                placeholder="field_name (e.g., patient_name)"
                @input="emitChange"
              />
              <p v-if="fieldError(field)" class="mt-0.5 text-xs text-red-600 dark:text-red-400">
                {{ fieldError(field) }}
              </p>
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
                  class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-content-subtle"
                />
              </div>
            </div>

            <!-- Required toggle: marks the field as required in the JSON schema
                 (tells the LLM the value must be present). -->
            <button
              type="button"
              :class="[
                'flex-shrink-0 p-1.5 rounded-card transition-colors',
                field.required
                  ? 'text-amber-500 hover:text-amber-600'
                  : 'text-content-subtle hover:text-content-muted',
              ]"
              :title="
                field.required
                  ? 'Required — click to make optional'
                  : 'Optional — click to make required'
              "
              :aria-pressed="field.required"
              aria-label="Toggle required"
              @click="toggleRequired(field)"
            >
              <Star v-if="!field.required" class="h-4 w-4" />
              <Star v-else class="h-4 w-4 fill-current" />
            </button>

            <!-- Description Input -->
            <div class="flex-1 min-w-0 hidden lg:block">
              <input
                v-model="field.description"
                class="w-full bg-transparent border-0 border-b border-strong focus:border-primary focus:ring-0 text-xs text-content-muted placeholder-content-subtle transition-colors py-1.5"
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
              class="basis-full w-full flex flex-wrap items-center gap-1.5 pt-1.5 mt-0.5 border-t border-default"
            >
              <span class="text-xs font-medium text-content-muted mr-0.5">Options</span>
              <span
                v-for="(opt, i) in field.options"
                :key="i"
                class="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-card bg-primary-soft text-primary text-xs font-medium"
              >
                {{ opt }}
                <button
                  type="button"
                  class="text-primary hover:text-primary transition-colors"
                  aria-label="Remove option"
                  @click="removeOption(field, i)"
                >
                  <X class="h-3 w-3" aria-hidden="true" />
                </button>
              </span>
              <input
                :value="pendingOptions[field.id] || ''"
                class="flex-1 min-w-[120px] bg-transparent border-0 border-b border-dashed border-strong focus:border-primary focus:ring-0 text-xs text-content-muted placeholder-content-subtle transition-colors py-0.5"
                placeholder="add option — press Enter"
                @input="setPendingOption(field.id, ($event.target as HTMLInputElement).value)"
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
      class="border-t border-default px-6 py-4 bg-gradient-to-r from-primary-soft to-purple-50 dark:to-purple-900/20"
    >
      <div class="flex items-start gap-3">
        <div
          class="flex-shrink-0 w-5 h-5 rounded-full bg-primary-soft flex items-center justify-center mt-0.5"
        >
          <Info class="h-3 w-3 text-primary" />
        </div>
        <div class="text-sm text-primary">
          <p class="font-medium mb-1.5">Quick Tips</p>
          <ul class="space-y-1 text-primary">
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-primary"></span>
              Use clear names like
              <code class="px-1.5 py-0.5 bg-surface-muted/60 rounded text-xs font-mono"
                >patient_name</code
              >
              or
              <code class="px-1.5 py-0.5 bg-surface-muted/60 rounded text-xs font-mono"
                >date_of_birth</code
              >
            </li>
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-primary"></span>
              The schema is automatically included in the prompt sent to the LLM
            </li>
            <li class="flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-primary"></span>
              Need nested objects or arrays? Switch to <strong>Advanced Mode</strong>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { ChevronDown, GripVertical, Info, Lock, Plus, Star, Trash2, X } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { selectClass } from '@/utils/formStyles'
import type { SchemaDefinition, SchemaProperty } from '@/types'

interface Props {
  schema: SchemaDefinition
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:schema': [schema: SchemaDefinition]
  /** Row-level validity: false when any field name is empty or duplicated.
   *  The parent uses this to block save instead of silently dropping fields. */
  'update:valid': [valid: boolean]
}>()

// Field types used in the simple editor
interface SimpleField {
  id: string
  kind: 'simple'
  name: string
  type: string
  description: string
  options: string[]
  // Whether this field is in the root `required` array. Core to extraction
  // (tells the LLM what must be present), so it's exposed in Simple mode.
  required: boolean
}

interface ReadonlyField {
  id: string
  kind: 'readonly'
  name: string
  description: string
  rawSchema: SchemaProperty
}

type Field = SimpleField | ReadonlyField

// Internal field storage with unique IDs
const fields = ref<Field[]>([])
const draggingIndex = ref(-1)
const dragOverIndex = ref(-1)
// Row index whose grip handle is currently pressed. Only that row is
// `draggable`, so dragging text inside the inputs still works.
const dragArmedIndex = ref(-1)
const isInternalChange = ref(false)

// Last schema received from the parent (external). Kept so `buildSchema` can
// preserve root-level keys (e.g. `required`, `additionalProperties`) and any
// read-only properties verbatim, instead of rebuilding the whole schema from
// only the editable fields (which would silently drop advanced features).
const originalSchema = ref<SchemaDefinition | null>(null)

// Generate unique ID
let fieldIdCounter = 0
const generateId = (): string => `field_${Date.now()}_${fieldIdCounter++}`

// Type mapping: Simple type → JSON Schema type + format
const typeMapping: Record<string, { type: string; format?: string }> = {
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

const isSimpleEditable = (propSchema: SchemaProperty): boolean => {
  if (!propSchema || !SIMPLE_TYPES.includes(propSchema.type)) return false
  // `enum` is allowed only on string fields — it represents the
  // pre-defined options feature (e.g. side: left/right/center).
  const isStringWithEnum = propSchema.type === 'string' && Array.isArray(propSchema.enum)
  const allowedKeys = new Set<string>([
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
  const format = propSchema.format as string
  if (format && !KNOWN_FORMATS.includes(format)) return false
  return true
}

// Human-readable label for a read-only property's type
const readonlyTypeLabel = (field: ReadonlyField): string => {
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

// --- Row validation (empty / duplicate names) ---
// `buildSchema` keys properties by name, so unnamed fields would be silently
// dropped and duplicate names would overwrite each other (last wins). Surface
// both inline and report validity to the parent so save is blocked instead.
const nameCounts = computed<Record<string, number>>(() => {
  const counts: Record<string, number> = {}
  for (const f of fields.value) {
    const name = (f.name || '').trim()
    if (!name) continue
    counts[name] = (counts[name] || 0) + 1
  }
  return counts
})

const fieldError = (field: Field): string | null => {
  if (field.kind !== 'simple') return null
  const name = (field.name || '').trim()
  if (!name) return 'Name this field or remove it'
  if ((nameCounts.value[name] || 0) > 1) return `Duplicate field name "${name}"`
  return null
}

const isValid = computed(() => fields.value.every((f) => !fieldError(f)))

watch(
  isValid,
  (valid) => {
    emit('update:valid', valid)
  },
  { immediate: true },
)

// Convert JSON Schema → Simple fields
const parseSchema = (schema: SchemaDefinition): Field[] => {
  const parsedFields: Field[] = []
  const props = schema?.properties || {}
  const requiredList: string[] = Array.isArray(schema?.required) ? schema.required : []

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
        options: Array.isArray(propSchema.enum) ? [...(propSchema.enum as string[])] : [],
        required: requiredList.includes(name),
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
const buildSchema = (): SchemaDefinition => {
  const schema: SchemaDefinition = originalSchema.value
    ? JSON.parse(JSON.stringify(originalSchema.value))
    : { type: 'object' }
  if (!schema.type) schema.type = 'object'

  const properties: Record<string, SchemaProperty> = {}

  for (const field of fields.value) {
    if (!field.name || !field.name.trim()) continue

    if (field.kind === 'readonly') {
      properties[field.name.trim()] = JSON.parse(JSON.stringify(field.rawSchema))
      continue
    }

    const mapping = typeMapping[field.type] ?? typeMapping.String
    if (!mapping) continue
    const propSchema: SchemaProperty = {
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

  // Rebuild `required`: carry over any required entries for read-only
  // (advanced) properties that still exist, plus the simple fields the user
  // marked required. This keeps required semantics editable in Simple mode
  // without dropping required flags on nested/advanced properties.
  const requiredSet = new Set<string>()
  if (Array.isArray(schema.required)) {
    for (const name of schema.required) {
      if (Object.prototype.hasOwnProperty.call(properties, name)) {
        requiredSet.add(name)
      }
    }
  }
  // Read-only fields: keep their existing required state (already carried above).
  // Simple fields: apply the user's toggle.
  for (const field of fields.value) {
    if (field.kind !== 'simple') continue
    const trimmed = field.name?.trim()
    if (trimmed && Object.prototype.hasOwnProperty.call(properties, trimmed)) {
      if (field.required) {
        requiredSet.add(trimmed)
      } else {
        requiredSet.delete(trimmed)
      }
    }
  }
  if (requiredSet.size > 0) {
    schema.required = Array.from(requiredSet)
  } else {
    delete schema.required
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
    required: false,
  })
  emitChange()
}

// Toggle a simple field's required flag and rebuild the schema.
const toggleRequired = (field: SimpleField) => {
  field.required = !field.required
  emitChange()
}

// Remove field
const removeField = (id: string) => {
  fields.value = fields.value.filter((f) => f.id !== id)
  emitChange()
}

// --- Pre-defined options (string enum) ---
// In-flight text for the "add option" input, keyed by field id so each
// field tracks its own draft independently.
const pendingOptions = ref<Record<string, string>>({})

const setPendingOption = (fieldId: string, value: string) => {
  pendingOptions.value[fieldId] = value
}

const commitOption = (field: SimpleField) => {
  const raw = (pendingOptions.value[field.id] || '').trim()
  pendingOptions.value[field.id] = ''
  if (!raw) return
  if (!Array.isArray(field.options)) field.options = []
  if (!field.options.includes(raw)) {
    field.options.push(raw)
    emitChange()
  }
}

const removeOption = (field: SimpleField, index: number) => {
  if (!Array.isArray(field.options)) return
  field.options.splice(index, 1)
  emitChange()
}

const onOptionKeydown = (field: SimpleField, e: KeyboardEvent) => {
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
const handleDragStart = (e: DragEvent) => {
  const target = e.target as HTMLElement
  draggingIndex.value = parseInt(target.dataset.index || '0')
  target.style.opacity = '0.5'
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(draggingIndex.value))
  }
}

const handleDragEnd = (e: DragEvent) => {
  const target = e.target as HTMLElement
  target.style.opacity = '1'
  draggingIndex.value = -1
  dragOverIndex.value = -1
  dragArmedIndex.value = -1
}

// Disarm dragging when the mouse is released without a drag having started
// (mousedown on the grip handle, mouseup anywhere).
const disarmDrag = () => {
  if (draggingIndex.value === -1) dragArmedIndex.value = -1
}
onMounted(() => {
  window.addEventListener('mouseup', disarmDrag)
})
onUnmounted(() => {
  window.removeEventListener('mouseup', disarmDrag)
})

const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  const currentTarget = e.currentTarget as HTMLElement
  const currentIndex = parseInt(currentTarget.dataset.index || '0')
  if (currentIndex !== draggingIndex.value) {
    dragOverIndex.value = currentIndex
  }
}

const handleDragLeave = () => {
  dragOverIndex.value = -1
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  const fromIndex = draggingIndex.value
  const currentTarget = e.currentTarget as HTMLElement
  const toIndex = parseInt(currentTarget.dataset.index || '0')

  if (fromIndex !== toIndex && fromIndex >= 0 && toIndex >= 0) {
    const newFields = [...fields.value]
    const [removed] = newFields.splice(fromIndex, 1)
    if (removed) newFields.splice(toIndex, 0, removed)
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
  background: var(--color-strong-border);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-content-subtle);
}

/* Dark mode scrollbar override */
:global(.dark) ::-webkit-scrollbar-thumb {
  background: var(--color-strong-border);
}

:global(.dark) ::-webkit-scrollbar-thumb:hover {
  background: var(--color-content-subtle);
}
</style>
