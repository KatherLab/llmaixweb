<template>
  <BaseModal
    :open="open"
    size="sm"
    :closeable="false"
    :close-on-esc="false"
    body-class="p-6"
    @close="$emit('close')"
  >
    <h3 class="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
      Add {{ advancedMode ? 'Property' : 'Field' }}
    </h3>

    <form @submit.prevent="submit">
      <div class="space-y-4">
        <div>
          <label :class="labelClass">
            {{ advancedMode ? 'Property Name' : 'Field Name' }}
          </label>
          <input
            ref="propertyNameInput"
            v-model="form.name"
            :class="inputClass"
            placeholder="e.g., patient_name"
            required
          />
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
                'relative rounded-lg border p-4 flex flex-col items-center cursor-pointer focus:outline-none transition-all',
                form.type === type.value
                  ? 'border-blue-500 ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/30 dark:border-blue-400'
                  : 'border-slate-300 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-500',
              ]"
              @click="form.type = type.value"
            >
              <div :class="['rounded-lg p-2 mb-2', type.color]">
                <component :is="type.icon" class="h-6 w-6 text-white" />
              </div>
              <span class="text-sm font-medium">{{ type.label }}</span>
            </button>
          </div>
        </div>

        <div>
          <label :class="labelClass"> Display Name </label>
          <input v-model="form.title" :class="inputClass" placeholder="e.g., Patient Name" />
        </div>

        <div>
          <label :class="labelClass"> Description </label>
          <textarea
            v-model="form.description"
            rows="2"
            :class="textareaClass"
            placeholder="Brief description of this field"
          />
        </div>
      </div>

      <div class="mt-6 flex justify-end space-x-3">
        <BaseButton variant="secondary" @click="$emit('close')">Cancel</BaseButton>
        <BaseButton type="submit">Add {{ advancedMode ? 'Property' : 'Field' }}</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { inputClass, textareaClass, labelClass } from '@/utils/formStyles'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  advancedMode: {
    type: Boolean,
    default: false,
  },
  availableTypes: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['close', 'add'])

// Form state (reset every time the modal opens)
const form = ref({
  name: '',
  type: 'string',
  title: '',
  description: '',
})

// Template ref for the name input — Phase 0 auto-focus fix (preserved)
const propertyNameInput = ref(null)

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      // Reset form on open
      form.value = { name: '', type: 'string', title: '', description: '' }
      // Auto-focus the name input (Phase 0 fix: template ref + nextTick)
      await nextTick()
      propertyNameInput.value?.focus()
    }
  },
)

const submit = () => {
  emit('add', { ...form.value })
}
</script>
