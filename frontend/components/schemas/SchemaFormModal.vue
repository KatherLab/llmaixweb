<template>
  <BaseModal
    :open="open"
    size="full"
    body-class="p-0 flex flex-col min-h-0"
    panel-class="max-w-[1600px] h-[90vh] dark:bg-slate-900 dark:border-slate-700"
    header-class="dark:border-slate-700"
    @close="cancelSchemaModal"
  >
    <template #header>
      <div class="flex items-center gap-4">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">
          {{ isEdit ? 'Edit Schema' : 'Create New Schema' }}
        </h3>
        <!-- Simple/Advanced Mode Toggle -->
        <div class="flex items-center gap-2 bg-gray-100 dark:bg-slate-800 rounded-lg p-1">
          <button
            type="button"
            :class="[
              'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
              !simpleMode
                ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-slate-400 hover:text-gray-900',
            ]"
            @click="simpleMode = false"
          >
            Advanced
          </button>
          <button
            type="button"
            :class="[
              'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
              simpleMode
                ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-slate-400 hover:text-gray-900',
            ]"
            @click="simpleMode = true"
          >
            Simple
          </button>
        </div>
      </div>
    </template>

    <form
      class="flex flex-col flex-1 min-h-0"
      @submit.prevent="isEdit ? updateSchema() : createSchema()"
    >
      <div class="flex-1 flex flex-col min-h-0">
        <!-- Schema Name Input (Modern) -->
        <div class="px-6 pt-4 pb-3 flex-shrink-0">
          <div class="flex items-center gap-3">
            <div class="flex-1 max-w-lg">
              <label
                for="schema-name"
                class="block text-xs font-semibold text-gray-600 dark:text-slate-400 uppercase tracking-wide mb-1.5"
                >Schema Name</label
              >
              <input
                id="schema-name"
                v-model="schemaForm.schema_name"
                class="block w-full border-0 border-b-2 border-gray-200 dark:border-slate-700 bg-transparent dark:bg-slate-800 dark:text-white px-3 py-2 text-lg font-semibold text-gray-900 dark:text-white focus:ring-0 focus:border-indigo-500 dark:focus:border-indigo-400 transition-colors placeholder-gray-400"
                placeholder="e.g., Patient Information"
                required
              />
            </div>
            <!-- Validation Indicator -->
            <div
              v-if="schemaForm.schema_definition"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
              :class="isSchemaValid ? getPillClass('green') : getPillClass('red')"
            >
              <svg
                v-if="isSchemaValid"
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>{{ isSchemaValid ? 'Valid' : 'Invalid' }}</span>
            </div>
          </div>
        </div>

        <!-- Tab Navigation (only show in Advanced mode) -->
        <div v-if="!simpleMode" class="px-6 flex-shrink-0 flex items-end justify-between gap-4">
          <BaseTabGroup v-model="activeTab" :tabs="tabs" tone="indigo">
            <template #tab="{ tab }">
              <svg
                v-if="tab.value === 'visual'"
                class="h-4 w-4 inline mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zM21 5a2 2 0 00-2-2h-4a2 2 0 00-2 2v12a4 4 0 004 4h4a2 2 0 002-2V5z"
                />
              </svg>
              <svg
                v-else
                class="h-4 w-4 inline mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                />
              </svg>
              {{ tab.label }}
            </template>
          </BaseTabGroup>

          <div class="flex items-center space-x-4 pb-2">
            <!-- Advanced Features Toggle -->
            <label class="flex items-center space-x-2 text-sm">
              <input
                v-model="advancedMode"
                type="checkbox"
                class="rounded border-gray-300 dark:border-slate-600 text-indigo-600 focus:ring-indigo-500"
              />
              <span class="text-gray-700 dark:text-slate-300">Enable advanced features</span>
            </label>

            <!-- Split View Toggle -->
            <label class="flex items-center space-x-2 text-sm">
              <input
                v-model="splitView"
                type="checkbox"
                class="rounded border-gray-300 dark:border-slate-600 text-indigo-600 focus:ring-indigo-500"
              />
              <span class="text-gray-700 dark:text-slate-300">Split view</span>
            </label>

            <!-- Templates Button -->
            <button
              type="button"
              class="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 flex items-center"
              @click="showTemplates = true"
            >
              <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              Templates
            </button>
          </div>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 min-h-0 overflow-hidden flex flex-col">
          <!-- Simple Mode Editor -->
          <div v-if="simpleMode" class="h-full">
            <SimpleSchemaEditor :schema="simpleSchema" @update:schema="updateSimpleSchema" />
          </div>

          <!-- Advanced Mode: Visual/Raw Tabs -->
          <div
            v-else
            class="flex-1 min-h-0"
            :class="splitView && activeTab === 'visual' ? 'flex' : ''"
          >
            <!-- Visual Editor Tab -->
            <div
              v-if="activeTab === 'visual' || (splitView && activeTab === 'visual')"
              :class="[
                'bg-gray-50 dark:bg-slate-800',
                splitView && activeTab === 'visual'
                  ? 'w-1/2 border-r dark:border-slate-700'
                  : 'h-full',
              ]"
            >
              <VisualSchemaEditor
                :schema="visualSchema"
                :advanced-mode="advancedMode"
                @update:schema="updateVisualSchema"
              />
            </div>

            <!-- Raw JSON Tab -->
            <div
              v-if="activeTab === 'raw' || (splitView && activeTab === 'visual')"
              :class="[
                'relative flex flex-col',
                splitView && activeTab === 'visual' ? 'w-1/2' : 'h-full',
              ]"
            >
              <div class="flex-1 p-6 min-h-0">
                <textarea
                  ref="rawJsonTextarea"
                  v-model="schemaForm.schema_definition"
                  class="block w-full h-full border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono resize-none"
                  placeholder='{"type": "object", "properties": {...}}'
                  required
                  @input="onRawSchemaChange"
                  @keydown="preserveCursorPosition"
                ></textarea>
                <button
                  type="button"
                  class="absolute top-8 right-8 px-2 py-1 text-xs bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded text-gray-700 dark:text-slate-300"
                  title="Format JSON"
                  @click="formatJsonInput"
                >
                  Format
                </button>
              </div>
            </div>
          </div>
        </div>

        <p
          v-if="schemaError"
          class="px-6 py-2 text-sm text-red-600 dark:text-red-400 flex-shrink-0"
        >
          {{ schemaError }}
        </p>
      </div>

      <!-- Modal Footer -->
      <div
        class="px-6 py-4 bg-gray-50 dark:bg-slate-800 border-t dark:border-slate-700 flex justify-end space-x-3 flex-shrink-0"
      >
        <BaseButton variant="secondary" @click="cancelSchemaModal">Cancel</BaseButton>
        <BaseButton type="submit" :loading="isSubmitting" :disabled="!isSchemaValid">
          {{ isEdit ? 'Update' : 'Create' }}
        </BaseButton>
      </div>
    </form>
  </BaseModal>

  <!-- Templates Modal -->
  <SchemaTemplatesModal
    :open="showTemplates"
    :templates="schemaTemplates"
    @close="showTemplates = false"
    @apply="applyTemplate"
  />
