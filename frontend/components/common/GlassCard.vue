<script setup lang="ts">
/**
 * Section card: opaque panel with border + shadow.
 *
 * Previously a glassmorphism (translucent + backdrop-blur) surface, but that
 * clashed with the otherwise flat, opaque design language used by BaseModal,
 * DataTable, FilterBar, etc. Flattened to a token-backed surface so the whole
 * app shares one surface treatment.
 */
interface Props {
  // Padding scale: 'sm' (p-4 sm:p-5) | 'lg' (p-6 sm:p-8)
  padding?: 'sm' | 'lg'
  // Rounded corner scale: 'card' (rounded-card) | 'modal' (rounded-modal)
  rounded?: 'card' | 'modal'
}

withDefaults(defineProps<Props>(), {
  padding: 'sm',
  rounded: 'card',
})
</script>

<template>
  <section
    :class="[
      'flex-1 min-h-0 relative transition-all border border-default bg-surface',
      rounded === 'modal' ? 'rounded-modal shadow-lg' : 'rounded-card shadow-sm',
      padding === 'lg' ? 'p-6 sm:p-8' : 'p-4 sm:p-5',
    ]"
  >
    <slot />
  </section>
</template>
