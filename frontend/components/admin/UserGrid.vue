<template>
  <div class="h-full w-full">
    <AgGridVue
      :row-data="internalRowData"
      :column-defs="columnDefs"
      :default-col-def="defaultColDef"
      :pagination="true"
      :pagination-auto-page-size="true"
      :theme="gridTheme"
      :grid-options="gridOptions"
      :components="components"
      class="h-full w-full"
      @grid-ready="onGridReady"
      @first-data-rendered="onFirstDataRendered"
      @grid-size-changed="onGridSizeChanged"
    />
  </div>
</template>

<script setup>
import { ref, watch, defineComponent, h } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { themeMaterial } from 'ag-grid-community'

// Emits to parent
const emit = defineEmits(['edit-requested'])

// Theme (v34 :theme API) - with dark mode support
const isDarkMode = () => {
  if (typeof window !== 'undefined') {
    return (
      localStorage.getItem('darkMode') === '1' ||
      (!localStorage.getItem('darkMode') &&
        window.matchMedia('(prefers-color-scheme: dark)').matches)
    )
  }
  return false
}

const getGridTheme = () => {
  const darkMode = isDarkMode()
  return themeMaterial.withParams({
    spacing: 12,
    borderRadius: 8,
    rowHeight: 56,
    headerHeight: 48,
    listItemHeight: 40,
    accentColor: '#3b82f6',
    rowHoverColor: darkMode ? '#1e293b' : '#f3f4f6',
    headerBackgroundColor: darkMode ? '#1e293b' : '#f9fafb',
    headerTextColor: darkMode ? '#e2e8f0' : '#111827',
    headerCellHoverBackgroundColor: darkMode ? '#334155' : '#e0e7ff',
    // Dark mode colors
    backgroundColor: darkMode ? '#0f172a' : '#ffffff',
    foregroundColor: darkMode ? '#f1f5f9' : '#111827',
    rowBackgroundColor: darkMode ? '#0f172a' : '#ffffff',
    rowForegroundColor: darkMode ? '#e2e8f0' : '#111827',
    borderColor: darkMode ? '#334155' : '#e5e7eb',
    controlBorderRadius: 8,
  })
}

const gridTheme = ref(getGridTheme())

// Watch for dark mode changes
if (typeof window !== 'undefined') {
  const observer = new MutationObserver(() => {
    gridTheme.value = getGridTheme()
  })
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })
}

// ----------------------------
// Vue cell components (render)
// ----------------------------
const UserCell = defineComponent({
  name: 'UserCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const onEdit = () => props.params.context?.emitEdit?.(props.params.data)
    return () => {
      const name = String(props.params.value ?? '')
      const initials = name
        ? name
            .split(' ')
            .map((n) => n[0])
            .join('')
            .toUpperCase()
        : '?'
      const email = props.params.data?.email ?? ''
      return h('div', { class: 'flex items-center h-full cursor-pointer', onClick: onEdit }, [
        h(
          'div',
          {
            class:
              'flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 dark:bg-slate-700 flex items-center justify-center',
          },
          [h('span', { class: 'text-blue-800 dark:text-blue-300 font-medium' }, initials)],
        ),
        h('div', { class: 'ml-3' }, [
          h('div', { class: 'text-sm font-medium text-gray-900 dark:text-white' }, name || 'N/A'),
          h('div', { class: 'text-sm text-gray-500 dark:text-slate-400' }, email),
        ]),
      ])
    }
  },
})

const StatusCell = defineComponent({
  name: 'StatusCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const onEdit = () => props.params.context?.emitEdit?.(props.params.data)
    return () => {
      const active = !!props.params.value
      const cls = active
        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
        : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
      const text = active ? 'Active' : 'Inactive'
      return h('div', { class: 'flex items-center h-full cursor-pointer', onClick: onEdit }, [
        h(
          'span',
          { class: `px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full ${cls}` },
          text,
        ),
      ])
    }
  },
})

const RoleCell = defineComponent({
  name: 'RoleCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const onEdit = () => props.params.context?.emitEdit?.(props.params.data)
    return () =>
      h('div', { class: 'flex items-center h-full cursor-pointer capitalize', onClick: onEdit }, [
        h('span', { class: 'text-gray-900 dark:text-white' }, String(props.params.value ?? '')),
      ])
  },
})

