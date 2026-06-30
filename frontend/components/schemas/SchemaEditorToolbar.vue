<template>
  <div
    class="bg-white dark:bg-slate-800 border-b dark:border-slate-700 px-4 py-3 flex items-center justify-between"
  >
    <div class="flex items-center space-x-4">
      <!-- Navigation Breadcrumb -->
      <nav class="flex items-center space-x-2 text-sm">
        <button
          type="button"
          class="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white font-medium"
          @click="$emit('navigate-to-root')"
        >
          Root
        </button>
        <template v-for="(segment, index) in navigationPath" :key="index">
          <ChevronRight class="h-4 w-4 text-slate-400 dark:text-slate-500" />
          <button
            type="button"
            class="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white font-medium"
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
        class="p-2 text-slate-500 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700 hover:text-slate-700 hover:bg-slate-100 rounded-lg"
        title="Help"
        @click="$emit('show-help')"
      >
        <CircleHelp class="h-5 w-5" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ChevronRight, CircleHelp } from '@lucide/vue'

defineProps({
  navigationPath: {
    type: Array,
    default: () => [],
  },
})

defineEmits(['navigate-to-root', 'navigate-to-path', 'show-help'])
</script>
