<template>
  <div>
    <div class="flex items-center gap-1 mb-1">
      <label class="block text-sm font-semibold text-slate-700 dark:text-slate-200"
        >LLM Model <span class="text-red-500">*</span></label
      >
      <Tooltip :text="modelHelpText">
        <Info class="h-4 w-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" />
      </Tooltip>
    </div>
    <select
      v-model="model"
      :disabled="isLoadingModels || isTestingConnection || availableModels.length === 0"
      class="w-full border border-slate-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-100 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200"
    >
      <option disabled value="">
        {{
          isLoadingModels || isTestingConnection
            ? 'Loading models...'
            : availableModels.length === 0
              ? 'No models available'
              : 'Select a model'
        }}
      </option>
      <option v-for="mdl in availableModels" :key="mdl" :value="mdl">
        {{ mdl }}
      </option>
    </select>
    <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
      Models are loaded from your configured LLM provider. Not all models support structured JSON
      output — the compatibility test below verifies your chosen model works with the selected
      schema before you run the trial.
    </p>
    <div v-if="configStatus?.type === 'error'" class="text-xs text-red-500 mt-1">
      {{ configStatus.message }}
    </div>
  </div>
</template>

<script setup>
import { Info } from '@lucide/vue'
import Tooltip from '@/components/common/Tooltip.vue'

defineProps({
  availableModels: {
    type: Array,
    default: () => [],
  },
  isLoadingModels: {
    type: Boolean,
    default: false,
  },
  isTestingConnection: {
    type: Boolean,
    default: false,
  },
  configStatus: {
    type: Object,
    default: () => ({ type: 'none', message: '' }),
  },
})

const modelHelpText =
  'The AI model used for extraction. Models are fetched from your LLM provider (system default or your custom API settings). The list shows raw model IDs from the provider; use the compatibility test to confirm a model can produce structured output matching your schema.'

const model = defineModel({ type: String, default: '' })
</script>
