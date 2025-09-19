<template>
  <div style="width: 100%; height: 500px">
    <AgGridVue
      :rowData="rowData"
      :columnDefs="columnDefs"
      :defaultColDef="defaultColDef"
      :pagination="true"
      :paginationAutoPageSize="true"
      :theme="gridTheme"
      :gridOptions="gridOptions"
      :components="components"
      style="width: 100%; height: 100%"

      @grid-ready="onGridReady"
      @first-data-rendered="onFirstDataRendered"
      @grid-size-changed="onGridSizeChanged"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, defineComponent, h } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { api as http } from '@/services/api'
import { themeMaterial } from 'ag-grid-community'

// Emits to parent
const emit = defineEmits(['toggle-requested', 'delete-requested'])

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
  headerCellHoverBackgroundColor: '#e0e7ff'
})

// ----------------------------
// Vue cell components (render)
// ----------------------------
const UserCell = defineComponent({
  name: 'UserCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    return () => {
      const name = String(props.params.value ?? '')
      const initials = name ? name.split(' ').map(n => n[0]).join('').toUpperCase() : '?'
      const email = props.params.data?.email ?? ''
      return h('div', { class: 'flex items-center h-full' }, [
        h('div', { class: 'flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center' }, [
          h('span', { class: 'text-blue-800 font-medium' }, initials)
        ]),
        h('div', { class: 'ml-3' }, [
          h('div', { class: 'text-sm font-medium text-gray-900' }, name || 'N/A'),
          h('div', { class: 'text-sm text-gray-500' }, email)
        ])
      ])
    }
  }
})

const StatusCell = defineComponent({
  name: 'StatusCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    return () => {
      const active = !!props.params.value
      const cls = active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      const text = active ? 'Active' : 'Inactive'
      return h('div', { class: 'flex items-center h-full' }, [
        h('span', { class: `px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full ${cls}` }, text)
      ])
    }
  }
})

const RoleCell = defineComponent({
  name: 'RoleCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    return () => h('div', { class: 'flex items-center h-full' }, [
      h('span', { class: 'capitalize' }, String(props.params.value ?? ''))
    ])
  }
})

const ActionsCell = defineComponent({
  name: 'ActionsCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    // use gridOptions.context to reach parent emits without globals
    const onToggle = () => props.params.context?.emitToggle?.(props.params.data)
    const onDelete = () => props.params.context?.emitDelete?.(props.params.data)
    return () => {
      const isAdmin = props.params.data?.role === 'admin'
      if (isAdmin) return h('div') // no actions for admins
      const active = !!props.params.data?.is_active
      return h('div', { class: 'flex items-center h-full justify-end gap-2' }, [
        h('button',
          {
            class: `px-3 py-1.5 text-xs font-medium rounded text-white ${active ? 'bg-amber-500 hover:bg-amber-600' : 'bg-green-500 hover:bg-green-600'}`,
            style: { minWidth: '70px' },
            onClick: (e) => { e.stopPropagation(); onToggle() }
          },
          active ? 'Disable' : 'Enable'
        ),
        h('button',
          {
            class: 'px-3 py-1.5 text-xs font-medium rounded text-white bg-red-500 hover:bg-red-600',
            style: { minWidth: '70px' },
            onClick: (e) => { e.stopPropagation(); onDelete() }
          },
          'Delete'
        )
      ])
    }
  }
})

const components = { UserCell, StatusCell, RoleCell, ActionsCell } // used by colDefs via string names. :contentReference[oaicite:5]{index=5}

// ----------------------------
// Column definitions
// ----------------------------
const columnDefs = ref([
  { field: 'full_name', headerName: 'User', flex: 2, minWidth: 220, cellRenderer: 'UserCell' },
  { field: 'is_active', headerName: 'Status', width: 120, cellRenderer: 'StatusCell' },
  { field: 'role', headerName: 'Role', width: 120, cellRenderer: 'RoleCell' },
  { field: 'actions', headerName: 'Actions', width: 260, cellRenderer: 'ActionsCell' }
])

// ----------------------------
// Defaults & options
// ----------------------------
const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle'
}

const rowData = ref([])
const gridApi = ref(null)

const gridOptions = {
  // so button clicks can emit to the parent Component
  context: {
    emitToggle: (row) => emit('toggle-requested', row),
    emitDelete: (row) => emit('delete-requested', row)
  },
  getRowId: p => String(p.data.id) // stabilize row updates across refreshes. :contentReference[oaicite:6]{index=6}
}

// ----------------------------
// Sizing helpers & lifecycle
// ----------------------------
const sizeToFitIfVisible = () => {
  const el = gridApi.value?.getGui?.()
  const visible = el && el.offsetParent !== null && el.clientWidth > 0
  if (visible && gridApi.value && !gridApi.value.isDestroyed()) {
    gridApi.value.sizeColumnsToFit()
  }
}

function onGridReady(params) {
  gridApi.value = params.api
  params.api.addEventListener('gridPreDestroy', () => { gridApi.value = null }) // teardown hook. :contentReference[oaicite:7]{index=7}
}

function onFirstDataRendered() { sizeToFitIfVisible() }
function onGridSizeChanged()  { sizeToFitIfVisible() }

// ----------------------------
// Data
// ----------------------------
onMounted(async () => {
  const resp = await http.get('/user')
  rowData.value = resp.data
  sizeToFitIfVisible()
})
</script>

<style>
:deep(.ag-center-cols-container) {
  display: flex;
  align-items: center;
}
</style>
