<template>
  <div style="width: 100%; height: 500px">
    <AgGridVue
      :row-data="internalRowData"
      :column-defs="columnDefs"
      :default-col-def="defaultColDef"
      :pagination="true"
      :pagination-auto-page-size="true"
      :theme="gridTheme"
      :grid-options="gridOptions"
      :components="components"
      style="width: 100%; height: 100%"
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

// Theme (v34 :theme API)
const gridTheme = themeMaterial.withParams({
  spacing: 12,
  borderRadius: 8,
  rowHeight: 56,
  headerHeight: 48,
  listItemHeight: 40,
  accentColor: '#3b82f6',
  rowHoverColor: '#f3f4f6',
  headerBackgroundColor: '#f9fafb',
  headerTextColor: '#111827',
  headerCellHoverBackgroundColor: '#e0e7ff',
})

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
              'flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center',
          },
          [h('span', { class: 'text-blue-800 font-medium' }, initials)],
        ),
        h('div', { class: 'ml-3' }, [
          h('div', { class: 'text-sm font-medium text-gray-900' }, name || 'N/A'),
          h('div', { class: 'text-sm text-gray-500' }, email),
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
      const cls = active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
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
        h('span', String(props.params.value ?? '')),
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
              'px-3 py-1.5 text-xs font-medium rounded text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition',
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
</style>
