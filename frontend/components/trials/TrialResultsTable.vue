<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- Wide-schema note: every leaf field gets a column, none are hidden -->
    <div
      v-if="columns.length > COLUMN_NOTE_THRESHOLD"
      class="px-4 py-1.5 border-b border-default bg-surface text-[11px] text-content-subtle shrink-0"
    >
      {{ $t('trials.results.table_columns_note', { count: columns.length }) }}
    </div>

    <div ref="scrollContainer" class="flex-1 min-h-0 overflow-auto" @scroll="updateScrollState">
      <table :class="t.table">
        <thead>
          <tr>
            <!-- Sticky document column header (sticky in both axes) -->
            <th
              scope="col"
              :aria-sort="ariaSortFor(DOC_COLUMN)"
              :class="[t.th, thSticky, 'left-0 z-30', canScrollLeft ? stickyShadow : '']"
            >
              <button
                type="button"
                class="flex items-center gap-1 cursor-pointer select-none"
                @click="toggleSort(DOC_COLUMN)"
              >
                {{ $t('trials.results.table_document_header') }}
                <ChevronDown
                  v-if="sortPath === DOC_COLUMN"
                  :class="[
                    'w-3.5 h-3.5 transition-transform',
                    sortDir === 'asc' ? 'rotate-180' : '',
                  ]"
                  aria-hidden="true"
                />
              </button>
            </th>
            <th
              v-for="col in columns"
              :key="col.path"
              scope="col"
              :aria-sort="ariaSortFor(col.path)"
              :class="[t.th, thSticky, 'z-20']"
              :title="col.path"
            >
              <button
                type="button"
                class="flex items-center gap-1 cursor-pointer select-none whitespace-nowrap"
                @click="toggleSort(col.path)"
              >
                {{ col.name }}
                <ChevronDown
                  v-if="sortPath === col.path"
                  :class="[
                    'w-3.5 h-3.5 transition-transform',
                    sortDir === 'asc' ? 'rotate-180' : '',
                  ]"
                  aria-hidden="true"
                />
              </button>
            </th>
          </tr>
        </thead>
        <tbody :class="t.tbody">
          <tr v-for="row in rows" :key="row.result.id" :class="[t.tr, 'group']">
            <!-- Sticky document name cell → jump to document view -->
            <td
              :class="[
                t.td,
                'sticky left-0 z-10 bg-surface group-hover:bg-surface-muted whitespace-nowrap',
                canScrollLeft ? stickyShadow : '',
              ]"
            >
              <button
                type="button"
                class="flex items-center gap-2 min-w-0 max-w-[16rem] text-left"
                :title="$t('trials.results.table_open_document')"
                @click="$emit('open-document', row.result)"
              >
                <span
                  :class="[
                    'h-1.5 w-1.5 rounded-full shrink-0',
                    statusDotClass(String(row.result.status)),
                  ]"
                />
                <span class="truncate font-medium text-primary hover:underline">
                  {{ docName(row.result) }}
                </span>
              </button>
            </td>
            <!-- Value cells -->
            <template v-if="row.cells">
              <td
                v-for="(cell, ci) in row.cells"
                :key="columns[ci].path"
                :class="[t.td, 'whitespace-nowrap']"
              >
                <span
                  :class="['block max-w-[16rem] truncate', cell.empty ? 'text-content-subtle' : '']"
                  :title="cell.title || undefined"
                >
                  {{ cell.text }}
                </span>
              </td>
            </template>
            <!-- Failed document: error indicator instead of values -->
            <td v-else :colspan="columns.length" :class="[t.td, 'whitespace-nowrap']">
              <span class="inline-flex items-center gap-1.5 text-red-600 dark:text-red-400">
                <AlertTriangle class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {{
                  $t('trials.results.table_error_row', {
                    status: statusLabel(String(row.result.status ?? '')),
                  })
                }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Filter yielded nothing — keep the reset affordance visible -->
      <div
        v-if="results.length === 0"
        class="flex flex-col items-center justify-center py-12 text-center"
      >
        <p class="text-sm text-content-subtle">{{ $t('trials.results.no_match') }}</p>
        <button
          type="button"
          class="mt-2 text-xs font-medium text-primary hover:underline"
          @click="$emit('reset-filters')"
        >
          {{ $t('trials.results.reset_filters') }}
        </button>
      </div>
    </div>

    <!-- Compact pagination — same pages as the document view -->
    <div
      v-if="totalPages > 1"
      class="p-2 border-t border-default flex items-center justify-center gap-1 shrink-0"
    >
      <BaseButton
        variant="ghost"
        size="sm"
        :disabled="currentPage <= 1"
        :aria-label="$t('common.pagination.previous')"
        :title="$t('common.pagination.previous')"
        @click="$emit('page-change', currentPage - 1)"
      >
        <ChevronLeft class="h-4 w-4" />
      </BaseButton>
      <span class="text-xs text-content-muted tabular-nums">
        {{ currentPage }} / {{ totalPages }}
      </span>
      <BaseButton
        variant="ghost"
        size="sm"
        :disabled="currentPage >= totalPages"
        :aria-label="$t('common.pagination.next')"
        :title="$t('common.pagination.next')"
        @click="$emit('page-change', currentPage + 1)"
      >
        <ChevronRight class="h-4 w-4" />
      </BaseButton>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Cross-document table view of extraction results: rows = documents, columns =
 * schema leaf fields. Answers "did the model get this field right across all
 * documents?" without clicking through them one by one.
 *
 * Columns come from the SCHEMA (snapshot), not the results, so they stay
 * stable even when some documents lack values. Sorting is client-side and
 * page-scoped — it reorders the currently loaded page only.
 *
 * Not built on common/DataTable: this table needs a sticky LEFT column +
 * sticky header over an arbitrarily wide dynamic column set, which DataTable
 * only supports for its right-pinned actions column. The visual language
 * (useTableClasses) is shared.
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, ChevronDown, ChevronLeft, ChevronRight } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { useTableClasses } from '@/composables/useTableClasses'
import { flattenSchemaFields, type SchemaField } from '@/utils/schemaFieldList'
import type { SchemaDefinition, TrialResultItem } from '@/types'

