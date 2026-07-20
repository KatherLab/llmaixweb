<template>
  <div class="mb-4">
    <label :class="labelClass" for="trial-prompt-select"
      >{{ $t('trials.select.prompt_label') }} <span class="text-red-500">*</span></label
    >
    <select id="trial-prompt-select" v-model="model" :class="selectClass" @change="emit('change')">
      <option disabled value="">{{ $t('trials.select.prompt_placeholder') }}</option>
      <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id.toString()">
        {{ prompt.name }}
      </option>
    </select>
    <details class="mt-1 text-xs">
      <summary class="text-primary cursor-pointer hover:underline">
        {{ $t('trials.select.preview_prompt') }}
      </summary>
      <div
        v-if="selectedPrompt"
        class="mt-2 bg-surface-muted border border-default rounded-card p-2"
      >
        <p v-if="selectedPrompt.description" class="mb-1 text-content-muted">
          {{ selectedPrompt.description }}
        </p>
        <div v-if="selectedPrompt.system_prompt" class="font-mono text-xs mb-1 text-content-muted">
          {{ $t('trials.select.sys_prefix') }} {{ selectedPrompt.system_prompt }}
        </div>
        <div v-if="selectedPrompt.user_prompt" class="font-mono text-xs text-content-muted">
          {{ $t('trials.select.user_prefix') }} {{ selectedPrompt.user_prompt }}
        </div>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { selectClass, labelClass } from '@/utils/formStyles'
import type { Prompt } from '@/types'

const props = defineProps({
  prompts: {
    type: Array as PropType<Prompt[]>,
    default: () => [],
  },
})

const emit = defineEmits<{ change: [] }>()

const model = defineModel<string>({ default: '' })

const selectedPrompt = computed(() => {
  if (!model.value) return null
  return props.prompts.find((prompt) => prompt.id.toString() === model.value) ?? null
})
</script>
