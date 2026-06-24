<template>
  <div
    class="mb-8 bg-gradient-to-br from-blue-50 to-gray-50 rounded-xl border border-blue-100 shadow flex items-center px-6 py-5 gap-4"
  >
    <div class="flex-shrink-0">
      <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
        />
      </svg>
    </div>
    <div class="w-full">
      <div class="grid grid-cols-1 gap-4">
        <div>
          <label class="block text-xs font-semibold text-gray-700 mb-1 tracking-wide"
            >Trial Name <span class="text-gray-400 font-normal">(optional)</span></label
          >
          <input
            v-model="name"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
            maxlength="100"
            placeholder="E.g. Contract Extraction Run Q3"
          />
        </div>
        <div>
          <label class="block text-xs font-semibold text-gray-700 mb-1 tracking-wide"
            >Description <span class="text-gray-400 font-normal">(optional)</span></label
          >
          <textarea
            v-model="description"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
            maxlength="512"
            placeholder="Short summary for this trial (e.g. doc type, goal, changes etc)"
            rows="2"
          ></textarea>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const name = defineModel('name', { type: String, default: '' })
const description = defineModel('description', { type: String, default: '' })
</script>
