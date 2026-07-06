<!-- src/components/Tooltip.vue -->
<script setup lang="ts">
import { computed, ref, watchEffect, useId } from 'vue'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/vue'

interface Props {
  text: string
  // Optional bold headline rendered above the body.
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
})

// refs for the trigger and tooltip
const reference = ref<HTMLElement | null>(null)
const floating = ref<HTMLElement | null>(null)
const show = ref(false)
const tooltipId = useId()

// Split the body into lines so `\n` in `text` renders as paragraph breaks
// instead of one long wrapped string.
const lines = computed(() => (props.text ? props.text.split('\n') : []))

// Use @floating-ui/vue for positioning.
// `flip({ padding: NAVBAR_RESERVE })` treats the top strip occupied by the
// fixed Project Nav Bar as unavailable, so the tooltip flips *below* the
// trigger instead of rendering hidden behind the navbar. `fallbackPlacements`
// ensures it has somewhere to go. `shift()` keeps it inside the viewport
// horizontally. Placement defaults to top.
const NAVBAR_RESERVE = 72
const { x, y, strategy } = useFloating(reference, floating, {
  placement: 'top',
  middleware: [
    offset(8),
    flip({ padding: NAVBAR_RESERVE, fallbackPlacements: ['bottom', 'right', 'left'] }),
    shift({ padding: 8 }),
  ],
  whileElementsMounted: autoUpdate,
})

// Optionally hide tooltip if text is empty
watchEffect(() => {
  if (!props.text) show.value = false
})
</script>

<template>
  <span
    ref="reference"
    class="relative inline-block focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 rounded"
    tabindex="0"
    :aria-describedby="show && text ? tooltipId : undefined"
    @mouseenter="show = !!text"
    @mouseleave="show = false"
    @focus="show = !!text"
    @blur="show = false"
  >
    <slot />
    <div
      v-if="show && text"
      :id="tooltipId"
      ref="floating"
      :style="{ position: strategy, top: `${y ?? 0}px`, left: `${x ?? 0}px`, zIndex: 100 }"
      class="pointer-events-none px-3 py-2 rounded-card bg-slate-800 text-white text-xs shadow-xl transition-opacity duration-150 opacity-95 w-max max-w-[360px] max-h-[60vh] overflow-y-auto break-words leading-snug space-y-1"
      role="tooltip"
    >
      <p v-if="title" class="font-semibold text-white">{{ title }}</p>
      <p v-for="(line, i) in lines" :key="i" class="text-slate-200">{{ line }}</p>
    </div>
  </span>
</template>
