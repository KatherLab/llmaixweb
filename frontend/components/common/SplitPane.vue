<!--
  Reusable two-pane split (e.g. original file | extracted content).

  Replaces the hand-rolled split in DocumentCompareView and the eval drawer's
  column 1, and gives the trial result viewer a shared split layout. A compact
  segmented control toggles between Split / left-only / right-only; the control
  only renders when both panes are available (`collapsible` true). When only one
  pane exists, it fills the full width with no control.

  Props:
    - leftLabel / rightLabel : pane titles shown in the top bar
    - defaultMode            : 'split' | 'left' | 'right' (initial mode)
    - collapsible            : whether to offer the single-pane toggle. Pass
                               false when one pane may be absent (e.g. no
                               previewable original file) — control is hidden
                               and the available pane fills the width.

  Slots: #left, #right.
  Emits: update:mode (so parents can persist/restore the chosen mode).
-->
<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- Mode toggle (only when both panes are available) -->
    <div
      v-if="collapsible"
      class="flex items-center justify-between gap-2 px-3 py-1.5 border-b border-default bg-surface shrink-0"
    >
      <span class="text-xs font-medium text-content-muted truncate">{{ activeLabel }}</span>
      <BaseSegmentedControl
        :model-value="mode"
        :options="modeOptions"
        size="sm"
        @update:model-value="onModeChange"
      />
    </div>

    <!-- Panes -->
    <div
      :class="[
        'flex-1 min-h-0 grid gap-px bg-default',
        mode === 'split' ? 'lg:grid-cols-2 grid-cols-1' : 'grid-cols-1',
      ]"
    >
      <div v-if="mode !== 'right'" class="flex flex-col min-h-0 min-w-0 bg-surface overflow-hidden">
        <slot name="left" />
      </div>
      <div v-if="mode !== 'left'" class="flex flex-col min-h-0 min-w-0 bg-surface overflow-hidden">
        <slot name="right" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseSegmentedControl from './BaseSegmentedControl.vue'

type SplitMode = 'split' | 'left' | 'right'

interface Props {
  leftLabel?: string
  rightLabel?: string
  defaultMode?: SplitMode
  // Controlled mode (v-model:mode). When provided, the pane is fully driven by
  // the parent and the internal toggle (if collapsible) still emits updates but
  // the parent is the source of truth.
  mode?: SplitMode
  collapsible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  leftLabel: 'Original',
  rightLabel: 'Content',
  defaultMode: 'split',
  mode: undefined,
  collapsible: true,
})

const emit = defineEmits<{ (e: 'update:mode', value: SplitMode): void }>()

// Internal state used only when no controlled `mode` is supplied.
const internalMode = ref<SplitMode>(props.defaultMode)

const mode = computed<SplitMode>(() => (props.mode !== undefined ? props.mode : internalMode.value))

watch(
  () => props.defaultMode,
  (m) => {
    if (props.mode === undefined) internalMode.value = m
  },
)

const modeOptions = [
  { label: 'Split', value: 'split' },
  { label: props.leftLabel, value: 'left' },
  { label: props.rightLabel, value: 'right' },
]

const activeLabel = computed(() => {
  if (mode.value === 'split') return `${props.leftLabel} · ${props.rightLabel}`
  return mode.value === 'left' ? props.leftLabel : props.rightLabel
})

function onModeChange(value: string | number | boolean): void {
  const next = value as SplitMode
  internalMode.value = next
  emit('update:mode', next)
}
</script>
