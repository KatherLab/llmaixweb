<template>
  <div>
    <div class="flex items-center gap-1 mb-1.5">
      <label :class="labelClass" for="trial-model-select"
        >LLM Model <span class="text-red-500">*</span></label
      >
      <Tooltip :text="modelHelpText">
        <Info class="h-4 w-4 text-content-subtle hover:text-content-muted" />
      </Tooltip>
    </div>
    <select
      id="trial-model-select"
      v-model="model"
      :disabled="isLoadingModels || isTestingConnection || (availableModels ?? []).length === 0"
      :class="[selectClass, 'disabled:opacity-60 disabled:cursor-not-allowed']"
    >
      <option disabled value="">
        {{
          isLoadingModels || isTestingConnection
            ? 'Loading models...'
            : (availableModels ?? []).length === 0
              ? 'No models available'
              : 'Select a model'
        }}
      </option>
      <option v-for="mdl in availableModels ?? []" :key="mdl" :value="mdl">
        {{ mdl }}
      </option>
    </select>
    <p class="mt-1 text-xs text-content-muted">
      Models are loaded from your configured LLM provider. Not all models support structured JSON
      output — the compatibility test below verifies your chosen model works with the selected
      schema before you run the trial.
    </p>
    <div v-if="configStatus?.type === 'error'" class="text-xs text-red-500 mt-1">
      {{ configStatus.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { Info } from '@lucide/vue'
import Tooltip from '@/components/common/Tooltip.vue'
import { selectClass, labelClass } from '@/utils/formStyles'

interface StatusDescriptor {
  type: 'loading' | 'warning' | 'error' | 'success' | 'none'
  message: string
}

withDefaults(
  defineProps<{
    availableModels?: string[]
    isLoadingModels?: boolean
    isTestingConnection?: boolean
    configStatus?: StatusDescriptor
  }>(),
  {
    availableModels: () => [],
    isLoadingModels: false,
    isTestingConnection: false,
    configStatus: () => ({ type: 'none', message: '' }),
  },
)

const modelHelpText =
  'The AI model used for extraction. Models are fetched from your LLM provider (system default or your custom API settings). The list shows raw model IDs from the provider; use the compatibility test to confirm a model can produce structured output matching your schema.'

const model = defineModel<string>({ default: '' })
</script>
