<template>
  <BaseModal :open="open" title="Trial Prompt" size="lg" body-class="p-6" @close="$emit('close')">
    <div class="mb-2">
      <div class="flex items-center gap-2">
        <h4 class="font-semibold">{{ prompt?.name }}</h4>
        <span
          v-if="isSnapshot"
          :class="['text-[10px] uppercase tracking-wide px-2 py-0.5 rounded', getPillClass('blue')]"
          title="Frozen copy of the prompt as it was when the trial ran"
          >Snapshot</span
        >
      </div>
      <p v-if="prompt?.description" class="text-sm text-slate-600">{{ prompt.description }}</p>
    </div>
    <div class="mb-3">
      <label class="block font-medium text-slate-700 mb-1">System Prompt</label>
      <pre class="bg-slate-50 border rounded-md p-3 overflow-x-auto text-xs font-mono max-h-32">{{
        prompt?.system_prompt || '-'
      }}</pre>
    </div>
    <div class="mb-3">
      <label class="block font-medium text-slate-700 mb-1">User Prompt</label>
      <pre class="bg-slate-50 border rounded-md p-3 overflow-x-auto text-xs font-mono max-h-32">{{
        prompt?.user_prompt || '-'
      }}</pre>
    </div>
    <template #footer>
      <BaseButton variant="primary" @click="copyPrompt">Copy</BaseButton>
    </template>
  </BaseModal>
</template>
<script setup>
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { getPillClass } from '@/utils/statusStyles'

const props = defineProps({
  open: Boolean,
  prompt: { type: Object, default: () => ({}) },
  isSnapshot: { type: Boolean, default: false },
})
defineEmits(['close'])

const toast = useToast()

function copyPrompt() {
  if (!props.prompt) return
  const text = `System Prompt:\n${props.prompt.system_prompt || '-'}\n\nUser Prompt:\n${props.prompt.user_prompt || '-'}`
  navigator.clipboard.writeText(text)
  toast.success('Prompt copied!')
}
</script>
