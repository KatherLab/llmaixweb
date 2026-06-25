<script setup>
/**
 * Sticky page header bar: icon badge + title + actions slot.
 *
 * Collapses the near-identical header markup that was duplicated across
 * ProjectOverview, AdminUserManagement, etc.
 */
defineProps({
  title: { type: String, required: true },
  // Max width container: 'sm'|'md'|'lg'|'xl'|'2xl'|'3xl'|'7xl'
  maxWidth: { type: String, default: '7xl' },
})
</script>

<template>
  <header class="sticky top-0 z-30 bg-white dark:bg-slate-900 shadow-lg flex-shrink-0">
    <div
      :class="['max-w-' + maxWidth, 'mx-auto flex justify-between items-center py-2 px-4 sm:px-6']"
    >
      <div class="flex items-center gap-2">
        <div
          v-if="$slots.icon"
          class="bg-blue-100 dark:bg-slate-800 text-blue-500 dark:text-blue-400 rounded-full p-1.5 shadow"
        >
          <slot name="icon" />
        </div>
        <h1 class="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">{{ title }}</h1>
      </div>
      <div class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