</template>

<script setup>
import { ref, onUnmounted, watch, nextTick, computed } from 'vue'
import { schemasApi } from '@/services/schemasApi'
import { useToast } from 'vue-toastification'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import VisualSchemaEditor from './VisualSchemaEditor.vue'
import SimpleSchemaEditor from './SimpleSchemaEditor.vue'
import SchemaTemplatesModal from './SchemaTemplatesModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { formatJSON, STARTER_SCHEMA, schemaTemplates } from '@/utils/schemaTemplates'
import { getPillClass } from '@/utils/statusStyles'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: [String, Number],
    required: true,
  },
  schema: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'created', 'updated'])

const toast = useToast()

const isEdit = computed(() => !!props.schema)

const hasUnsavedChanges = ref(false)
const rawJsonTextarea = ref(null)
const cursorPosition = ref(0)
const isSubmitting = ref(false)
const schemaError = ref('')
const showTemplates = ref(false)
const schemaForm = ref({
  schema_name: '',
  schema_definition: '',
})

let isUpdating = false
let isUpdatingFromWatch = false
let updateTimeout = null

const activeTab = ref('visual')
// Tab config for BaseTabGroup (SVG icons rendered via #tab scoped slot)
const tabs = [
  { label: 'Visual Editor', value: 'visual' },
  { label: 'Raw JSON', value: 'raw' },
]
const visualSchema = ref({
  type: 'object',
  properties: {},
})
const advancedMode = ref(false)
const splitView = ref(false)

