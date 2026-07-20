<template>
  <div class="overflow-x-auto">
    <div class="inline-block min-w-full">
      <table class="border-collapse text-xs">
        <thead>
          <tr>
            <th class="sticky left-0 z-20 bg-surface">
              <!-- Axis legend -->
              <div
                class="flex flex-col items-center justify-center gap-0.5 w-[120px] min-h-[64px] p-2"
              >
                <span class="text-[10px] uppercase tracking-wide text-content-subtle">{{
                  $t('evaluation.confusion.predicted_axis')
                }}</span>
                <span class="text-[10px] text-content-subtle">{{
                  $t('evaluation.confusion.ground_truth_axis')
                }}</span>
              </div>
            </th>
            <th
              v-for="col in labels"
              :key="`col-${col}`"
              class="p-2 font-medium text-content-muted align-bottom max-w-[140px] border-b border-default"
              :title="col"
            >
              <div class="whitespace-normal break-words text-center leading-tight">
                {{ col }}
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in labels" :key="`row-${row}`">
            <th
              class="sticky left-0 z-10 bg-surface p-2 font-medium text-content-muted whitespace-normal break-words max-w-[140px] text-left border-r border-default align-middle"
              :title="row"
            >
              {{ row }}
            </th>
            <td
              v-for="col in labels"
              :key="`cell-${row}-${col}`"
              class="p-1.5 text-center border border-default transition-all duration-150 select-none"
              :class="
                count(row, col) > 0
                  ? [
                      'cursor-pointer focus:outline-none focus:ring-2 focus:ring-inset focus:ring-ring',
                      cellClass(row, col),
                    ]
                  : ['cursor-default', cellClass(row, col)]
              "
              :style="cellStyle(row, col)"
              :role="count(row, col) > 0 ? 'button' : undefined"
              :tabindex="count(row, col) > 0 ? 0 : -1"
              :aria-label="cellTitle(row, col)"
              :title="cellTitle(row, col)"
              @click="onCellClick(row, col)"
              @keydown="onCellKeydown($event, row, col)"
            >
              <div class="flex flex-col items-center leading-none">
                <span class="text-sm font-semibold tabular-nums">{{ count(row, col) || '·' }}</span>
                <span
                  v-if="count(row, col) > 0"
                  class="text-[9px] tabular-nums opacity-70 mt-0.5"
                  >{{ rowPercent(row, col) }}</span
                >
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="mt-2 text-xs text-content-subtle">
      {{ $t('evaluation.confusion.caption_intro') }}
      <span class="font-medium text-content-muted">{{
        $t('evaluation.confusion.caption_click')
      }}</span>
      {{ $t('evaluation.confusion.caption_outro') }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

/**
 * Confusion matrix for a single categorical field:
 * { gt_value: { pred_value: count } }
 */
type ConfusionMatrix = Record<string, Record<string, number>>

/** Active cell filter shape: { groundTruth, predicted } | null */
interface ConfusionFilter {
  groundTruth: string
  predicted: string
  field?: string
}

interface Props {
  matrix?: ConfusionMatrix
  /** Currently active cell filter (mirrors the parent's confusionFilter). */
  activeFilter?: ConfusionFilter | null
}

const props = withDefaults(defineProps<Props>(), {
  matrix: () => ({}),
  activeFilter: undefined,
})

const emit = defineEmits<{
  filter: [filter: ConfusionFilter]
}>()

// Emit a filter event for a cell. Only non-empty cells are interactive
// (clickable + keyboard-focusable), so this is a no-op when count is 0.
const onCellClick = (gt: string, pred: string): void => {
  if (count(gt, pred) > 0) emit('filter', { groundTruth: gt, predicted: pred })
}

// Keyboard equivalent of clicking a cell: Enter / Space toggles the filter.
const onCellKeydown = (e: KeyboardEvent, gt: string, pred: string): void => {
  if (count(gt, pred) === 0) return
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    emit('filter', { groundTruth: gt, predicted: pred })
  }
}

// Sorted union of all ground-truth and predicted values as row/column labels.
const labels = computed<string[]>(() => {
  const set = new Set<string>()
  for (const gt of Object.keys(props.matrix || {})) {
    set.add(gt)
    for (const pred of Object.keys(props.matrix[gt] || {})) {
      set.add(pred)
    }
  }
  return [...set].sort((a, b) => a.localeCompare(b))
})

const count = (gt: string, pred: string): number => {
  const row = props.matrix?.[gt]
  if (!row) return 0
  return row[pred] || 0
}

// Total count of a ground-truth value across all predictions (row sum).
const rowTotal = (gt: string): number =>
  Object.values(props.matrix?.[gt] || {}).reduce((sum, c) => sum + (c || 0), 0)

// Highest non-diagonal count drives the error-heatmap scale; diagonal uses its
// own max so a dominant correct cell doesn't wash out the error cells.
const maxError = computed(() => {
  let m = 0
  for (const gt of labels.value) {
    for (const pred of labels.value) {
      if (gt !== pred) m = Math.max(m, count(gt, pred))
    }
  }
  return m || 1
})
const maxCorrect = computed(() => {
  let m = 0
  for (const gt of labels.value) m = Math.max(m, count(gt, gt))
  return m || 1
})

// Share of the ground-truth row — "of all GT=X docs, what fraction predicted Y".
const rowPercent = (gt: string, pred: string): string => {
  const rt = rowTotal(gt)
  if (!rt) return '0%'
  return `${Math.round((count(gt, pred) / rt) * 100)}%`
}

const isActive = (gt: string, pred: string): boolean =>
  !!props.activeFilter &&
  String(props.activeFilter.groundTruth) === String(gt) &&
  String(props.activeFilter.predicted) === String(pred)

const cellTitle = (gt: string, pred: string): string => {
  const c = count(gt, pred)
  const rt = rowTotal(gt)
  const pct = rt ? Math.round((c / rt) * 100) : 0
  const verdict =
    gt === pred
      ? t('evaluation.confusion.verdict_correct')
      : t('evaluation.confusion.verdict_mismatch')
  return t('evaluation.confusion.cell_title', { gt, pred, count: c, pct, verdict })
}

// Intensity-scaled background. Diagonal = green, off-diagonal with count>0 =
// red, empty cells stay neutral. Alpha grows with the cell's share of its
// scale max so patterns are visible at a glance.
const cellStyle = (gt: string, pred: string): Record<string, string> => {
  const c = count(gt, pred)
  if (c === 0) return {}
  if (gt === pred) {
    const alpha = 0.18 + 0.55 * (c / maxCorrect.value)
    return { backgroundColor: `rgba(34, 197, 94, ${alpha.toFixed(2)})` }
  }
  const alpha = 0.14 + 0.6 * (c / maxError.value)
  return { backgroundColor: `rgba(239, 68, 68, ${alpha.toFixed(2)})` }
}

const cellClass = (gt: string, pred: string): string => {
  const classes: string[] = []
  if (count(gt, pred) === 0) {
    classes.push('text-content-subtle')
  } else if (gt === pred) {
    classes.push('text-green-800 dark:text-green-300')
  } else {
    classes.push('text-red-700 dark:text-red-300')
  }
  // Hover lift (only on non-empty cells)
  if (count(gt, pred) > 0) {
    classes.push('hover:brightness-95 dark:hover:brightness-110')
  }
  // Active-filter highlight — strong blue ring + lift, drawn above neighbors.
  if (isActive(gt, pred)) {
    classes.push('ring-2 ring-inset ring-ring relative z-10 shadow-lg scale-[1.04]')
  }
  return classes.join(' ')
}
</script>
