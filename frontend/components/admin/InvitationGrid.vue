<template>
  <AgGridVue
    :row-data="rowData"
    :column-defs="columnDefs"
    :default-col-def="defaultColDef"
    pagination
    pagination-auto-page-size
    style="width: 100%; height: 320px"
    class="mx-auto"
    :quick-filter-text="search"
    :theme="gridTheme"
    @grid-ready="gridReady"
  />
</template>

<script setup>
import { AgGridVue } from 'ag-grid-vue3'
import { useGridTheme } from '@/composables/useGridTheme'

defineProps({
  rowData: { type: Array, default: () => [] },
  search: { type: String, default: '' },
})

const emit = defineEmits(['delete-requested'])

// Column definitions (self-contained — previously passed from parent)
const columnDefs = [
  { field: 'email', headerName: 'Email', sortable: true, filter: true, flex: 1, minWidth: 140 },
  {
    field: 'is_used',
    headerName: 'Used',
    sortable: true,
    filter: true,
    flex: 1,
    minWidth: 70,
    valueFormatter: ({ value }) => (value ? 'Yes' : 'No'),
    cellRenderer: ({ value }) =>
      value
        ? '<span class="bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full text-xs">Yes</span>'
        : '<span class="bg-green-50 text-green-700 px-2 py-0.5 rounded-full text-xs">No</span>',
  },
  {
    headerName: 'Actions',
    field: 'actions',
    minWidth: 110,
    maxWidth: 130,
    sortable: false,
    filter: false,
    pinned: 'right',
    cellRenderer: (params) => {
      return `<button class="text-xs text-red-600 font-bold ag-action-btn" data-action="delete">Delete</button>`
    },
  },
]
const defaultColDef = { resizable: true, sortable: true, filter: true }

// Shared ag-grid theme with dark-mode support (re-themes on toggle)
const { gridTheme } = useGridTheme({ rowHeight: 40, listItemHeight: 40, controlBorderRadius: 8 })

function gridReady(params) {
  params.api.addEventListener('cellClicked', (event) => {
    if (event.colDef.field !== 'actions') return
    const invitation = event.data
    if (event.event.target.dataset.action === 'delete') {
      emit('delete-requested', invitation)
    }
  })
}
</script>
