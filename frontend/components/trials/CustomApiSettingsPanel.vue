<template>
  <div class="mt-2 bg-gray-50 border rounded-lg p-4 grid gap-6">
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
      <input
        v-model="apiKey"
        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        placeholder="e.g., sk-1234567890abcdef..."
        type="password"
        autocomplete="off"
      />
    </div>
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
      <input
        v-model="baseUrl"
        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        placeholder="e.g., https://api.openai.com/v1"
        type="text"
        autocomplete="off"
      />
    </div>
  </div>
</template>

<script setup>
const apiKey = defineModel('apiKey', { type: String, default: '' })
const baseUrl = defineModel('baseUrl', { type: String, default: '' })
</script>