// Simple mode refs (default to simple mode)
const simpleMode = ref(true)
const simpleSchema = ref({
  type: 'object',
  properties: {},
})

const formatJsonInput = () => {
  try {
    const parsedJson = JSON.parse(schemaForm.value.schema_definition)
    schemaForm.value.schema_definition = JSON.stringify(parsedJson, null, 2)
    visualSchema.value = parsedJson
    schemaError.value = ''
  } catch (err) {
    schemaError.value = 'Invalid JSON: ' + err.message
  }
}

const cancelSchemaModal = () => {
  if (hasUnsavedChanges.value) {
    if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
      return
    }
  }

  emit('close')
}

const createSchema = async () => {
  schemaError.value = ''
  isSubmitting.value = true
  let response
  try {
    let schemaDefinition
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition)
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message
      toast.error('Invalid JSON format. Please check your schema definition.')
      isSubmitting.value = false
      return
    }
    if (!validateSchema(schemaDefinition)) {
      toast.error(schemaError.value || 'Schema validation failed')
      isSubmitting.value = false
      return
    }
    response = await schemasApi.create(props.projectId, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition,
    })
    hasUnsavedChanges.value = false
    emit('created', response.data)
    emit('close')
    toast.success(`Schema "${schemaForm.value.schema_name}" created successfully`)
  } catch (err) {
    schemaError.value = extractErrorMessage(err, 'Failed to create schema')
    toast.error(schemaError.value)
    console.error(err)
  } finally {
    isSubmitting.value = false
  }
}

const updateSchema = async () => {
  schemaError.value = ''
  isSubmitting.value = true
  let response
  try {
    let schemaDefinition
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition)
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message
      toast.error('Invalid JSON format. Please check your schema definition.')
      isSubmitting.value = false
      return
    }
    if (!validateSchema(schemaDefinition)) {
      toast.error(schemaError.value || 'Schema validation failed')
      isSubmitting.value = false
      return
    }
    response = await schemasApi.update(props.projectId, props.schema.id, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition,
    })
    hasUnsavedChanges.value = false
    emit('updated', response.data)
    emit('close')
    toast.success(`Schema "${schemaForm.value.schema_name}" updated successfully`)
  } catch (err) {
    schemaError.value = extractErrorMessage(err, 'Failed to update schema')
    toast.error(schemaError.value)
    console.error(err)
  } finally {
    isSubmitting.value = false
  }
}

// A schema is saveable when it parses to an object with at least one property.
const isSchemaValid = computed(() => {
  try {
    const parsed = JSON.parse(schemaForm.value.schema_definition)
    return (
      !!parsed &&
      typeof parsed === 'object' &&
      !!parsed.properties &&
      Object.keys(parsed.properties).length > 0
    )
  } catch {
    return false
  }
})

const validateSchema = (schema) => {
  schemaError.value = ''
  if (
    !schema ||
    typeof schema !== 'object' ||
    !schema.properties ||
    Object.keys(schema.properties).length === 0
  ) {
    schemaError.value = 'Schema must contain at least one field.'
    return false
  }
  return true
}

const onRawSchemaChange = () => {
  if (isUpdatingFromWatch) return

  // Clear any pending updates
  if (updateTimeout) {
    clearTimeout(updateTimeout)
  }

  // Store cursor position
  const textarea = rawJsonTextarea.value
  const savedPosition = textarea ? textarea.selectionStart : 0

  updateTimeout = setTimeout(() => {
    try {
      const parsed = JSON.parse(schemaForm.value.schema_definition)
      isUpdatingFromWatch = true

      // Deep clone to break reference
      visualSchema.value = JSON.parse(JSON.stringify(parsed))
      schemaError.value = ''

      nextTick(() => {
        isUpdatingFromWatch = false
        // Restore cursor position
        if (textarea && textarea === document.activeElement) {
          textarea.setSelectionRange(savedPosition, savedPosition)
        }
      })
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message
    }
  }, 300)
}

const applyTemplate = (template) => {
  visualSchema.value = template.schema
  schemaForm.value.schema_definition = JSON.stringify(template.schema, null, 2)
  schemaForm.value.schema_name = template.name
  showTemplates.value = false
  toast.info(`Template "${template.name}" applied`)
}