interface Props {
  results: TrialResultItem[]
  schemaDefinition: SchemaDefinition | string | null
  currentPage: number
  totalPages: number
  /** Localized label for a result status (shared with the parent's rail). */
  statusLabel: (status: string) => string
}

const props = defineProps<Props>()

defineEmits<{
  (e: 'open-document', result: TrialResultItem): void
  (e: 'page-change', page: number): void
  (e: 'reset-filters'): void
}>()

const { t: translate } = useI18n({ useScope: 'global' })
const t = useTableClasses({ density: 'compact' })

const DOC_COLUMN = '__document__'
const COLUMN_NOTE_THRESHOLD = 30

// Sticky header cells need their own background to paint over scrolling rows.
const thSticky = 'sticky top-0 bg-surface-muted'
const stickyShadow =
  'shadow-[6px_0_10px_-6px_rgba(0,0,0,0.10)] dark:shadow-[6px_0_10px_-6px_rgba(0,0,0,0.45)]'

// --- Columns: one per schema leaf field ---
// Objects expand into their children; arrays stay a single summarized column
// (their item internals are excluded — the cell shows "N items" + tooltip).
const columns = computed<SchemaField[]>(() =>
  flattenSchemaFields(props.schemaDefinition).filter(
    (f) => f.type !== 'object' && !f.path.includes('[]'),
  ),
)

// --- Cell values ---

interface CellValue {
  text: string
  title: string
  empty: boolean
}

function valueAtPath(obj: Record<string, unknown> | null, path: string): unknown {
  if (!obj) return undefined
  let cur: unknown = obj
  for (const seg of path.split('.')) {
    if (cur === null || typeof cur !== 'object' || Array.isArray(cur)) return undefined
    cur = (cur as Record<string, unknown>)[seg]
  }
  return cur
}

