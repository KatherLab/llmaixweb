<template>
  <BaseModal :open="open" title="Rename Trial" size="sm" body-class="p-6" @close="$emit('close')">
    <label class="block text-xs font-semibold text-gray-700 mb-1">Name</label>
    <input
      v-model="name"
      maxlength="100"
      class="w-full border border-gray-300 rounded px-2 py-1 mb-3"
    />
    <label class="block text-xs font-semibold text-gray-700 mb-1">Description</label>
    <textarea
      v-model="description"
      maxlength="512"
      class="w-full border border-gray-300 rounded px-2 py-1 mb-3"
      rows="2"
    />
    <template #footer>
      <button
        class="px-3 py-1 rounded text-gray-600 bg-gray-100 hover:bg-gray-200"
        @click="$emit('close')"
      >
        Cancel
      </button>
      <button
        :disabled="!name.trim()"
        class="px-3 py-1 rounded text-white bg-blue-600 hover:bg-blue-700"
        @click="submit"
      >
        Save
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'

const props = defineProps({
  open: Boolean,
  trial: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close', 'rename'])

const name = ref('')
const description = ref('')

watch(
  () => props.trial,
  (t) => {
    name.value = t?.name || `Trial #${t?.id}` || ''
    description.value = t?.description || ''
  },
  { immediate: true },
)

function submit() {
  emit('rename', {
    id: props.trial.id,
    name: name.value.trim(),
    description: description.value.trim(),
  })
}
</script>
