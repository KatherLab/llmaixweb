<template>
  <div
    class="bg-surface rounded-card border border-default shadow-sm overflow-hidden"
    role="status"
    aria-live="polite"
  >
    <table class="min-w-full divide-y divide-default-border">
      <thead class="bg-surface-muted">
        <tr>
          <th
            v-for="i in columns"
            :key="i"
            scope="col"
            class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
          >
            <div class="h-3 w-20 rounded bg-surface-sunken animate-pulse"></div>
          </th>
        </tr>
      </thead>
      <tbody class="bg-surface divide-y divide-default-border">
        <SkeletonRow v-for="r in rows" :key="r" :cells="columns" />
      </tbody>
    </table>
    <span class="sr-only">Loading</span>
  </div>
</template>

<script setup lang="ts">
import SkeletonRow from './SkeletonRow.vue'

interface Props {
  /** Number of columns (also the cell count for each skeleton row). */
  columns?: number
  /** Number of skeleton rows to render. */
  rows?: number
}

withDefaults(defineProps<Props>(), {
  columns: 5,
  rows: 5,
})
</script>
