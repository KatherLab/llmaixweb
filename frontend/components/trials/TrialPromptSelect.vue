<template>
  <div class="mb-4">
    <label class="block text-sm font-semibold text-gray-700 mb-1"
      >Prompt <span class="text-red-500">*</span></label
    >
    <select
      v-model="model"
      class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
      @change="emit('change')"
    >
      <option disabled value="">Select a prompt</option>
      <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id.toString()">
        {{ prompt.name }}
      </option>
    </select>
    <details class="mt-1 text-xs">
      <summary class="text-blue-700 cursor-pointer">Preview Prompt</summary>
      <div v-if="selectedPrompt" class="mt-2 bg-gray-50 border rounded p-2">
        <p v-if="selectedPrompt.description" class="mb-1 text-gray-600">
          {{ selectedPrompt.description }}
        </p>
        <div v-if="selectedPrompt.system_prompt" class="font-mono text-xs mb-1">
          Sys: {{ selectedPrompt.system_prompt }}
        </div>
        <div v-if="selectedPrompt.user_prompt" class="font-mono text-xs">
          User: {{ selectedPrompt.user_prompt }}
        </div>
      </div>
    </details>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  prompts: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['change'])

const model = defineModel({ type: String, default: '' })

const selectedPrompt = computed(() => {
  if (!model.value) return null
  return props.prompts.find((prompt) => prompt.id.toString() === model.value)
})
</script>
