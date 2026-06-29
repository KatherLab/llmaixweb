<template>
  <div>
    <label class="block text-sm font-semibold text-slate-700 mb-1"
      >LLM Model <span class="text-red-500">*</span></label
    >
    <select
      v-model="model"
      :disabled="isLoadingModels || isTestingConnection || availableModels.length === 0"
      class="w-full border border-slate-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-100"
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
    <div v-if="configStatus?.type === 'error'" class="text-xs text-red-500 mt-1">
      {{ configStatus.message }}
    </div>
  </div>
</template>

<script setup>
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

const model = defineModel({ type: String, default: '' })
</script>
