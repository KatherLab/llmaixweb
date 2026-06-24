<template>
  <div class="h-full flex flex-col bg-gray-50">
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
      <div v-if="showTreeNav" class="w-64 bg-white border-r overflow-y-auto">
        <div class="p-4">
          <h3 class="text-sm font-medium text-gray-900 mb-3">Schema Structure</h3>
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
          <div
            v-if="
              currentSchema.type === 'object' &&
              (!currentSchema.properties || Object.keys(currentSchema.properties).length === 0)
            "
            class="mt-6 text-center py-12 border-2 border-dashed border-gray-300 rounded-lg"
          >
            <svg
              class="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            <p class="mt-2 text-sm text-gray-600">No properties defined</p>
            <button
              type="button"
              class="mt-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              @click="showAddPropertyModal = true"
            >
              Add First Property
            </button>
          </div>
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

<script setup>
import { ref, computed, watch } from 'vue'
import { StringIcon, NumberIcon, BooleanIcon, ObjectIcon, ArrayIcon } from '@/utils/schemaTypeIcons'
import SchemaBlock from './SchemaBlock.vue'
import SchemaTree from './SchemaTree.vue'
import SchemaEditorToolbar from './SchemaEditorToolbar.vue'
import AddPropertyModal from './AddPropertyModal.vue'
import EditPropertyModal from './EditPropertyModal.vue'
import DeletePropertyModal from './DeletePropertyModal.vue'
import SchemaEditorHelpModal from './SchemaEditorHelpModal.vue'
import { useSchemaKeyboard } from '@/composables/useSchemaKeyboard'

const props = defineProps({
  schema: {
    type: Object,
    required: true,
  },
  advancedMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:schema'])

// UI State
const showTreeNav = ref(true)
const showAddPropertyModal = ref(false)
const showEditPropertyModal = ref(false)
const showDeleteModal = ref(false)
const showHelp = ref(false)

// Navigation
const currentPath = ref([])
const navigationPath = computed(() => {
  return currentPath.value.map((segment) => {
    // Make path segments more readable
    return segment.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  })
})

// Schema Data
const localSchema = ref(JSON.parse(JSON.stringify(props.schema)))
const currentSchema = computed(() => {
  let schema = localSchema.value
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
const availableTypes = computed(() => [
  {
    value: 'string',
    label: props.advancedMode ? 'String' : 'Text',
    color: 'bg-green-500',
    icon: StringIcon,
    description: 'Single line or multi-line text',
  },
  {
    value: 'number',
    label: props.advancedMode ? 'Number' : 'Number',
    color: 'bg-blue-500',
    icon: NumberIcon,
    description: 'Numeric values, decimals allowed',
  },
  {
    value: 'boolean',
    label: props.advancedMode ? 'Boolean' : 'Yes/No',
    color: 'bg-purple-500',
    icon: BooleanIcon,
    description: 'True or false values',
  },
  {
    value: 'object',
    label: props.advancedMode ? 'Object' : 'Group',
    color: 'bg-orange-500',
    icon: ObjectIcon,
    description: 'Group of related fields',
  },
  {
    value: 'array',
    label: props.advancedMode ? 'Array' : 'List',
    color: 'bg-pink-500',
    icon: ArrayIcon,
    description: 'List of items',
  },
])

// Edit property data (passed to EditPropertyModal)
const editingPropertyData = ref(null)

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

// Keyboard shortcuts (Ctrl/Cmd+N, Escape)
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

const navigateToPath = (pathIndex) => {
  if (typeof pathIndex === 'number') {
    currentPath.value = currentPath.value.slice(0, pathIndex + 1)
  } else if (Array.isArray(pathIndex)) {
    currentPath.value = pathIndex
  }
}

const navigateToProperty = (propertyKey) => {
  currentPath.value = [...currentPath.value, propertyKey]
}

// Schema update methods
const updateCurrentSchema = (updates) => {
  let schema = localSchema.value
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
const onAddProperty = (formData) => {
  const key = formData.name.trim()
  if (currentSchema.value.properties?.[key]) {
    alert(`Property "${key}" already exists!`)
    return
  }

  if (!formData.name.trim()) return

  const propertyKey = formData.name.trim()
  const propertySchema = {
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
const editProperty = ({ key, schema }) => {
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
const onEditSave = (payload) => {
  if (savePropertyEdits(payload)) {
    showEditPropertyModal.value = false
  }
}

const onEditClose = () => {
  showEditPropertyModal.value = false
}

const savePropertyEdits = ({ key, newKey, schema }) => {
  /* ---------- 1. ROOT SCHEMA ---------- */
  if (key === '__root__') {
    // Replace (don't merge) the entire root schema
    localSchema.value = JSON.parse(JSON.stringify(schema))
    return true
  }

  /* ---------- 2. NORMAL PROPERTY ---------- */
  const oldKey = key

  // Find the parent container of the property being edited
  let parent = localSchema.value
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
    alert(`Property "${newKey}" already exists!`)
    return false
  }

  // Deep-clone the edited schema so we don't keep reactive links
  const freshSchema = JSON.parse(JSON.stringify(schema))

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
const confirmDeleteProperty = (propertyKey) => {
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
