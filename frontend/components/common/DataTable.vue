<template>
  <div :class="[t.wrapper, 'h-full flex flex-col']">
    <!-- Cross-page "select all" banner -->
    <div v-if="showSelectAllBanner" class="bg-primary-soft border-b border-primary/30 px-4 py-2">
      <div class="flex items-center justify-between">
        <p class="text-sm text-primary">
          <span class="font-medium">{{ totalSelected }}</span>
          {{ totalSelected === 1 ? itemLabelSingular : itemLabel }}
          {{ $t('common.data_table.selected') }}
          <span v-if="(totalSelected ?? 0) < (pagination?.total ?? 0)" class="text-primary">
            {{ $t('common.data_table.out_of_total', { total: pagination?.total }) }}
          </span>
        </p>
        <BaseButton
          v-if="(totalSelected ?? 0) < (pagination?.total ?? 0)"
          variant="ghost"
          size="sm"
          class="font-medium underline"
          :disabled="selectAllBusy"
          @click="$emit('select-all')"
        >
          {{
            selectAllBusy
              ? $t('common.data_table.selecting')
              : $t('common.data_table.select_all_count', {
                  count: pagination?.total,
                  label: itemLabel,
                })
          }}
        </BaseButton>
        <BaseButton v-else variant="ghost" size="sm" @click="$emit('clear-selection')">
          {{ $t('common.data_table.clear_selection') }}
        </BaseButton>
      </div>
    </div>

    <!-- Table -->
    <div :class="['overflow-auto min-h-0', items.length > 0 ? 'flex-1' : '']">
      <table :class="t.table">
        <thead :class="t.thead">
          <tr>
            <th v-if="selectable" scope="col" :class="[t.th, 'text-left']">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate="someSelected"
                :aria-label="$t('common.data_table.select_all_page', { label: itemLabel })"
                class="h-4 w-4 text-primary border-strong rounded focus:ring-ring"
                @change="$emit('toggle-all')"
              />
            </th>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              :aria-sort="ariaSortFor(column)"
              :class="[
                t.th,
                column.sortable ? 'hover:bg-surface-muted transition-colors select-none' : '',
                column.align === 'right' ? 'text-right' : 'text-left',
              ]"
            >
              <button
                v-if="column.sortable"
                type="button"
                :class="[
                  'flex items-center gap-1 w-full cursor-pointer',
                  column.align === 'right' ? 'flex-row-reverse' : '',
                ]"
                @click="$emit('sort', column.key)"
              >
                {{ column.label }}
                <ChevronDown
                  v-if="sortBy === column.key"
                  :class="['w-4 h-4 transition-transform', sortOrder === 'asc' ? 'rotate-180' : '']"
                  aria-hidden="true"
                />
              </button>
              <div
                v-else
                :class="[
                  'flex items-center gap-1',
                  column.align === 'right' ? 'flex-row-reverse' : '',
                ]"
              >
                {{ column.label }}
              </div>
            </th>
            <th v-if="hasRowActions" scope="col" :class="[t.th, 'text-right']">
              {{ $t('common.data_table.actions') }}
            </th>
            <th v-if="expandable" scope="col" :class="[t.th, 'w-10']"></th>
          </tr>
        </thead>
        <tbody :class="t.tbody">
          <template v-for="row in items" :key="getRowKey(row)">
            <tr
              :id="rowIdPrefix ? `${rowIdPrefix}${getRowKeyValue(row)}` : undefined"
              :class="[
                t.tr,
                isRowSelected(row) ? 'bg-primary-soft' : '',
                isRowHighlighted(row)
                  ? 'ring-2 ring-emerald-500 ring-inset bg-emerald-50 dark:bg-emerald-900/20'
                  : '',
                rowClickable ? 'cursor-pointer' : '',
              ]"
              :tabindex="rowClickable ? 0 : undefined"
              @click="rowClickable ? $emit('row-click', row) : null"
              @keydown.enter.self="rowClickable ? $emit('row-click', row) : null"
              @keydown.space.self.prevent="rowClickable ? $emit('row-click', row) : null"
            >
              <td v-if="selectable" :class="t.td" class="whitespace-nowrap">
                <input
                  type="checkbox"
                  :checked="isRowSelected(row)"
                  :aria-label="
                    $t('common.data_table.select_row', {
                      label: itemLabelSingular,
                      name: rowLabel(row),
                    })
                  "
                  class="h-4 w-4 text-primary border-strong rounded focus:ring-ring"
                  @click.stop="$emit('toggle-selection', getRowKeyValue(row))"
                />
              </td>
              <td
                v-for="column in columns"
                :key="column.key"
                :class="t.td"
                class="tabular-nums"
                :style="column.width ? { width: column.width } : null"
              >
                <slot :name="`cell-${column.key}`" :row="row">
                  {{ row[column.key] }}
                </slot>
              </td>
              <td v-if="hasRowActions" :class="t.td" class="whitespace-nowrap text-right">
                <div class="flex items-center justify-end gap-1">
                  <slot name="row-actions" :row="row" />
                </div>
              </td>
              <td v-if="expandable" :class="t.td" class="whitespace-nowrap text-right">
                <button
                  type="button"
                  class="p-1 rounded text-content-subtle hover:text-content hover:bg-surface-muted transition-colors"
                  :aria-label="
                    isRowExpanded(row)
                      ? $t('common.data_table.collapse')
                      : $t('common.data_table.expand')
                  "
                  @click.stop="$emit('expand', getRowKeyValue(row))"
                >
                  <ChevronDown
                    :class="[
                      'w-4 h-4 transition-transform',
                      isRowExpanded(row) ? 'rotate-180' : '',
                    ]"
                  />
                </button>
              </td>
            </tr>
            <tr v-if="expandable && isRowExpanded(row)">
              <td :colspan="totalColspan" class="p-0">
                <div class="bg-surface-muted border-t border-default">
                  <slot name="expanded" :row="row" />
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <EmptyState
      v-if="items.length === 0 && !loading"
      :title="emptyTitle ?? $t('common.data_table.empty_title')"
      :description="emptyDescription"
    >
      <template v-if="$slots['empty-icon']" #icon>
        <slot name="empty-icon" />
      </template>
    </EmptyState>

    <!-- Pagination -->
    <PaginationControls
      v-if="pagination"
      :model-value="pagination.page"
      :total-pages="pagination.total_pages"
      :visible-pages="visiblePages"
      :total-items="pagination.total"
      :page-size="pagination.page_size"
      :show-page-size-selector="showPageSizeSelector"
      :page-size-options="pageSizeOptions"
      :item-label="itemLabel"
      @update:model-value="$emit('page-change', $event)"
      @update:page-size="$emit('page-size-change', $event)"
    />
  </div>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
