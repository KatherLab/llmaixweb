<template>
  <div class="overflow-x-auto">
    <table class="border-collapse text-xs">
      <thead>
        <tr>
          <th class="p-2 text-left text-slate-500 dark:text-slate-400">
            <span class="block">Ground truth ↓</span>
            <span class="block">Predicted →</span>
          </th>
          <th
            v-for="col in labels"
            :key="`col-${col}`"
            class="p-2 font-medium text-slate-600 dark:text-slate-300 whitespace-nowrap max-w-[140px] truncate"
            :title="col"
          >
            {{ col }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in labels" :key="`row-${row}`">
          <th
            class="p-2 font-medium text-slate-600 dark:text-slate-300 whitespace-nowrap max-w-[140px] truncate text-left"
            :title="row"
          >
            {{ row }}
          </th>
          <td
            v-for="col in labels"
            :key="`cell-${row}-${col}`"
            :class="[
              'p-2 text-center border border-slate-200 dark:border-slate-700 cursor-pointer transition-colors',
              cellClass(row, col),
            ]"
            :title="`${row} → ${col}: ${count(row, col)} document(s). Click to filter.`"
            @click="$emit('filter', { groundTruth: row, predicted: col })"
          >
            {{ count(row, col) || '' }}
          </td>
        </tr>
      </tbody>
    </table>
    <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">
      Click a cell to show documents where the model predicted that value. The diagonal (correct
      predictions) is highlighted green.
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /**
   * Confusion matrix for a single categorical field:
   * { gt_value: { pred_value: count } }
   */
  matrix: {
    type: Object,
    default: () => ({}),
  },
})

defineEmits(['filter'])

// Sorted union of all ground-truth and predicted values as row/column labels.
const labels = computed(() => {
  const set = new Set()
  for (const gt of Object.keys(props.matrix || {})) {
    set.add(gt)
    for (const pred of Object.keys(props.matrix[gt] || {})) {
      set.add(pred)
    }
  }
  return [...set].sort((a, b) => a.localeCompare(b))
})

const count = (gt, pred) => {
  const row = props.matrix?.[gt]
  if (!row) return 0
  return row[pred] || 0
}

const cellClass = (gt, pred) => {
  const c = count(gt, pred)
  if (c === 0) return 'text-slate-300 dark:text-slate-700'
  if (gt === pred) {
    return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 font-semibold hover:bg-green-200 dark:hover:bg-green-900/50'
  }
  return 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/40'
}
</script>
