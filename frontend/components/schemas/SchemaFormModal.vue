<template>
  <BaseModal
    :open="open"
    size="full"
    body-class="p-0 flex flex-col min-h-0"
    panel-class="max-w-[1600px] h-[90vh]"
    @close="cancelSchemaModal"
  >
    <template #header>
      <div class="flex items-center gap-4">
        <h3 class="text-lg font-medium text-slate-900 dark:text-white">
          {{ isEdit ? 'Edit Schema' : 'Create New Schema' }}
        </h3>
        <!-- Simple/Advanced Mode Toggle -->
        <BaseSegmentedControl
          v-model="simpleMode"
          :options="[
            { label: 'Simple', value: true },
            { label: 'Advanced', value: false },
          ]"
        />
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
                class="block text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1.5"
                >Schema Name</label
              >
              <input
                id="schema-name"
                v-model="schemaForm.schema_name"
                class="block w-full border-0 border-b-2 border-slate-200 dark:border-slate-700 bg-transparent dark:bg-slate-800 dark:text-white px-3 py-2 text-lg font-semibold text-slate-900 dark:text-white focus:ring-0 focus:border-blue-500 dark:focus:border-blue-400 transition-colors placeholder-slate-400 dark:placeholder-slate-500"
                placeholder="e.g., Patient Information"
                maxlength="100"
                required
              />
            </div>
            <!-- Validation Indicator -->
            <div
              v-if="schemaForm.schema_definition"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
              :class="isSchemaValid ? getPillClass('green') : getPillClass('red')"
            >
              <CircleCheckBig v-if="isSchemaValid" class="h-4 w-4" />
              <CircleAlert v-else class="h-4 w-4" />
              <span>{{ isSchemaValid ? 'Valid' : 'Invalid' }}</span>
            </div>
          </div>
        </div>

        <!-- Tab Navigation (only show in Advanced mode) -->
        <div v-if="!simpleMode" class="px-6 flex-shrink-0 flex items-end justify-between gap-4">
          <BaseTabGroup v-model="activeTab" :tabs="tabs">
            <template #tab="{ tab }">
              <BookOpen v-if="tab.value === 'visual'" class="h-4 w-4 inline mr-1" />
              <ArrowUpDown v-else class="h-4 w-4 inline mr-1" />
              {{ tab.label }}
            </template>
          </BaseTabGroup>

          <div class="flex items-center space-x-4 pb-2">
            <!-- Advanced Features Toggle -->
            <label class="flex items-center space-x-2 text-sm">
              <input v-model="advancedMode" type="checkbox" :class="checkboxClass" />
              <span class="text-slate-700 dark:text-slate-300">Enable advanced features</span>
            </label>

            <!-- Split View Toggle -->
            <label class="flex items-center space-x-2 text-sm">
              <input v-model="splitView" type="checkbox" :class="checkboxClass" />
              <span class="text-slate-700 dark:text-slate-300">Split view</span>
            </label>

            <!-- Templates Button -->
            <button
              type="button"
              class="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex items-center"
              @click="showTemplates = true"
            >
              <Layers class="h-4 w-4 mr-1" />
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
                'bg-slate-50 dark:bg-slate-800',
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
                  :class="[inputClass, 'h-full font-mono resize-none']"
                  placeholder='{"type": "object", "properties": {...}}'
                  required
                  @input="onRawSchemaChange"
                  @keydown="preserveCursorPosition"
                ></textarea>
                <button
                  type="button"
                  class="absolute top-8 right-8 px-2 py-1 text-xs bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded text-slate-700 dark:text-slate-300"
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
    </form>
    <template #footer>
      <BaseButton variant="secondary" @click="cancelSchemaModal">Cancel</BaseButton>
      <BaseButton
        variant="primary"
        :loading="isSubmitting"
        :disabled="!isSchemaValid"
        @click="isEdit ? updateSchema() : createSchema()"
      >
        {{ isEdit ? 'Update' : 'Create' }}
      </BaseButton>
    </template>
  </BaseModal>

  <!-- Templates Modal -->
  <SchemaTemplatesModal
    :open="showTemplates"
    :templates="schemaTemplates"
    @close="showTemplates = false"
    @apply="applyTemplate"
  />

  <!-- Discard unsaved changes confirmation -->
  <ConfirmationDialog
    :open="showConfirm"
    title="Discard unsaved changes?"
    message="Your schema edits will be lost."
    confirm-text="Discard"
    cancel-text="Keep editing"
    confirm-variant="danger"
    @confirm="confirmDiscard"
    @cancel="showConfirm = false"
  />
</template>