import { computed, useSlots } from 'vue'
import { ChevronDown } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import { useTableClasses } from '@/composables/useTableClasses'
import { computeVisiblePages } from '@/composables/usePagination'

export interface DataTableColumn {
  key: string
  label: string
  sortable?: boolean
  align?: 'left' | 'right'
  width?: string
}

export interface DataTablePagination {
  page: number
  total_pages: number
  total: number
  page_size: number
}

interface Props {
  // [{ key, label, sortable?: boolean, align?: 'left'|'right', width?: string }]
  columns: DataTableColumn[]
  items: T[]
  rowKey?: string

  // selection
  selectable?: boolean
  selectedKeys?: (string | number)[]
  allSelected?: boolean

  // sorting
  sortBy?: string
  sortOrder?: string

  // pagination — pass null/omit to hide
  pagination?: DataTablePagination | null
  showPageSizeSelector?: boolean
  pageSizeOptions?: number[]
  itemLabel?: string

  // cross-page select-all banner
  totalSelected?: number
  // busy state while the "select all across pages" id fetch runs
  selectAllBusy?: boolean

  // per-row highlight (e.g. emerald ring for "just notified" rows)
  highlightedKeys?: (string | number)[]

  // optional id prefix for each <tr> (enables scroll-to-row via getElementById)
  rowIdPrefix?: string

