<template>
  <BaseModal
    :open="open"
    size="sm"
    :closeable="false"
    :close-on-esc="false"
    body-class="p-6"
    @close="$emit('close')"
  >
    <h3 class="text-lg font-semibold text-content mb-4">
      Add {{ advancedMode ? 'Property' : 'Field' }}
    </h3>

    <form @submit.prevent="submit">
      <div class="space-y-4">
        <div>
          <label :class="labelClass" for="add-property-name">
            {{ advancedMode ? 'Property Name' : 'Field Name' }}
          </label>
          <input
            id="add-property-name"
            ref="propertyNameInput"
            v-model="form.name"
            :class="[inputClass, nameError ? 'border-red-400 dark:border-red-600' : '']"
            placeholder="e.g., patient_name"
            required
            :aria-invalid="!!nameError"
          />
          <p v-if="nameError" class="mt-1 text-xs text-red-600 dark:text-red-400">
            {{ nameError }}
          </p>
          <p v-else class="mt-1 text-xs text-content-muted">
            Use lowercase with underscores (e.g., patient_name)
          </p>
        </div>

        <div>
          <label :class="labelClass">
            {{ advancedMode ? 'Type' : 'Field Type' }}
          </label>
          <div class="mt-2 grid grid-cols-2 gap-2">
            <button
              v-for="type in availableTypes"
              :key="type.value"
              type="button"
              :class="[
                'relative rounded-card border p-4 flex flex-col items-center cursor-pointer focus:outline-none transition-all',
                form.type === type.value
                  ? 'border-primary ring-2 ring-ring bg-primary-soft'
                  : 'border-strong hover:border-strong',
              ]"
              @click="form.type = type.value"
            >
              <div :class="['rounded-card p-2 mb-2', type.color]">
                <component :is="type.icon" class="h-6 w-6 text-white" />
              </div>
              <span class="text-sm font-medium">{{ type.label }}</span>
            </button>
          </div>
        </div>

        <div>
          <label :class="labelClass" for="add-property-title"> Display Name </label>
          <input
            id="add-property-title"
            v-model="form.title"
            :class="inputClass"
            placeholder="e.g., Patient Name"
          />
        </div>

        <div>
          <label :class="labelClass" for="add-property-description"> Description </label>
          <textarea
            id="add-property-description"
            v-model="form.description"
            rows="2"
            :class="textareaClass"
            placeholder="Brief description of this field"
          />
        </div>
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">Cancel</BaseButton>
      <BaseButton variant="primary" :disabled="!!nameError" @click="submit"
        >Add {{ advancedMode ? 'Property' : 'Field' }}</BaseButton
      >
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, type Component } from 'vue'
import { inputClass, textareaClass, labelClass } from '@/utils/formStyles'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface AvailableType {
  value: string
  label: string
  color: string
  icon: Component
  description?: string
}

interface Props {
  open: boolean
  advancedMode?: boolean
  availableTypes: AvailableType[]
}

const props = withDefaults(defineProps<Props>(), {
  advancedMode: false,
})

const emit = defineEmits<{
  close: []
  add: [formData: { name: string; type: string; title: string; description: string }]
}>()

// Form state (reset every time the modal opens)
const form = ref({
  name: '',
  type: 'string',
  title: '',
  description: '',
})

// Template ref for the name input — Phase 0 auto-focus fix (preserved)
const propertyNameInput = ref<HTMLInputElement | null>(null)

// Property keys must be valid identifiers (they become JSON schema property
// names). Shown inline; the `pattern` attribute alone never fires because the
// footer button bypasses native form submission.
const KEY_PATTERN = /^[a-zA-Z_][a-zA-Z0-9_]*$/
const submitAttempted = ref(false)

const nameError = computed<string | null>(() => {
  const name = form.value.name.trim()
  if (!name) return submitAttempted.value ? 'Name is required' : null
  if (!KEY_PATTERN.test(name)) {
    return 'Only letters, numbers and underscores — must not start with a number (e.g., patient_name)'
  }
  return null
})

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      // Reset form on open
      form.value = { name: '', type: 'string', title: '', description: '' }
      submitAttempted.value = false
      // Auto-focus the name input (Phase 0 fix: template ref + nextTick)
      await nextTick()
      propertyNameInput.value?.focus()
    }
  },
)

const submit = () => {
  submitAttempted.value = true
  const name = form.value.name.trim()
  if (!name || nameError.value) return
  emit('add', { ...form.value, name })
}
</script>