<script setup lang="ts">
import { ref, onUnmounted, watch, nextTick, computed } from 'vue'
import { ArrowUpDown, BookOpen, CircleAlert, CircleCheckBig, Layers } from '@lucide/vue'
import { schemasApi } from '@/services/schemasApi'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import VisualSchemaEditor from './VisualSchemaEditor.vue'
import SimpleSchemaEditor from './SimpleSchemaEditor.vue'
import SchemaTemplatesModal from './SchemaTemplatesModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import { formatJSON, STARTER_SCHEMA, schemaTemplates } from '@/utils/schemaTemplates'
import { getPillClass } from '@/utils/statusStyles'
import { inputClass, checkboxClass } from '@/utils/formStyles'
import { extractErrorMessage } from '@/utils/errors'
import type { Schema, SchemaDefinition } from '@/types'
import type { SchemaTemplate } from '@/utils/schemaTemplates'

interface Props {
  open: boolean
  projectId: string | number
  schema?: Schema | null
}

const props = withDefaults(defineProps<Props>(), {
  schema: null,
})

const emit = defineEmits<{
  close: []
  created: [schema: Schema]
  updated: [schema: Schema]
}>()

const toast = useToast()

const isEdit = computed(() => !!props.schema)

const hasUnsavedChanges = ref(false)
const rawJsonTextarea = ref<HTMLTextAreaElement | null>(null)
const cursorPosition = ref(0)
const isSubmitting = ref(false)
const schemaError = ref('')
const showTemplates = ref(false)
const schemaForm = ref<{
  schema_name: string
  schema_definition: string
}>({
  schema_name: '',
  schema_definition: '',
})

const isUpdating = false
let isUpdatingFromWatch = false
let updateTimeout: ReturnType<typeof setTimeout> | null = null

const activeTab = ref('visual')
// Tab config for BaseTabGroup (lucide icons rendered via #tab scoped slot)
const tabs = [
  { label: 'Visual Editor', value: 'visual' },
  { label: 'Raw JSON', value: 'raw' },
]
const visualSchema = ref<SchemaDefinition>({
  type: 'object',
  properties: {},
})
const advancedMode = ref(false)
const splitView = ref(false)

// Simple mode refs (default to simple mode)
const simpleMode = ref(true)
const simpleSchema = ref<SchemaDefinition>({
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
    schemaError.value = 'Invalid JSON: ' + (err as Error).message
  }
}

const showConfirm = ref(false)
const cancelSchemaModal = () => {
  if (hasUnsavedChanges.value) {
    showConfirm.value = true
    return
  }
  emit('close')
}
const confirmDiscard = () => {
  showConfirm.value = false
  emit('close')
}

const createSchema = async () => {
  schemaError.value = ''
  isSubmitting.value = true
  let response
  try {
    let schemaDefinition: SchemaDefinition
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition)
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + (err as Error).message
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
    let schemaDefinition: SchemaDefinition
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition)
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + (err as Error).message
      toast.error('Invalid JSON format. Please check your schema definition.')
      isSubmitting.value = false
      return
    }
    if (!validateSchema(schemaDefinition)) {
      toast.error(schemaError.value || 'Schema validation failed')
      isSubmitting.value = false
      return
    }
    response = await schemasApi.update(props.projectId, props.schema!.id, {
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
      !!(parsed as Record<string, unknown>).properties &&
      Object.keys((parsed as Record<string, unknown>).properties as object).length > 0
    )
  } catch {
    return false
  }
})

const validateSchema = (schema: unknown): boolean => {
  schemaError.value = ''
  if (
    !schema ||
    typeof schema !== 'object' ||
    !(schema as SchemaDefinition).properties ||
    Object.keys((schema as SchemaDefinition).properties as object).length === 0
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
      schemaError.value = 'Invalid JSON: ' + (err as Error).message
    }
  }, 300)
}

const applyTemplate = (template: SchemaTemplate) => {
  visualSchema.value = template.schema
  schemaForm.value.schema_definition = JSON.stringify(template.schema, null, 2)
  schemaForm.value.schema_name = template.name
  showTemplates.value = false
  toast.info(`Template "${template.name}" applied`)
}

const updateVisualSchema = (newSchema: SchemaDefinition) => {
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

const updateSimpleSchema = (newSchema: SchemaDefinition) => {
  simpleSchema.value = newSchema
  schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2)
  schemaError.value = ''
}

const preserveCursorPosition = (event: Event) => {
  const target = event.target as HTMLTextAreaElement
  cursorPosition.value = target.selectionStart
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
          schema_name: props.schema.schema_name || '',
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
