<template>
  <div class="mt-2 bg-slate-50 border rounded-lg p-4 grid gap-6">
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1">
        Max Completion Tokens <span class="text-slate-400 font-normal">(optional)</span>
      </label>
      <input
        v-model="maxCompletionTokens"
        class="w-full border border-slate-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        min="1"
        placeholder="e.g., 4096"
        type="number"
      />
      <p class="mt-1 text-xs text-slate-500">
        Limit the maximum tokens for model responses. Leave empty to use model defaults.
      </p>
    </div>
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1">
        Temperature <span class="text-slate-400 font-normal">(optional)</span>
      </label>
      <input
        v-model="temperature"
        class="w-full border border-slate-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        min="0"
        max="2"
        step="0.01"
        placeholder="e.g., 0.7"
        type="number"
      />
      <p class="mt-1 text-xs text-slate-500">
        Controls randomness. Lower values make outputs more focused; higher values make them more
        random. Typical: 0.0–1.0
      </p>
    </div>
    <div>
      <label class="block text-sm font-medium text-slate-700 mb-1">
        Reasoning Effort <span class="text-slate-400 font-normal">(optional)</span>
      </label>
      <select
        v-model="reasoningEffort"
        class="w-full border border-slate-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">Use model default</option>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>
      <p class="mt-1 text-xs text-slate-500">
        Hints the model how much compute to spend on chain-of-thought/reasoning. Not all models/APIs
        support this.
      </p>
    </div>
  </div>
</template>

<script setup>
const maxCompletionTokens = defineModel('maxCompletionTokens', { type: String, default: '' })
const temperature = defineModel('temperature', { type: String, default: '' })
const reasoningEffort = defineModel('reasoningEffort', { type: String, default: '' })
</script>
