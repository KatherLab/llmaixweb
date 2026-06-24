<template>
  <div
    v-if="failures && Object.keys(failures).length"
    class="bg-red-50 border border-red-200 rounded-xl p-5 mb-6"
  >
    <div class="flex items-center gap-2 mb-2">
      <svg class="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span class="font-semibold text-red-700"
        >{{ Object.keys(failures).length }} document error{{
          Object.keys(failures).length === 1 ? '' : 's'
        }}</span
      >
    </div>
    <details class="mt-1">
      <summary class="text-sm text-red-700 cursor-pointer">View error details</summary>
      <ul class="list-disc list-inside mt-2 text-sm text-red-800">
        <li v-for="(err, docId) in failures" :key="docId">
          <span class="font-semibold">Doc {{ docId }}:</span> {{ err }}
        </li>
      </ul>
    </details>
  </div>
</template>

<script setup>
defineProps({
  failures: {
    type: Object,
    default: () => ({}),
  },
})
</script>
