<template>
  <tr>
    <td v-for="i in cells" :key="i" class="px-4 py-3">
      <div
        class="h-4 rounded bg-surface-sunken animate-pulse"
        :style="{ width: barWidth(i) }"
      ></div>
    </td>
  </tr>
</template>

<script setup lang="ts">
interface Props {
  /** Number of shimmering cells in the row. */
  cells?: number
}

withDefaults(defineProps<Props>(), {
  cells: 5,
})

// Vary the bar width per cell so the skeleton reads as content, not a grid.
const widths = ['85%', '60%', '45%', '70%', '50%', '40%', '65%', '55%']
const barWidth = (i: number): string => widths[(i - 1) % widths.length]
</script>
