<!-- src/components/ProjectSettingsModal.vue -->
<template>
  <BaseModal :open="open" title="Project Settings" size="md" body-class="p-8" @close="emitClose">
    <!-- General Settings Section -->
    <div class="mb-6">
      <h3
        class="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide mb-3"
      >
        General
      </h3>
      <input
        v-model="name"
        :class="[inputClass, 'text-lg font-semibold mb-3']"
        placeholder="Project Name"
        maxlength="100"
        autofocus
      />
      <textarea
        v-model="description"
        :class="textareaClass"
        rows="3"
        maxlength="500"
        placeholder="Description (optional)"
      ></textarea>
    </div>

    <!-- Danger Zone Section -->
    <div class="border-t border-slate-200 dark:border-slate-700 pt-6 mt-6">
      <h3 class="text-sm font-semibold text-red-700 dark:text-red-400 uppercase tracking-wide mb-3">
        Danger Zone
      </h3>
      <div
        class="bg-red-50 dark:bg-red-900/30 rounded-lg p-4 border border-red-200 dark:border-red-800"
      >
        <p class="text-sm text-red-700 dark:text-red-400 mb-3">
          Once you delete a project, there is no going back. Please be certain.
        </p>
        <BaseButton variant="danger" class="w-full" @click="onDeleteClick">
          <Trash2 class="w-4 h-4" />
          Delete Project
        </BaseButton>
      </div>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="emitClose"> Cancel </BaseButton>
      <BaseButton :loading="isSaving" :disabled="isSaving" @click="onSave">
        Save Changes
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Trash2 } from '@lucide/vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { inputClass, textareaClass } from '@/utils/formStyles'

const props = defineProps({
  open: Boolean,
  initialName: { type: String, default: '' },
  initialDescription: { type: String, default: '' },
  isSaving: Boolean,
})
const emit = defineEmits(['save', 'close', 'delete'])

const name = ref(props.initialName || '')
const description = ref(props.initialDescription || '')

// Sync props changes
watch(
  () => [props.initialName, props.initialDescription],
  ([newName, newDesc]) => {
    name.value = newName || ''
    description.value = newDesc || ''
  },
)

// Emit save event with form data
function onSave() {
  emit('save', { name: name.value, description: description.value })
}

// Emit close event
function emitClose() {
  if (!props.isSaving) {
    emit('close')
  }
}

// Emit delete event
function onDeleteClick() {
  emit('delete')
}

onMounted(() => {
  if (props.open) {
    setTimeout(() => document.querySelector('input[autofocus]')?.focus(), 10)
  }
})
</script>
