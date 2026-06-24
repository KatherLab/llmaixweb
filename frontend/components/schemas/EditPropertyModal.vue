<template>
  <BaseModal
    :open="open"
    size="lg"
    :closeable="false"
    :close-on-esc="false"
    body-class="p-6"
    footer-class="bg-gray-50"
    @close="handleBackdropClose"
  >
    <template #header>
      <h3 class="text-lg font-medium text-gray-900">
        Edit
        {{
          localEditingProperty?.key === '__root__'
            ? 'Root Schema'
            : advancedMode
              ? 'Property'
              : 'Field'
        }}:
        {{ localEditingProperty?.key === '__root__' ? '' : localEditingProperty?.key }}
      </h3>
    </template>

    <PropertyDetailsEditor
      v-if="localEditingProperty"
      :property="localEditingProperty.schema"
      :property-key="localEditingProperty.key"
      :advanced-mode="advancedMode"
      @update="updateProperty"
      @update-key="updatePropertyKey"
    />

    <template #footer>
      <button
        type="button"
        class="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        @click="$emit('close')"
      >
        Cancel
      </button>
      <button
        type="button"
        class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
        @click="save"
      >
        Save Changes
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import PropertyDetailsEditor from './PropertyDetailsEditor.vue'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  advancedMode: {
    type: Boolean,
    default: false,
  },
  propertyData: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'save'])

// Internal editing state (initialized from propertyData when modal opens)
const localEditingProperty = ref(null)
const originalEditingProperty = ref(null)
const originalEditingPropertyKey = ref(null)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen && props.propertyData) {
      // Initialize editing state from the parent-provided data
      localEditingProperty.value = {
        key: props.propertyData.key,
        schema: JSON.parse(JSON.stringify(props.propertyData.schema)),
      }
      originalEditingProperty.value = JSON.parse(JSON.stringify(props.propertyData.schema))
      originalEditingPropertyKey.value = props.propertyData.key
    } else if (!isOpen) {
      // Cleanup on close
      localEditingProperty.value = null
      originalEditingProperty.value = null
      originalEditingPropertyKey.value = null
    }
  },
)

// PropertyDetailsEditor event handlers
const updateProperty = (newSchema) => {
  if (localEditingProperty.value) {
    // Deep-clone to break reactivity links
    localEditingProperty.value.schema = JSON.parse(JSON.stringify(newSchema))
  }
}

const updatePropertyKey = (newKey) => {
  if (localEditingProperty.value) {
    localEditingProperty.value.newKey = newKey
  }
}

// Unsaved-changes detection (for backdrop close guard)
const hasUnsavedPropertyChanges = () => {
  if (!localEditingProperty.value || !originalEditingProperty.value) return false

  const currentKey = localEditingProperty.value.newKey || localEditingProperty.value.key
  if (
    currentKey !== originalEditingPropertyKey.value &&
    originalEditingPropertyKey.value !== '__root__'
  ) {
    return true
  }

  const currentJSON = JSON.stringify(originalEditingProperty.value)
  const editedJSON = JSON.stringify(localEditingProperty.value.schema)

  return currentJSON !== editedJSON
}

// Backdrop close — confirms unsaved changes (original behavior)
const handleBackdropClose = () => {
  if (localEditingProperty.value && hasUnsavedPropertyChanges()) {
    if (confirm('You have unsaved changes. Are you sure you want to close?')) {
      emit('close')
    }
  } else {
    emit('close')
  }
}

// Save — emits payload to parent, parent applies mutation
const save = () => {
  if (!localEditingProperty.value) return

  emit('save', {
    key: localEditingProperty.value.key,
    newKey: localEditingProperty.value.newKey || localEditingProperty.value.key,
    schema: localEditingProperty.value.schema,
  })
}
</script>
