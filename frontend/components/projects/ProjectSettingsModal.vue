<!-- src/components/ProjectSettingsModal.vue -->
<template>
  <BaseModal :open="open" title="Project Settings" size="md" body-class="p-8" @close="emitClose">
    <!-- General Settings Section -->
    <div class="mb-6">
      <h3 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">General</h3>
      <input
        v-model="name"
        class="w-full px-4 py-2 text-lg font-semibold rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-400 mb-3"
        placeholder="Project Name"
        autofocus
      />
      <textarea
        v-model="description"
        class="w-full px-4 py-2 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-400"
        rows="3"
        placeholder="Description (optional)"
      ></textarea>
    </div>

    <!-- Danger Zone Section -->
    <div class="border-t border-gray-200 pt-6 mt-6">
      <h3 class="text-sm font-semibold text-red-700 uppercase tracking-wide mb-3">Danger Zone</h3>
      <div class="bg-red-50 rounded-lg p-4 border border-red-200">
        <p class="text-sm text-red-700 mb-3">
          Once you delete a project, there is no going back. Please be certain.
        </p>
        <button
          type="button"
          class="w-full px-4 py-2 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 transition shadow-sm flex items-center justify-center"
          @click="onDeleteClick"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 7l-.867 16.141A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          Delete Project
        </button>
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
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

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
