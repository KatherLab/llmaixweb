<template>
  <BaseModal :open="open" title="Rename Trial" size="sm" body-class="p-6" @close="$emit('close')">
    <label :class="labelClass">Name</label>
    <input v-model="name" maxlength="100" :class="[inputClass, 'mb-3']" />
    <label :class="labelClass">Description</label>
    <textarea v-model="description" maxlength="512" :class="[textareaClass, 'mb-3']" rows="2" />
    <template #footer>
      <BaseButton variant="secondary" size="sm" @click="$emit('close')">Cancel</BaseButton>
      <BaseButton variant="primary" size="sm" :disabled="!name.trim()" @click="submit"
        >Save</BaseButton
      >
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { inputClass, textareaClass, labelClass } from '@/utils/formStyles'

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