const updateVisualSchema = (newSchema) => {
  if (isUpdatingFromWatch) return

  // Clear any pending updates
  if (updateTimeout) {
    clearTimeout(updateTimeout)
  }

  isUpdatingFromWatch = true
  visualSchema.value = JSON.parse(JSON.stringify(newSchema)) // Deep clone
  schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2)
  schemaError.value = ''

  nextTick(() => {
    isUpdatingFromWatch = false
  })
}

const updateSimpleSchema = (newSchema) => {
  simpleSchema.value = newSchema
  schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2)
  schemaError.value = ''
}

const preserveCursorPosition = (event) => {
  cursorPosition.value = event.target.selectionStart
}

// Cleanup on unmount
onUnmounted(() => {
  if (updateTimeout) {
    clearTimeout(updateTimeout)
  }
})

// Watch for tab changes to sync data
watch(activeTab, (newTab) => {
  if (newTab === 'visual' && !splitView.value) {
    // Convert raw JSON to visual schema
    try {
      const parsed = JSON.parse(
        schemaForm.value.schema_definition || '{"type": "object", "properties": {}}',
      )
      visualSchema.value = parsed
    } catch {
      console.warn('Invalid JSON, using default schema')
      visualSchema.value = { type: 'object', properties: {} }
    }
  } else if (newTab === 'raw' && !splitView.value) {
    // Convert visual schema to raw JSON
    schemaForm.value.schema_definition = JSON.stringify(visualSchema.value, null, 2)
  }
})

// Sync the working copy of whichever editor we're switching INTO from the
// canonical schema string. `visualSchema` and `simpleSchema` are independent
// copies that are only refreshed from `schemaForm` on modal open otherwise, so
// without this, edits made in one mode (e.g. deleting a field in Advanced) would
// not appear in the other until the schema is saved and re-opened.
watch(simpleMode, (isSimple) => {
  try {
    const parsed = JSON.parse(
      schemaForm.value.schema_definition || '{"type": "object", "properties": {}}',
    )
    if (isSimple) {
      simpleSchema.value = parsed
    } else {
      visualSchema.value = parsed
    }
  } catch {
    console.warn('Invalid JSON when switching schema editor mode, keeping current state')
  }
})

// Initialize schema when opening modal
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      simpleMode.value = true // Default to simple mode
      if (props.schema) {
        // Edit mode
        const formattedJson = formatJSON(props.schema.schema_definition)
        schemaForm.value = {
          schema_name: props.schema.schema_name,
          schema_definition: formattedJson,
        }
        try {
          const parsed = JSON.parse(formattedJson)
          simpleSchema.value = parsed
          visualSchema.value = parsed
        } catch {
          simpleSchema.value = { type: 'object', properties: {} }
          visualSchema.value = { type: 'object', properties: {} }
        }
      } else {
        // Create mode — seed starter fields for a new schema
        const starter = JSON.parse(JSON.stringify(STARTER_SCHEMA))
        simpleSchema.value = starter
        visualSchema.value = JSON.parse(JSON.stringify(STARTER_SCHEMA))
        schemaForm.value = {
          schema_name: '',
          schema_definition: JSON.stringify(STARTER_SCHEMA, null, 2),
        }
      }
    } else {
      // Reset on close
      schemaError.value = ''
      activeTab.value = 'visual'
      schemaForm.value = {
        schema_name: '',
        schema_definition: '',
      }
      visualSchema.value = { type: 'object', properties: {} }
      hasUnsavedChanges.value = false
    }
  },
)

// Watch for changes to track unsaved state
watch(
  [schemaForm, visualSchema],
  () => {
    if (isUpdating) return
    hasUnsavedChanges.value = true
  },
  { deep: true },
)

// Watch visual schema changes (advanced mode only).
// In simple mode the SimpleSchemaEditor drives `schemaForm` via `updateSimpleSchema`;
// syncing from `visualSchema` here would clobber it with the (empty) visual schema.
watch(
  visualSchema,
  (newSchema) => {
    if (isUpdatingFromWatch || simpleMode.value) return

    // Clear any pending updates
    if (updateTimeout) {
      clearTimeout(updateTimeout)
    }

    // Debounce updates
    updateTimeout = setTimeout(() => {
      if (document.activeElement !== rawJsonTextarea.value) {
        isUpdatingFromWatch = true
        schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2)
        nextTick(() => {
          isUpdatingFromWatch = false
        })
      }
    }, 300)
  },
  { deep: true },
)
</script>
