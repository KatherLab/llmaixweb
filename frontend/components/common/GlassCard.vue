<script setup>
/**
 * Glassmorphism section card: translucent panel with blur + border.
 *
 * Replaces the verbatim `bg-white/70 dark:bg-slate-800/70 rounded-xl shadow-lg
 * p-4 sm:p-5 ... backdrop-filter: blur(8px)` wrapper duplicated across
 * ProjectOverview, AdminUserManagement, ProjectDetail, etc.
 */
defineProps({
  // Padding scale: 'sm' (p-4 sm:p-5) | 'lg' (p-6 sm:p-8)
  padding: { type: String, default: 'sm' },
  // Rounded corner scale: 'lg' (rounded-xl) | '3xl' (rounded-3xl)
  rounded: { type: String, default: 'lg' },
  // Backdrop blur strength in px (translucent glass effect).
  blur: { type: [String, Number], default: 8 },
})
</script>

<template>
  <section
    :class="[
      'flex-1 min-h-0 relative shadow-lg transition-all border border-blue-100 dark:border-slate-700',
      rounded === '3xl' ? 'rounded-3xl shadow-2xl' : 'rounded-xl shadow-lg',
      padding === 'lg' ? 'p-6 sm:p-8' : 'p-4 sm:p-5',
      'bg-white/70 dark:bg-slate-800/70',
    ]"
    :style="{ backdropFilter: `blur(${blur}px)` }"
  >
    <slot />
  </section>
</template>
