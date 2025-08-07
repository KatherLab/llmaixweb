<!-- src/components/Tooltip.vue -->
<script setup>
import { ref, watchEffect } from 'vue'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/vue'

const props = defineProps({
  text: { type: String, required: true }
})

// refs for the trigger and tooltip
const reference = ref(null)
const floating = ref(null)
const show = ref(false)

// Use @floating-ui/vue for positioning
const { x, y, strategy, placement } = useFloating(reference, floating, {
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
  <span class="relative inline-block"
    ref="reference"
    @mouseenter="show = !!text"
    @mouseleave="show = false"
    @focus="show = !!text"
    @blur="show = false"
    tabindex="0"
    style="outline: none"
  >
    <slot />
    <div
      v-if="show && text"
      ref="floating"
      :style="{ position: strategy, top: `${y ?? 0}px`, left: `${x ?? 0}px`, zIndex: 50 }"
      class="pointer-events-none px-3 py-1 rounded bg-gray-800 text-white text-xs shadow transition-opacity duration-150 opacity-95"
      role="tooltip"
    >
      {{ text }}
    </div>
  </span>
</template>
