<template>
  <BaseModal :open="open" size="xl" body-class="p-6" @close="emit('close')">
    <template #header>
      <div>
        <div class="flex items-center gap-2">
          <h3 class="text-lg font-medium text-content">
            {{ prompt?.name }}
          </h3>
          <span
            v-if="isSnapshot"
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded',
              getPillClass('blue'),
            ]"
            title="Frozen copy of the prompt as it was when the trial ran"
            >Snapshot</span
          >
        </div>
        <p v-if="prompt?.description" class="mt-1 text-sm text-content-muted">
          {{ prompt.description }}
        </p>
      </div>
    </template>

    <div class="space-y-4">
      <div v-if="prompt?.system_prompt" class="bg-surface-muted rounded-card p-4">
        <h4 class="text-sm font-medium text-content-muted mb-2">System Prompt</h4>
        <pre class="text-sm text-content-muted whitespace-pre-wrap">{{ prompt.system_prompt }}</pre>
      </div>
      <div v-if="prompt?.user_prompt" class="bg-primary-soft rounded-card p-4">
        <h4 class="text-sm font-medium text-primary mb-2">User Prompt</h4>
        <pre class="text-sm text-content-muted whitespace-pre-wrap">{{ prompt.user_prompt }}</pre>
      </div>
    </div>

    <template #footer>
      <BaseButton v-if="copyable" variant="primary" @click="copyPrompt">Copy</BaseButton>
      <BaseButton variant="secondary" @click="emit('close')">Close</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { getPillClass } from '@/utils/statusStyles'
import type { Prompt } from '@/types'

interface Props {
  open: boolean
  prompt?: Prompt | null
  isSnapshot?: boolean
  copyable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  prompt: null,
  isSnapshot: false,
  copyable: true,
})

const emit = defineEmits<{
  close: []
}>()

const toast = useToast()

function copyPrompt() {
  if (!props.prompt) return
  const text = `System Prompt:\n${props.prompt.system_prompt || '-'}\n\nUser Prompt:\n${
    props.prompt.user_prompt || '-'
  }`
  navigator.clipboard.writeText(text)
  toast.success('Prompt copied!')
}
</script>