  // make whole rows clickable (emits `row-click` with the row object)
  rowClickable?: boolean

  // expandable rows
  expandable?: boolean
  expandedKeys?: (string | number)[]

  // presentation
  density?: 'default' | 'compact'
  emptyTitle?: string
  emptyDescription?: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  rowKey: 'id',
  selectable: false,
  selectedKeys: () => [],
  allSelected: false,
  sortBy: '',
  sortOrder: 'desc',
  pagination: null,
  showPageSizeSelector: true,
  pageSizeOptions: () => [25, 50, 100, 250],
  itemLabel: 'items',
  totalSelected: 0,
  selectAllBusy: false,
  highlightedKeys: () => [],
  rowIdPrefix: '',
  rowClickable: false,
  expandable: false,
  expandedKeys: () => [],
  density: 'default',
  emptyDescription: '',
  loading: false,
})

defineEmits<{
  (e: 'sort', key: string): void
  (e: 'toggle-selection', key: string | number): void
  (e: 'toggle-all'): void
  (e: 'select-all'): void
  (e: 'clear-selection'): void
  (e: 'page-change', page: number): void
  (e: 'page-size-change', size: number): void
  (e: 'expand', key: string | number): void
  (e: 'row-click', row: T): void
}>()

const slots = useSlots()
const t = useTableClasses({ density: props.density })

const hasRowActions = computed(() => !!slots['row-actions'])

const someSelected = computed(
  () => props.selectedKeys.length > 0 && props.selectedKeys.length < props.items.length,
)

const showSelectAllBanner = computed(
  () =>
    props.selectable &&
    props.totalSelected > 0 &&
    props.pagination &&
    props.pagination.total > props.pagination.page_size,
)

const visiblePages = computed(() =>
  props.pagination ? computeVisiblePages(props.pagination.page, props.pagination.total_pages) : [],
)

const totalColspan = computed(() => {
  let count = props.columns.length
  if (props.selectable) count += 1
  if (hasRowActions.value) count += 1
  if (props.expandable) count += 1
  return count
})

// Singular label for the select-all banner ("file" vs "files").
const itemLabelSingular = computed(() => {
  const label = props.itemLabel
  return label.endsWith('s') ? label.slice(0, -1) : label
})

// aria-sort value for a header cell: only the actively sorted column carries a
// direction; other sortable columns expose 'none'.
function ariaSortFor(column: DataTableColumn): 'ascending' | 'descending' | 'none' | undefined {
  if (!column.sortable) return undefined
  if (props.sortBy !== column.key) return 'none'
  return props.sortOrder === 'asc' ? 'ascending' : 'descending'
}

// Human-friendly label for a row's select checkbox (falls back to the key).
function rowLabel(row: T): string | number {
  const candidate = row.name ?? row.file_name ?? row.document_name ?? row.title
  return typeof candidate === 'string' && candidate ? candidate : getRowKeyValue(row)
}

function getRowKeyValue(row: T): string | number {
  return (row?.[props.rowKey] ?? undefined) as string | number
}

function getRowKey(row: T): string | number {
  const v = getRowKeyValue(row)
  return v !== undefined ? v : JSON.stringify(row)
}

function isRowSelected(row: T): boolean {
  return props.selectedKeys.includes(getRowKeyValue(row))
}

function isRowHighlighted(row: T): boolean {
  return props.highlightedKeys.includes(getRowKeyValue(row))
}

function isRowExpanded(row: T): boolean {
  return props.expandedKeys.includes(getRowKeyValue(row))
}
</script>
