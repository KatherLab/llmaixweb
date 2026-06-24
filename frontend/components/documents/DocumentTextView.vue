<template>
  <div class="p-6">
    <div v-if="textLoading" class="flex items-center justify-center py-12 text-gray-400">
      <svg
        class="animate-spin h-6 w-6 mr-2"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        ></circle>
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
      <span>Loading text…</span>
    </div>
    <div v-else class="prose max-w-none bg-gray-50 p-4 rounded-lg" v-html="safeMarkdown" />
  </div>
</template>

<script setup>
defineProps({
  textLoading: { type: Boolean, default: false },
  safeMarkdown: { type: String, default: '' },
})
</script>
