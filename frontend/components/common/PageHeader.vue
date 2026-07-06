<script setup lang="ts">
/**
 * Sticky page header bar: icon badge + title + subtitle + actions slot.
 *
 * Collapses the near-identical header markup that was duplicated across
 * ProjectOverview, AdminUserManagement, etc.
 */
interface Props {
  title: string
  subtitle?: string
  // Max width container: 'sm'|'md'|'lg'|'xl'|'2xl'|'3xl'|'7xl'
  maxWidth?: string
  // When false, the header is not sticky (for sub-views inside a scrolling container).
  sticky?: boolean
}

withDefaults(defineProps<Props>(), {
  subtitle: '',
  maxWidth: '7xl',
  sticky: true,
})
</script>

<template>
  <header
    :class="[
      'bg-surface shadow-sm flex-shrink-0 border-b border-default',
      sticky ? 'sticky top-0 z-30' : '',
    ]"
  >
    <div
      :class="['max-w-' + maxWidth, 'mx-auto flex justify-between items-center py-3 px-4 sm:px-6']"
    >
      <div class="flex items-center gap-3 min-w-0">
        <div v-if="$slots.icon" class="bg-primary-soft text-primary rounded-card p-2 flex-shrink-0">
          <slot name="icon" />
        </div>
        <div class="min-w-0">
          <h1 class="text-xl font-bold text-content truncate">{{ title }}</h1>
          <p v-if="subtitle" class="text-sm text-content-muted truncate">{{ subtitle }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
