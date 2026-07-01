<template>
  <div
    class="mt-2 bg-slate-50 dark:bg-slate-800 border dark:border-slate-700 rounded-lg p-4 grid gap-6"
  >
    <div>
      <label :class="labelClass">
        Max Completion Tokens <span class="text-slate-400 font-normal">(optional)</span>
      </label>
      <input
        v-model="maxCompletionTokens"
        :class="inputClass"
        min="1"
        placeholder="e.g., 4096"
        type="number"
      />
      <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Limit the maximum tokens for model responses. Leave empty to use model defaults.
      </p>
    </div>
    <div>
      <label :class="labelClass">
        Temperature <span class="text-slate-400 font-normal">(optional)</span>
      </label>
      <input
        v-model="temperature"
        :class="inputClass"
        min="0"
        max="2"
        step="0.01"
        placeholder="e.g., 0.7"
        type="number"
      />
      <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Controls randomness. Lower values make outputs more focused; higher values make them more
        random. Typical: 0.0–1.0
      </p>
    </div>
    <div>
      <label :class="labelClass">
        Reasoning Effort <span class="text-slate-400 font-normal">(optional)</span>
      </label>
      <select v-model="reasoningEffort" :class="selectClass">
        <option value="">Use model default</option>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>
      <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Hints the model how much compute to spend on chain-of-thought/reasoning. Not all models/APIs
        support this.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'

const maxCompletionTokens = defineModel<string>('maxCompletionTokens', { default: '' })
const temperature = defineModel<string>('temperature', { default: '' })
const reasoningEffort = defineModel<string>('reasoningEffort', { default: '' })
</script>
