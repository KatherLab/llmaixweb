<template>
  <div class="mb-4">
    <label :class="labelClass">Prompt <span class="text-red-500">*</span></label>
    <select v-model="model" :class="selectClass" @change="emit('change')">
      <option disabled value="">Select a prompt</option>
      <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id.toString()">
        {{ prompt.name }}
      </option>
    </select>
    <details class="mt-1 text-xs">
      <summary class="text-blue-700 dark:text-blue-400 cursor-pointer hover:underline">
        Preview Prompt
      </summary>
      <div
        v-if="selectedPrompt"
        class="mt-2 bg-slate-50 dark:bg-slate-800 border dark:border-slate-700 rounded p-2"
      >
        <p v-if="selectedPrompt.description" class="mb-1 text-slate-600 dark:text-slate-400">
          {{ selectedPrompt.description }}
        </p>
        <div
          v-if="selectedPrompt.system_prompt"
          class="font-mono text-xs mb-1 text-slate-700 dark:text-slate-300"
        >
          Sys: {{ selectedPrompt.system_prompt }}
        </div>
        <div
          v-if="selectedPrompt.user_prompt"
          class="font-mono text-xs text-slate-700 dark:text-slate-300"
        >
          User: {{ selectedPrompt.user_prompt }}
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
