<template>
  <div
    class="mt-2 bg-slate-50 dark:bg-slate-800 border dark:border-slate-700 rounded-card p-4 grid gap-6"
  >
    <FormField
      v-model="apiKey"
      label="API Key"
      type="password"
      maxlength="512"
      placeholder="e.g., sk-1234567890abcdef..."
      autocomplete="off"
    />
    <FormField
      v-model="baseUrl"
      label="Base URL"
      type="text"
      maxlength="512"
      placeholder="e.g., https://api.openai.com/v1"
      autocomplete="off"
    />
  </div>
</template>

<script setup lang="ts">
import FormField from '@/components/common/FormField.vue'

const apiKey = defineModel<string>('apiKey', { default: '' })
const baseUrl = defineModel<string>('baseUrl', { default: '' })
</script>
