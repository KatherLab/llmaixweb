<template>
  <div class="bg-white border-b px-4 py-3 flex items-center justify-between">
    <div class="flex items-center space-x-4">
      <!-- Navigation Breadcrumb -->
      <nav class="flex items-center space-x-2 text-sm">
        <button
          type="button"
          class="text-gray-600 hover:text-gray-900 font-medium"
          @click="$emit('navigate-to-root')"
        >
          Root
        </button>
        <template v-for="(segment, index) in navigationPath" :key="index">
          <svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5l7 7-7 7"
            />
          </svg>
          <button
            type="button"
            class="text-gray-600 hover:text-gray-900 font-medium"
            @click="$emit('navigate-to-path', index)"
          >
            {{ segment }}
          </button>
        </template>
      </nav>
    </div>

    <!-- Quick Actions -->
    <div class="flex items-center space-x-2">
      <button
        type="button"
        class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
        title="Help"
        @click="$emit('show-help')"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  navigationPath: {
    type: Array,
    default: () => [],
  },
})

defineEmits(['navigate-to-root', 'navigate-to-path', 'show-help'])
</script>