function compactJson(value: unknown): string {
  try {
    const s = JSON.stringify(value)
    return s.length > 400 ? s.slice(0, 400) + '…' : s
  } catch {
    return ''
  }
}

function isEmptyCell(value: unknown): boolean {
  return (
    value === null ||
    value === undefined ||
    (typeof value === 'string' && !value.trim()) ||
    (Array.isArray(value) && value.length === 0)
  )
}

function formatCell(value: unknown): CellValue {
  if (isEmptyCell(value)) return { text: '—', title: '', empty: true }
  if (Array.isArray(value)) {
    return {
      text: translate('trials.results.table_items_count', { count: value.length }, value.length),
      title: compactJson(value),
      empty: false,
    }
  }
  if (typeof value === 'object') {
    const n = Object.keys(value as Record<string, unknown>).length
    return {
      text: translate('trials.results.table_fields_count', { count: n }, n),
      title: compactJson(value),
      empty: false,
    }
  }
  const s = String(value)
  return { text: s, title: s.length > 40 ? s : '', empty: false }
}

function hasResult(r: TrialResultItem): boolean {
  return !!r.result && typeof r.result === 'object'
}

function docName(r: TrialResultItem): string {
  return (
    r.document_name ||
    r.original_file_name ||
    translate('trials.results.doc_fallback', { id: r.document_id })
  )
}

const statusDotClass = (status: string): string => {
  if (status === 'success') return 'bg-green-500'
  if (status === 'incomplete') return 'bg-yellow-500'
  if (status === 'refused') return 'bg-orange-500'
  return 'bg-red-500'
}

// --- Sorting (page-scoped, client-side) ---

const sortPath = ref('')
const sortDir = ref<'asc' | 'desc'>('asc')

function toggleSort(path: string): void {
  if (sortPath.value === path) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortPath.value = path
    sortDir.value = 'asc'
  }
}

function ariaSortFor(path: string): 'ascending' | 'descending' | 'none' {
  if (sortPath.value !== path) return 'none'
  return sortDir.value === 'asc' ? 'ascending' : 'descending'
}

function sortKey(r: TrialResultItem): unknown {
  if (sortPath.value === DOC_COLUMN) return docName(r)
  return valueAtPath(r.result, sortPath.value)
}

function compareValues(a: unknown, b: unknown): number {
  if (typeof a === 'number' && typeof b === 'number') return a - b
  if (typeof a === 'boolean' && typeof b === 'boolean') return Number(a) - Number(b)
  if (Array.isArray(a) && Array.isArray(b)) return a.length - b.length
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' })
}

const sortedResults = computed<TrialResultItem[]>(() => {
  if (!sortPath.value) return props.results
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...props.results].sort((a, b) => {
    const va = sortKey(a)
    const vb = sortKey(b)
    const ea = isEmptyCell(va)
    const eb = isEmptyCell(vb)
    // Empty cells always sink to the bottom, whatever the direction.
    if (ea && eb) return 0
    if (ea) return 1
    if (eb) return -1
    return compareValues(va, vb) * dir
  })
})

// Precomputed cells per row; `cells === null` marks a failed document row.
const rows = computed(() =>
  sortedResults.value.map((result) => ({
    result,
    cells: hasResult(result)
      ? columns.value.map((col) => formatCell(valueAtPath(result.result, col.path)))
      : null,
  })),
)

// --- Sticky-column shadow (only while columns are hidden to the left) ---

const scrollContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)

function updateScrollState(): void {
  canScrollLeft.value = (scrollContainer.value?.scrollLeft ?? 0) > 0
}

let resizeObserver: ResizeObserver | null = null
onMounted(() => {
  updateScrollState()
  const el = scrollContainer.value
  if (el && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => updateScrollState())
    resizeObserver.observe(el)
  }
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})
watch(
  () => props.results,
  () => nextTick(updateScrollState),
)
</script>
