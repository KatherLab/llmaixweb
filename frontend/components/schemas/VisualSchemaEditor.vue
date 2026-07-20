<template>
  <div class="h-full flex flex-col bg-surface-muted">
    <!-- Toolbar -->
    <SchemaEditorToolbar
      :navigation-path="navigationPath"
      @navigate-to-root="navigateToRoot"
      @navigate-to-path="navigateToPath"
      @show-help="showHelp = true"
    />

    <!-- Main Editor Area -->
    <div class="flex-1 overflow-hidden flex">
      <!-- Tree Navigation (Collapsible) -->
      <div v-if="showTreeNav" class="w-64 bg-surface border-r border-default overflow-y-auto">
        <div class="p-4">
          <h3 class="text-sm font-medium text-content mb-3">{{ $t('schemaEditor.structure') }}</h3>
          <SchemaTree :schema="schema" :current-path="currentPath" @navigate="navigateToPath" />
        </div>
      </div>

      <!-- Editor Canvas -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Current Schema Block -->
        <div class="max-w-4xl mx-auto">
          <SchemaBlock
            :schema="currentSchema"
            :path="currentPath"
            :advanced-mode="advancedMode"
            @update="updateCurrentSchema"
            @add-property="showAddPropertyModal = true"
            @edit-property="editProperty"
            @delete-property="confirmDeleteProperty"
            @navigate="navigateToProperty"
            @edit-root="editRootSchema"
          />

          <!-- Empty State -->
          <EmptyState
            v-if="
              currentSchema.type === 'object' &&
              (!currentSchema.properties || Object.keys(currentSchema.properties).length === 0)
            "
            class="mt-6"
            :title="$t('schemaEditor.no_properties')"
            :action-text="$t('schemaEditor.add_first_property')"
            @action="showAddPropertyModal = true"
          />
        </div>
      </div>
    </div>

    <!-- Add Property Modal -->
    <AddPropertyModal
      :open="showAddPropertyModal"
      :advanced-mode="advancedMode"
      :available-types="availableTypes"
      @close="showAddPropertyModal = false"
      @add="onAddProperty"
    />

    <!-- Edit Property Modal -->
    <EditPropertyModal
      :open="showEditPropertyModal"
      :advanced-mode="advancedMode"
      :property-data="editingPropertyData"
      @close="onEditClose"
      @save="onEditSave"
    />

    <!-- Delete Confirmation Modal -->
    <DeletePropertyModal
      :open="showDeleteModal"
      :property-key="propertyToDelete"
      :advanced-mode="advancedMode"
      @confirm="deleteProperty"
      @cancel="showDeleteModal = false"
    />

    <!-- Help Modal -->
    <SchemaEditorHelpModal
      :open="showHelp"
      :available-types="availableTypes"
      @close="showHelp = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  StringIcon,
  NumberIcon,
  BooleanIcon,
  ObjectIcon,
  ArrayIcon,
  getTypeColor,
} from '@/utils/schemaTypeIcons'
import EmptyState from '@/components/common/EmptyState.vue'
import SchemaBlock from './SchemaBlock.vue'
import SchemaTree from './SchemaTree.vue'
import SchemaEditorToolbar from './SchemaEditorToolbar.vue'
import AddPropertyModal from './AddPropertyModal.vue'
import EditPropertyModal from './EditPropertyModal.vue'
import DeletePropertyModal from './DeletePropertyModal.vue'
import SchemaEditorHelpModal from './SchemaEditorHelpModal.vue'
import { useSchemaKeyboard } from '@/composables/useSchemaKeyboard'
import { useToast } from '@/composables/useToast'
import type { SchemaDefinition, SchemaProperty } from '@/types'

interface Props {
  schema: SchemaDefinition
  advancedMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  advancedMode: false,
})

const emit = defineEmits<{
  'update:schema': [schema: SchemaDefinition]
}>()

// UI State
const { t } = useI18n({ useScope: 'global' })
const toast = useToast()
const showTreeNav = ref(true)
const showAddPropertyModal = ref(false)
const showEditPropertyModal = ref(false)
const showDeleteModal = ref(false)
const showHelp = ref(false)

// Navigation
const currentPath = ref<string[]>([])
const navigationPath = computed(() => {
  return currentPath.value.map((segment) => {
    // Make path segments more readable
    return segment.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  })
})

