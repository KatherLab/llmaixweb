<!-- src/components/Tooltip.vue -->
<script setup>
import { ref, watchEffect, useId } from 'vue'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/vue'

const props = defineProps({
  text: { type: String, required: true },
})

// refs for the trigger and tooltip
const reference = ref(null)
const floating = ref(null)
const show = ref(false)
const tooltipId = useId()

// Use @floating-ui/vue for positioning
const { x, y, strategy } = useFloating(reference, floating, {
  placement: 'top',
  middleware: [offset(8), flip(), shift()],
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
    class="relative inline-block focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded"
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
      :style="{ position: strategy, top: `${y ?? 0}px`, left: `${x ?? 0}px`, zIndex: 50 }"
      class="pointer-events-none px-3 py-1 rounded bg-slate-800 text-white text-xs shadow transition-opacity duration-150 opacity-95"
      role="tooltip"
    >
      {{ text }}
    </div>
  </span>
</template>
