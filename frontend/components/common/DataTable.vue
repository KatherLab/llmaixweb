<template>
  <div :class="[t.wrapper, 'h-full flex flex-col']">
    <!-- Cross-page "select all" banner -->
    <div
      v-if="showSelectAllBanner"
      class="bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 px-4 py-2"
    >
      <div class="flex items-center justify-between">
        <p class="text-sm text-blue-800 dark:text-blue-300">
          <span class="font-medium">{{ totalSelected }}</span>
          {{ itemLabelSingular }}
          {{ totalSelected !== 1 ? 's' : '' }} selected
          <span v-if="totalSelected < pagination.total" class="text-blue-600 dark:text-blue-400">
            out of {{ pagination.total }} total
          </span>
        </p>
        <BaseButton
          v-if="totalSelected < pagination.total"
          variant="ghost"
          size="sm"
          class="font-medium underline"
          @click="$emit('select-all')"
        >
          Select all {{ pagination.total }} {{ itemLabel }}
        </BaseButton>
        <BaseButton v-else variant="ghost" size="sm" @click="$emit('clear-selection')">
          Clear selection
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
                class="h-4 w-4 text-blue-600 border-slate-300 dark:border-slate-600 rounded focus:ring-blue-500"
                @change="$emit('toggle-all')"
              />
            </th>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              :class="[
                t.th,
                column.sortable
                  ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors select-none'
                  : '',
                column.align === 'right' ? 'text-right' : 'text-left',
              ]"
              @click="column.sortable ? $emit('sort', column.key) : null"
            >
              <div
                :class="[
                  'flex items-center gap-1',
                  column.align === 'right' ? 'flex-row-reverse' : '',
                ]"
              >
                {{ column.label }}
                <ChevronDown
                  v-if="column.sortable && sortBy === column.key"
                  :class="['w-4 h-4 transition-transform', sortOrder === 'asc' ? 'rotate-180' : '']"
                />
              </div>
            </th>
            <th v-if="hasRowActions" scope="col" :class="[t.th, 'text-right']">Actions</th>
            <th v-if="expandable" scope="col" :class="[t.th, 'w-10']"></th>
          </tr>
        </thead>
        <tbody :class="t.tbody">
          <template v-for="row in items" :key="getRowKey(row)">
            <tr
              :id="rowIdPrefix ? `${rowIdPrefix}${getRowKeyValue(row)}` : undefined"
              :class="[
                t.tr,
                isRowSelected(row) ? 'bg-blue-50 dark:bg-slate-800' : '',
                isRowHighlighted(row)
                  ? 'ring-2 ring-emerald-500 ring-inset bg-emerald-50 dark:bg-emerald-900/20'
                  : '',
                rowClickable ? 'cursor-pointer' : '',
              ]"
              @click="rowClickable ? $emit('row-click', row) : null"
            >
              <td v-if="selectable" :class="t.td" class="whitespace-nowrap">
                <input
                  type="checkbox"
                  :checked="isRowSelected(row)"
                  class="h-4 w-4 text-blue-600 border-slate-300 dark:border-slate-600 rounded focus:ring-blue-500"
                  @click.stop="$emit('toggle-selection', getRowKeyValue(row))"
                />
              </td>
              <td
                v-for="column in columns"
                :key="column.key"
                :class="t.td"
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
                  class="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  :aria-label="isRowExpanded(row) ? 'Collapse' : 'Expand'"
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
                <div
                  class="bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700"
                >
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
      :title="emptyTitle"
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

<script setup>
import { computed, useSlots } from 'vue'
import { ChevronDown } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import { useTableClasses } from '@/composables/useTableClasses'
import { computeVisiblePages } from '@/composables/usePagination'

const props = defineProps({
  // [{ key, label, sortable?: boolean, align?: 'left'|'right', width?: string }]
  columns: { type: Array, required: true },
  items: { type: Array, required: true },
  rowKey: { type: String, default: 'id' },

  // selection
  selectable: { type: Boolean, default: false },
  selectedKeys: { type: Array, default: () => [] },
  allSelected: { type: Boolean, default: false },

  // sorting
  sortBy: { type: String, default: '' },
  sortOrder: { type: String, default: 'desc' },

  // pagination — pass null/omit to hide
  pagination: { type: Object, default: null },
  showPageSizeSelector: { type: Boolean, default: true },
  pageSizeOptions: { type: Array, default: () => [25, 50, 100, 250] },
  itemLabel: { type: String, default: 'items' },

  // cross-page select-all banner
  totalSelected: { type: Number, default: 0 },

  // per-row highlight (e.g. emerald ring for "just notified" rows)
  highlightedKeys: { type: Array, default: () => [] },

  // optional id prefix for each <tr> (enables scroll-to-row via getElementById)
  rowIdPrefix: { type: String, default: '' },

  // make whole rows clickable (emits `row-click` with the row object)
  rowClickable: { type: Boolean, default: false },

  // expandable rows
  expandable: { type: Boolean, default: false },
  expandedKeys: { type: Array, default: () => [] },

  // presentation
  density: { type: String, default: 'default' },
  emptyTitle: { type: String, default: 'No items found' },
  emptyDescription: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

defineEmits([
  'sort',
  'toggle-selection',
  'toggle-all',
  'select-all',
  'clear-selection',
  'page-change',
  'page-size-change',
  'expand',
  'row-click',
])

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

function getRowKeyValue(row) {
  return row?.[props.rowKey]
}

function getRowKey(row) {
  const v = getRowKeyValue(row)
  return v !== undefined ? v : JSON.stringify(row)
}

function isRowSelected(row) {
  return props.selectedKeys.includes(getRowKeyValue(row))
}

function isRowHighlighted(row) {
  return props.highlightedKeys.includes(getRowKeyValue(row))
}

function isRowExpanded(row) {
  return props.expandedKeys.includes(getRowKeyValue(row))
}
</script>
