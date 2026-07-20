<!-- src/components/ProjectSettingsModal.vue -->
<template>
  <BaseModal :open="open" title="Project Settings" size="md" body-class="p-8" @close="emitClose">
    <!-- General Settings Section -->
    <div class="mb-6">
      <h3 class="text-sm font-semibold text-content-muted uppercase tracking-wide mb-3">General</h3>
      <div class="mb-3">
        <input
          v-model="name"
          :class="[
            inputClass,
            'text-lg font-semibold',
            nameError ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800' : '',
          ]"
          placeholder="Project Name"
          maxlength="100"
          required
          autofocus
          :aria-invalid="!!nameError"
        />
        <p v-if="nameError" class="mt-1 text-sm text-red-600 dark:text-red-400">
          {{ nameError }}
        </p>
      </div>
      <textarea
        v-model="description"
        :class="textareaClass"
        rows="3"
        maxlength="500"
        placeholder="Description (optional)"
      ></textarea>
    </div>

    <!-- Danger Zone Section -->
    <div class="border-t border-default pt-6 mt-6">
      <h3 class="text-sm font-semibold text-red-700 dark:text-red-400 uppercase tracking-wide mb-3">
        Danger Zone
      </h3>
      <Callout variant="danger">
        <p class="text-sm mb-3">Once you delete a project, there is no going back. Be certain.</p>
        <BaseButton variant="danger" class="w-full" @click="onDeleteClick">
          <Trash2 class="w-4 h-4" />
          Delete Project
        </BaseButton>
      </Callout>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="emitClose"> Cancel </BaseButton>
      <BaseButton :loading="isSaving" :disabled="isSaving" @click="onSave">
        Save Changes
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { Trash2 } from '@lucide/vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { inputClass, textareaClass } from '@/utils/formStyles'
import type { ProjectUpdate } from '@/types'

interface Props {
  open: boolean
  initialName?: string
  initialDescription?: string
  isSaving?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  initialName: '',
  initialDescription: '',
  isSaving: false,
})

const emit = defineEmits<{
  save: [payload: ProjectUpdate]
  close: []
  delete: []
}>()

const name = ref(props.initialName || '')
const description = ref(props.initialDescription || '')
const nameError = ref('')

// Sync props changes
watch(
  () => [props.initialName, props.initialDescription] as const,
  ([newName, newDesc]) => {
    name.value = newName || ''
    description.value = newDesc || ''
    nameError.value = ''
  },
)

// Clear the validation error as soon as the user types a non-empty name.
watch(name, (v) => {
  if (v.trim()) nameError.value = ''
})

// Emit save event with form data (name is required — never emit an empty one)
function onSave(): void {
  const trimmedName = name.value.trim()
  if (!trimmedName) {
    nameError.value = 'Project name is required'
    return
  }
  nameError.value = ''
  emit('save', { name: trimmedName, description: description.value.trim() })
}

// Emit close event
function emitClose(): void {
  if (!props.isSaving) {
    emit('close')
  }
}

// Emit delete event
function onDeleteClick(): void {
  emit('delete')
}

onMounted(() => {
  if (props.open) {
    setTimeout(() => document.querySelector<HTMLInputElement>('input[autofocus]')?.focus(), 10)
  }
})
</script>
