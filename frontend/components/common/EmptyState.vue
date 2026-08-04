<!-- src/components/EmptyState.vue -->
<script setup lang="ts">
import { Plus } from '@lucide/vue'
import Tooltip from '@/components/common/Tooltip.vue'
import BaseButton from '@/components/common/BaseButton.vue'

/**
 * Shared empty-state block: icon + title + description + optional action(s).
 *
 * Slots:
 *  - icon             : custom icon (defaults to a "+" icon)
 *  - default          : rich description/body content (overrides the `description` prop)
 *  - action           : custom primary action (overrides the `actionText` button)
 *  - secondary-action : custom secondary action (overrides the `secondaryActionText` button)
 *
 * The action buttons only render when `actionText` / `secondaryActionText` are
 * set, so the component also covers no-action empty states (icon + text only).
 */
interface Props {
  title: string
  description?: string
  actionText?: string
  secondaryActionText?: string
  disabled?: boolean
  disabledReason?: string
}

withDefaults(defineProps<Props>(), {
  description: '',
  actionText: '',
  secondaryActionText: '',
  disabled: false,
  disabledReason: '',
})

const emit = defineEmits<{ (e: 'action'): void; (e: 'secondary-action'): void }>()
</script>

<template>
  <div class="text-center p-12 bg-surface-muted rounded-card border border-dashed border-strong">
    <slot name="icon">
      <!-- Default icon if no custom icon is provided -->
      <Plus class="h-12 w-12 mx-auto text-content-subtle" aria-hidden="true" />
    </slot>
    <h3 class="mt-4 text-lg font-medium text-content">{{ title }}</h3>
    <p v-if="description" class="mt-1 text-sm text-content-muted">
      {{ description }}
    </p>
    <slot />
    <div
      v-if="actionText || secondaryActionText || $slots.action || $slots['secondary-action']"
      class="mt-6 flex items-center justify-center gap-3 flex-wrap"
    >
      <slot name="action">
        <template v-if="actionText">
          <Tooltip v-if="disabled && disabledReason" :text="disabledReason">
            <!-- pointer-events-none lets hover reach the Tooltip wrapper: a
                 natively-disabled button swallows mouse events, so the tooltip
                 would otherwise never show. -->
            <BaseButton
              variant="primary"
              :disabled="disabled"
              class="pointer-events-none"
              @click="emit('action')"
            >
              {{ actionText }}
            </BaseButton>
          </Tooltip>
          <BaseButton v-else variant="primary" :disabled="disabled" @click="emit('action')">
            {{ actionText }}
          </BaseButton>
        </template>
      </slot>
      <slot name="secondary-action">
        <BaseButton
          v-if="secondaryActionText"
          variant="secondary"
          @click="emit('secondary-action')"
        >
          {{ secondaryActionText }}
        </BaseButton>
      </slot>
    </div>
  </div>
</template>
