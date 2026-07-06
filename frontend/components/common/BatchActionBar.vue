<template>
  <div v-if="count > 0" class="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50">
    <div
      class="bg-slate-900 dark:bg-slate-800 text-white rounded-modal shadow-2xl px-6 py-3 flex items-center space-x-4"
    >
      <span class="font-medium"
        >{{ count }} {{ countLabel || 'item' }}{{ count !== 1 ? 's' : '' }} selected</span
      >

      <!-- Optional warning chip (e.g. "needs config") -->
      <slot name="warning" />

      <!-- Close / clear affordance -->
      <BaseButton variant="icon" tone="gray" aria-label="Clear selection" @click="emit('clear')">
        <X class="w-4 h-4" />
      </BaseButton>

      <div class="w-px h-5 bg-slate-700 dark:bg-slate-600" />

      <!-- Action buttons -->
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { X } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'

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
