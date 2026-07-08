<template>
  <BaseModal :open="open" title="Rename Trial" size="sm" body-class="p-6" @close="$emit('close')">
    <label :class="labelClass">Name</label>
    <input v-model="name" maxlength="100" :class="[inputClass, 'mb-3']" />
    <label :class="labelClass">Description</label>
    <textarea v-model="description" maxlength="512" :class="[textareaClass, 'mb-3']" rows="2" />
    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">Cancel</BaseButton>
      <BaseButton variant="primary" :disabled="!name.trim()" @click="submit">Save</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch, type PropType } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { inputClass, textareaClass, labelClass } from '@/utils/formStyles'
import { trialLabel } from '@/utils/trialLabel'
import type { TrialSummary } from '@/types'

interface RenamePayload {
  id: number
  name: string
  description: string
}

const props = defineProps({
  open: { type: Boolean, default: false },
  trial: { type: Object as PropType<Partial<TrialSummary> | null>, default: () => ({}) },
})
const emit = defineEmits<{
  close: []
  rename: [payload: RenamePayload]
}>()

const name = ref('')
const description = ref('')

watch(
  () => props.trial,
  (t) => {
    name.value = trialLabel(t, t?.id)
    description.value = t?.description || ''
  },
  { immediate: true },
)

function submit(): void {
  emit('rename', {
    id: props.trial?.id ?? 0,
    name: name.value.trim(),
    description: description.value.trim(),
  })
}
</script>