// Schema Data
const localSchema = ref<SchemaDefinition>(JSON.parse(JSON.stringify(props.schema)))
const currentSchema = computed<SchemaDefinition>(() => {
  let schema: SchemaDefinition = localSchema.value
  for (const segment of currentPath.value) {
    if (schema.properties && schema.properties[segment]) {
      schema = schema.properties[segment]
    } else if (schema.items) {
      schema = schema.items
    }
  }
  return schema
})

// Property type definitions with icons — icons shared via @/utils/schemaTypeIcons
interface AvailableType {
  value: string
  label: string
  color: string
  icon: Component
  description: string
}

const availableTypes = computed<AvailableType[]>(() => [
  {
    value: 'string',
    label: props.advancedMode ? 'String' : t('schemaEditor.types.text'),
    color: getTypeColor('string'),
    icon: StringIcon,
    description: t('schemaEditor.type_desc.string'),
  },
  {
    value: 'number',
    label: props.advancedMode ? 'Number' : t('schemaEditor.types.number'),
    color: getTypeColor('number'),
    icon: NumberIcon,
    description: t('schemaEditor.type_desc.number'),
  },
  {
    value: 'boolean',
    label: props.advancedMode ? 'Boolean' : t('schemaEditor.types.yes_no'),
    color: getTypeColor('boolean'),
    icon: BooleanIcon,
    description: t('schemaEditor.type_desc.boolean'),
  },
  {
    value: 'object',
    label: props.advancedMode ? 'Object' : t('schemaEditor.types.group'),
    color: getTypeColor('object'),
    icon: ObjectIcon,
    description: t('schemaEditor.type_desc.object'),
  },
  {
    value: 'array',
    label: props.advancedMode ? 'Array' : t('schemaEditor.types.list'),
    color: getTypeColor('array'),
    icon: ArrayIcon,
    description: t('schemaEditor.type_desc.array'),
  },
])

// Edit property data (passed to EditPropertyModal)
interface EditingPropertyData {
  key: string
  schema: SchemaDefinition | SchemaProperty
}

const editingPropertyData = ref<EditingPropertyData | null>(null)

// Delete property
const propertyToDelete = ref('')

// Watch for external schema changes
watch(
  () => props.schema,
  (newSchema) => {
    // Only update if the schema actually changed
    if (JSON.stringify(newSchema) !== JSON.stringify(localSchema.value)) {
      localSchema.value = JSON.parse(JSON.stringify(newSchema))
    }
  },
  { deep: true },
)

// Emit changes
watch(
  localSchema,
  (newSchema) => {
    emit('update:schema', newSchema)
  },
  { deep: true },
)

// Keyboard shortcuts (plain "N" adds a property; Escape is owned by BaseModal)
useSchemaKeyboard({
  showAddPropertyModal,
  showEditPropertyModal,
  showDeleteModal,
  showHelp,
  currentSchema,
})

// Navigation methods
const navigateToRoot = () => {
  currentPath.value = []
}

const navigateToPath = (pathIndex: number | string[]) => {
  if (typeof pathIndex === 'number') {
    currentPath.value = currentPath.value.slice(0, pathIndex + 1)
  } else if (Array.isArray(pathIndex)) {
    currentPath.value = pathIndex
  }
}

const navigateToProperty = (propertyKey: string) => {
  currentPath.value = [...currentPath.value, propertyKey]
}

// Schema update methods
const updateCurrentSchema = (updates: SchemaProperty) => {
  let schema: SchemaDefinition = localSchema.value
  const path = [...currentPath.value]
  const lastSegment = path.pop()

  // Navigate to parent
  for (const segment of path) {
    if (schema.properties && schema.properties[segment]) {
      schema = schema.properties[segment]
    } else if (schema.items) {
      schema = schema.items
    }
  }

  // Update the schema
  if (lastSegment) {
    if (schema.properties && schema.properties[lastSegment]) {
      schema.properties[lastSegment] = JSON.parse(JSON.stringify(updates))
    } else if (lastSegment === 'items' && schema.items) {
      schema.items = JSON.parse(JSON.stringify(updates))
    }
  } else {
    // root
    localSchema.value = JSON.parse(JSON.stringify(updates))
  }
}