const ActionsCell = defineComponent({
  name: 'ActionsCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const onEdit = () => props.params.context?.emitEdit?.(props.params.data)
    return () => {
      return h('div', { class: 'flex items-center h-full justify-center' }, [
        h(
          'button',
          {
            class:
              'px-3 py-1.5 text-xs font-medium rounded text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-slate-700 border border-blue-200 dark:border-slate-600 hover:bg-blue-100 dark:hover:bg-slate-600 transition',
            onClick: (e) => {
              e.stopPropagation()
              onEdit()
            },
          },
          'Edit',
        ),
      ])
    }
  },
})

const components = { UserCell, StatusCell, RoleCell, ActionsCell } // used by colDefs via string names. :contentReference[oaicite:5]{index=5}

// ----------------------------
// Column definitions
// ----------------------------
const columnDefs = ref([
  { field: 'full_name', headerName: 'User', flex: 2, minWidth: 220, cellRenderer: 'UserCell' },
  { field: 'is_active', headerName: 'Status', width: 120, cellRenderer: 'StatusCell' },
  { field: 'role', headerName: 'Role', width: 120, cellRenderer: 'RoleCell' },
  { field: 'actions', headerName: 'Actions', width: 120, cellRenderer: 'ActionsCell' },
])

// ----------------------------
// Defaults & options
// ----------------------------
const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle',
}

const internalRowData = ref([])
const gridApi = ref(null)

const gridOptions = {
  // so button clicks can emit to the parent Component
  context: {
    emitEdit: (row) => emit('edit-requested', row),
  },
  getRowId: (p) => String(p.data.id), // stabilize row updates across refreshes
}

// Sizing helpers & lifecycle (called when data is rendered/resized)
const sizeToFitIfVisible = () => {
  const el = gridApi.value?.getGui?.()
  const visible = el && el.offsetParent !== null && el.clientWidth > 0
  if (visible && gridApi.value && !gridApi.value.isDestroyed()) {
    gridApi.value.sizeColumnsToFit()
  }
}

function onGridReady(params) {
  gridApi.value = params.api
  params.api.addEventListener('gridPreDestroy', () => {
    gridApi.value = null
  }) // teardown hook. :contentReference[oaicite:7]{index=7}
}

function onFirstDataRendered() {
  sizeToFitIfVisible()
}
function onGridSizeChanged() {
  sizeToFitIfVisible()
}

// ----------------------------
// Data — use parent rowData prop reactively
// ----------------------------
const props = defineProps({
  rowData: { type: Array, default: () => [] },
  search: { type: String, default: '' },
  theme: { type: Object, default: null },
})

watch(
  () => props.rowData,
  (newData) => {
    internalRowData.value = newData
    // Force refresh all cells so Vue cell renderers re-render with updated data
    if (gridApi.value && !gridApi.value.isDestroyed()) {
      gridApi.value.refreshCells({ force: true })
    }
  },
  { immediate: true },
)
</script>

<style>
:deep(.ag-center-cols-container) {
  display: flex;
  align-items: center;
}

/* Header text and icon styling for both light and dark mode */
:deep(.ag-header-cell-text) {
  color: #111827 !important;
}
:deep(.ag-cell-label-container) {
  color: #111827 !important;
}
:deep(.ag-filter-icon) {
  color: #6b7280 !important;
}
:deep(.ag-sort-icon) {
  color: #6b7280 !important;
}
:deep(.ag-header-cell-label-container) {
  color: #111827 !important;
}

/* Dark mode overrides for AG-Grid */
html.dark :deep(.ag-header-cell-text) {
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-header-cell) {
  background-color: #1e293b !important;
  border-color: #334155 !important;
}
html.dark :deep(.ag-cell-label-container) {
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-filter-icon) {
  color: #94a3b8 !important;
}
html.dark :deep(.ag-sort-icon) {
  color: #94a3b8 !important;
}
html.dark :deep(.ag-column-select-header) {
  background-color: #1e293b !important;
}
html.dark :deep(.ag-body-container) {
  background-color: #0f172a !important;
}
html.dark :deep(.ag-header) {
  background-color: #1e293b !important;
  border-color: #334155 !important;
}
html.dark :deep(.ag-row) {
  background-color: #0f172a !important;
  border-color: #334155 !important;
}
html.dark :deep(.ag-cell) {
  border-color: #334155 !important;
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-paging-panel) {
  background-color: #0f172a !important;
  border-color: #334155 !important;
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-paging-button) {
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-paging-button:disabled) {
  color: #64748b !important;
}
html.dark :deep(.ag-input-field-input) {
  background-color: #1e293b !important;
  border-color: #334155 !important;
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-filter-body) {
  background-color: #1e293b !important;
  border-color: #334155 !important;
}
html.dark :deep(.ag-list-item) {
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-popup) {
  background-color: #1e293b !important;
  border-color: #334155 !important;
}
</style>
