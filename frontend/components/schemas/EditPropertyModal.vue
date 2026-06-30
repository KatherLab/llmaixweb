<template>
  <BaseModal
    :open="open"
    size="lg"
    :closeable="false"
    :close-on-esc="false"
    body-class="p-6"
    footer-class="bg-slate-50 dark:bg-slate-800"
    @close="handleBackdropClose"
  >
    <template #header>
      <h3 class="text-lg font-medium text-slate-900 dark:text-slate-100">
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
      <BaseButton variant="secondary" @click="handleBackdropClose">Cancel</BaseButton>
      <BaseButton @click="save">Save Changes</BaseButton>
    </template>

    <!-- Discard unsaved changes confirmation -->
    <ConfirmationDialog
      :open="showConfirm"
      title="Discard unsaved changes?"
      message="Your edits to this property will be lost."
      confirm-text="Discard"
      cancel-text="Keep editing"
      confirm-variant="danger"
      @confirm="confirmDiscard"
      @cancel="showConfirm = false"
    />
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import BaseButton from '@/components/common/BaseButton.vue'
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

// Close — confirms unsaved changes via ConfirmationDialog
const showConfirm = ref(false)
const handleBackdropClose = () => {
  if (localEditingProperty.value && hasUnsavedPropertyChanges()) {
    showConfirm.value = true
  } else {
    emit('close')
  }
}
const confirmDiscard = () => {
  showConfirm.value = false
  emit('close')
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