// Add property (receives form data from AddPropertyModal)
const onAddProperty = (formData: {
  name: string
  type: string
  title: string
  description: string
}) => {
  const key = formData.name.trim()
  if (currentSchema.value.properties?.[key]) {
    toast.warning(t('schemaEditor.property_exists', { name: key }))
    return
  }

  if (!formData.name.trim()) return

  const propertyKey = formData.name.trim()
  const propertySchema: SchemaProperty = {
    type: formData.type,
    title: formData.title || propertyKey,
    description: formData.description,
  }

  // Add type-specific defaults
  if (propertySchema.type === 'object') {
    propertySchema.properties = {}
  } else if (propertySchema.type === 'array') {
    propertySchema.items = { type: 'string' }
  }

  // Add to current schema
  if (!currentSchema.value.properties) {
    currentSchema.value.properties = {}
  }
  currentSchema.value.properties[propertyKey] = propertySchema

  showAddPropertyModal.value = false
}

// Edit property — opens EditPropertyModal with initial data
const editProperty = ({
  key,
  schema,
}: {
  key: string
  schema: SchemaDefinition | SchemaProperty
}) => {
  editingPropertyData.value = {
    key,
    schema: JSON.parse(JSON.stringify(schema)),
  }
  showEditPropertyModal.value = true
}

const editRootSchema = () => {
  editingPropertyData.value = {
    key: '__root__',
    schema: JSON.parse(JSON.stringify(localSchema.value)),
  }
  showEditPropertyModal.value = true
}

// Edit save — applies mutation to localSchema
const onEditSave = (payload: {
  key: string
  newKey: string
  schema: SchemaDefinition | SchemaProperty
}) => {
  if (savePropertyEdits(payload)) {
    showEditPropertyModal.value = false
  }
}

const onEditClose = () => {
  showEditPropertyModal.value = false
}

const savePropertyEdits = ({
  key,
  newKey,
  schema,
}: {
  key: string
  newKey: string
  schema: SchemaDefinition | SchemaProperty
}): boolean => {
  /* ---------- 1. ROOT SCHEMA ---------- */
  if (key === '__root__') {
    // Replace (don't merge) the entire root schema
    localSchema.value = JSON.parse(JSON.stringify(schema))
    return true
  }

  /* ---------- 2. NORMAL PROPERTY ---------- */
  const oldKey = key

  // Find the parent container of the property being edited
  let parent: SchemaDefinition = localSchema.value
  const path = [...currentPath.value]
  for (const segment of path) {
    if (parent.properties && parent.properties[segment]) {
      parent = parent.properties[segment]
    } else if (parent.items) {
      parent = parent.items
    }
  }

  // Guard-clause for duplicates when renaming
  if (oldKey !== newKey && parent.properties && parent.properties[newKey]) {
    toast.warning(t('schemaEditor.property_exists', { name: newKey }))
    return false
  }

  // Deep-clone the edited schema so we don't keep reactive links
  const freshSchema: SchemaProperty = JSON.parse(JSON.stringify(schema))

  // If the container is an OBJECT
  if (parent.properties) {
    if (oldKey !== newKey) {
      delete parent.properties[oldKey]
    }
    parent.properties[newKey] = freshSchema

    // Update "required" array if present
    if (parent.required && Array.isArray(parent.required)) {
      const idx = parent.required.indexOf(oldKey)
      if (idx !== -1) {
        parent.required[idx] = newKey
      }
    }
  }

  // If the container is an ARRAY items schema (editing "items")
  if (oldKey === 'items' && parent.type === 'array') {
    parent.items = freshSchema
  }

  return true
}

// Delete property
const confirmDeleteProperty = (propertyKey: string) => {
  propertyToDelete.value = propertyKey
  showDeleteModal.value = true
}

const deleteProperty = () => {
  if (propertyToDelete.value && currentSchema.value.properties) {
    // Delete the property
    delete currentSchema.value.properties[propertyToDelete.value]

    // Also remove from required array if present
    if (currentSchema.value.required && Array.isArray(currentSchema.value.required)) {
      const requiredIndex = currentSchema.value.required.indexOf(propertyToDelete.value)
      if (requiredIndex !== -1) {
        currentSchema.value.required.splice(requiredIndex, 1)

        // Remove empty required array
        if (currentSchema.value.required.length === 0) {
          delete currentSchema.value.required
        }
      }
    }
  }
  showDeleteModal.value = false
  propertyToDelete.value = ''
}
</script>
