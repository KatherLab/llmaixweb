<!-- src/components/EmptyState.vue -->
<script setup lang="ts">
import { Plus } from '@lucide/vue'
import Tooltip from '@/components/common/Tooltip.vue'
import BaseButton from '@/components/common/BaseButton.vue'

/**
 * Shared empty-state block: icon + title + description + optional action.
 *
 * Slots:
 *  - icon    : custom icon (defaults to a "+" icon)
 *  - default : rich description/body content (overrides the `description` prop)
 *
 * The action button only renders when `actionText` is set, so the component
 * also covers no-action empty states (icon + text only).
 */
interface Props {
  title: string
  description?: string
  actionText?: string
  disabled?: boolean
  disabledReason?: string
}

withDefaults(defineProps<Props>(), {
  description: '',
  actionText: '',
  disabled: false,
  disabledReason: '',
})

const emit = defineEmits<{ (e: 'action'): void }>()
</script>

<template>
  <div
    class="text-center p-12 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-dashed border-slate-300 dark:border-slate-600"
  >
    <slot name="icon">
      <!-- Default icon if no custom icon is provided -->
      <Plus class="h-12 w-12 mx-auto text-slate-400 dark:text-slate-500" aria-hidden="true" />
    </slot>
    <h3 class="mt-4 text-lg font-medium text-slate-900 dark:text-slate-100">{{ title }}</h3>
    <p v-if="description" class="mt-1 text-sm text-slate-500 dark:text-slate-400">
      {{ description }}
    </p>
    <slot />
    <div v-if="actionText || $slots.action" class="mt-6 flex flex-col items-center">
      <slot name="action">
        <Tooltip v-if="disabled && disabledReason" :text="disabledReason">
          <BaseButton variant="primary" :disabled="disabled" @click="emit('action')">
            {{ actionText }}
          </BaseButton>
        </Tooltip>
        <BaseButton v-else variant="primary" :disabled="disabled" @click="emit('action')">
          {{ actionText }}
        </BaseButton>
      </slot>
    </div>
  </div>
</template>
