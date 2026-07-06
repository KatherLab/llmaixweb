<template>
  <div v-if="count > 0" class="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50">
    <div
      class="bg-inverse-surface text-inverse-content border border-inverse-border rounded-modal shadow-2xl px-6 py-3 flex items-center space-x-4"
    >
      <span class="font-medium"
        >{{ count }} {{ countLabel || 'item' }}{{ count !== 1 ? 's' : '' }} selected</span
      >

      <!-- Optional warning chip (e.g. "needs config") -->
      <slot name="warning" />

      <!-- Close / clear affordance -->
      <button
        type="button"
        aria-label="Clear selection"
        class="p-1.5 rounded-card text-inverse-muted hover:text-inverse-content hover:bg-inverse-border/50 transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
        @click="emit('clear')"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="w-px h-5 bg-inverse-border" />

      <!-- Action buttons -->
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { X } from '@lucide/vue'

interface Props {
  /** Number of selected items. The bar only renders when > 0. */
  count: number
  /** Noun label for the selection count, e.g. "files" / "documents" / "trials". */
  countLabel?: string
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'clear'): void
}>()
</script>
