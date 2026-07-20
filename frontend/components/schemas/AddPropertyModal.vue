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
      {{
        advancedMode
          ? $t('schemaEditor.add_modal.title_advanced')
          : $t('schemaEditor.add_modal.title')
      }}
    </h3>

    <form @submit.prevent="submit">
      <div class="space-y-4">
        <div>
          <label :class="labelClass" for="add-property-name">
            {{
              advancedMode
                ? $t('schemaEditor.add_modal.name_label_advanced')
                : $t('schemaEditor.add_modal.name_label')
            }}
          </label>
          <input
            id="add-property-name"
            ref="propertyNameInput"
            v-model="form.name"
            :class="[inputClass, nameError ? 'border-red-400 dark:border-red-600' : '']"
            :placeholder="$t('schemaEditor.add_modal.name_placeholder')"
            required
            :aria-invalid="!!nameError"
          />
          <p v-if="nameError" class="mt-1 text-xs text-red-600 dark:text-red-400">
            {{ nameError }}
          </p>
          <p v-else class="mt-1 text-xs text-content-muted">
            {{ $t('schemaEditor.property.key_hint') }}
          </p>
        </div>

        <div>
          <label :class="labelClass">
            {{
              advancedMode
                ? $t('schemaEditor.property.type_label_advanced')
                : $t('schemaEditor.property.type_label')
            }}
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
          <label :class="labelClass" for="add-property-title">
            {{ $t('schemaEditor.property.title_label') }}
          </label>
          <input
            id="add-property-title"
            v-model="form.title"
            :class="inputClass"
            :placeholder="$t('schemaEditor.add_modal.display_name_placeholder')"
          />
        </div>

        <div>
          <label :class="labelClass" for="add-property-description">
            {{ $t('schemaEditor.property.description_label') }}
          </label>
          <textarea
            id="add-property-description"
            v-model="form.description"
            rows="2"
            :class="textareaClass"
            :placeholder="$t('schemaEditor.add_modal.description_placeholder')"
          />
        </div>
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">{{
        $t('schemaEditor.add_modal.cancel')
      }}</BaseButton>
      <BaseButton variant="primary" :disabled="!!nameError" @click="submit">{{
        advancedMode
          ? $t('schemaEditor.add_modal.title_advanced')
          : $t('schemaEditor.add_modal.title')
      }}</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n({ useScope: 'global' })

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
  if (!name) return submitAttempted.value ? t('schemaEditor.add_modal.name_required') : null
  if (!KEY_PATTERN.test(name)) {
    return t('schemaEditor.property.key_invalid')
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
