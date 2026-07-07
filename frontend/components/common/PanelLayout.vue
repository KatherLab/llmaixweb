<!--
  Multi-pane layout with a toggle-chip bar.

  Replaces the "Split / Source / Result" segmented control: instead of mixing
  layout modes with content names, each available panel is a chip you click on
  to add/remove. Active panels flow side-by-side (1 → N panes), so you can see
  source + result + reasoning simultaneously. No hidden state.

  Props:
    - panels      : the full menu, in chip order: [{ key, label, icon? }]
    - modelValue  : active panel keys, in left-to-right order (v-model)
    - maxVisible  : optional cap on simultaneously visible panes (default 0 = no cap)
    - paneMinWidth: Tailwind min-width class for each pane (default 'min-w-[280px]')

  Slots: one scoped slot per panel key, named `pane-<key>`, rendered only when
  that panel is active. Each slot receives no props — the parent owns content.

  Emits: update:modelValue (on every toggle).
-->
<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- Chip bar -->
    <div
      class="flex items-center gap-2 px-3 py-1.5 border-b border-default bg-surface shrink-0 flex-wrap"
    >
      <div class="inline-flex items-center gap-1 bg-surface-sunken rounded-card p-1 flex-wrap">
        <button
          v-for="panel in panels"
          :key="panel.key"
          type="button"
          :disabled="!isActive(panel.key) && atCapacity"
          :title="
            !isActive(panel.key) && atCapacity
              ? `Close another panel first (max ${maxVisible})`
              : isActive(panel.key)
                ? `Hide ${panel.label}`
                : `Show ${panel.label}`
          "
          :class="[
            'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-card transition-all',
            isActive(panel.key)
              ? 'bg-surface text-content shadow-sm'
              : atCapacity
                ? 'text-content-subtle cursor-not-allowed opacity-50'
                : 'text-content-muted hover:text-content',
          ]"
          @click="toggle(panel.key)"
        >
          <component :is="panel.icon" v-if="panel.icon" class="h-3.5 w-3.5" />
          <span
            v-else
            class="h-1.5 w-1.5 rounded-full"
            :class="isActive(panel.key) ? 'bg-primary' : 'bg-content-subtle'"
          />
          {{ panel.label }}
        </button>
      </div>
      <span class="text-[11px] text-content-subtle ml-auto">
        {{ active.length }} panel{{ active.length === 1 ? '' : 's' }}
      </span>
    </div>

    <!-- Panes -->
    <div
      class="panel-grid flex-1 min-h-0 grid gap-px bg-default"
      :style="{ '--cols': active.length || 1 }"
    >
      <div
        v-for="key in active"
        :key="key"
        :class="['flex flex-col min-h-0 min-w-0 bg-surface overflow-hidden', paneMinWidth]"
      >
        <slot :name="`pane-${key}`" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'

export interface PanelOption {
  key: string
  label: string
  icon?: Component
}

interface Props {
  panels: PanelOption[]
  modelValue: string[]
  maxVisible?: number
  paneMinWidth?: string
}

const props = withDefaults(defineProps<Props>(), {
  maxVisible: 0,
  paneMinWidth: 'min-w-[280px]',
})

const emit = defineEmits<{ (e: 'update:modelValue', value: string[]): void }>()

const active = computed(() => props.modelValue.filter((k) => props.panels.some((p) => p.key === k)))

const atCapacity = computed(() => props.maxVisible > 0 && active.value.length >= props.maxVisible)

function isActive(key: string): boolean {
  return active.value.includes(key)
}

function toggle(key: string): void {
  if (isActive(key)) {
    // Don't remove the last remaining panel — always keep at least one.
    if (active.value.length <= 1) return
    emit(
      'update:modelValue',
      active.value.filter((k) => k !== key),
    )
  } else {
    if (atCapacity.value) return
    emit('update:modelValue', [...active.value, key])
  }
}
</script>

<style scoped>
/* Stack panes on small screens, side-by-side at lg+ (--cols = active count). */
.panel-grid {
  grid-template-columns: 1fr;
}
@media (min-width: 1024px) {
  .panel-grid {
    grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
  }
}
</style>
