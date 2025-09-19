<template>
  <div style="height: 500px; width: 100%">
    <AgGridVue
      :rowData="rowData"
      :columnDefs="columnDefs"
      :defaultColDef="defaultColDef"
      :gridOptions="gridOptions"
      :pagination="true"
      :paginationAutoPageSize="true"
      :theme="gridTheme"
      :components="components"

      style="width: 100%; height: 100%"

      @grid-ready="onGridReady"
      @first-data-rendered="onFirstDataRendered"
      @grid-size-changed="onGridSizeChanged"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, onActivated, nextTick, defineComponent, h } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { api as http } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { themeMaterial } from 'ag-grid-community'

// ---- auth / router ----
const authStore = useAuthStore()
const router = useRouter()

// ---- theme (v34 :theme) ----
const gridTheme = themeMaterial.withParams({
  spacing: 16,
  borderRadius: 4,
  rowHeight: 56,
  headerHeight: 48,
  accentColor: '#3b82f6',
  rowHoverColor: '#f3f4f6',
  primaryColor: '#3b82f6',
  cellHorizontalPadding: 16
})

// ---- state ----
const rowData = ref([])
const gridApi = ref(null)
const isAdmin = computed(() => authStore.user?.role === 'admin')

// ---- Vue cell components (render functions; no runtime compiler needed) ----
const ProjectCell = defineComponent({
  name: 'ProjectCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const router = useRouter()
    const go = () => router.push(`/projects/${props.params.data.id}`)
    return () =>
      h('div',
        { class: 'flex items-center h-full cursor-pointer text-blue-600 hover:text-blue-800', onClick: go },
        [
          // keep it simple; omit the SVG to keep h() readable
          h('span', { class: 'font-medium' }, String(props.params.value ?? ''))
        ]
      )
  }
})

const StatusCell = defineComponent({
  name: 'StatusCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    return () => {
      const v = String(props.params.value ?? '')
      const map = {
        active: 'bg-green-100 text-green-800',
        inactive: 'bg-red-100 text-red-800',
        pending: 'bg-yellow-100 text-yellow-800'
      }
      const klass = map[v] || 'bg-gray-100 text-gray-800'
      const label = v ? v.charAt(0).toUpperCase() + v.slice(1) : '—'
      return h('div', { class: 'flex items-center h-full' }, [
        h('span', { class: `px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full ${klass}` }, label)
      ])
    }
  }
})

const ActionsCell = defineComponent({
  name: 'ActionsCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const router = useRouter()
    const view = () => router.push(`/projects/${props.params.data.id}`)
    return () =>
      h('div', { class: 'flex items-center h-full justify-end' }, [
        h('button',
          { class: 'inline-flex items-center px-3 py-1.5 text-xs font-medium rounded text-white bg-blue-500 hover:bg-blue-600', onClick: e => { e.stopPropagation(); view() } },
          'View'
        )
      ])
  }
})

const UserCell = defineComponent({
  name: 'UserCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    return () => {
      const user = props.params.value || {}
      const initials = (user.full_name || '').split(' ').map(n => n[0]).join('') || '?'
      return h('div', { class: 'flex items-center h-full' }, [
        h('div', { class: 'flex items-center' }, [
          h('div', { class: 'flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center' }, [
            h('span', { class: 'text-blue-800 font-medium' }, initials)
          ]),
          h('div', { class: 'ml-3' }, [
            h('div', { class: 'text-sm font-medium text-gray-900' }, user.full_name || 'N/A'),
            h('div', { class: 'text-sm text-gray-500' }, user.email || 'N/A')
          ])
        ])
      ])
    }
  }
})

const components = { ProjectCell, StatusCell, ActionsCell, UserCell } // ag-grid-vue3 will use these by name. :contentReference[oaicite:2]{index=2}

// ---- column defs ----
const baseColumnsComputed = computed(() => {
  const cols = [
    { field: 'name', headerName: 'Project', flex: 2, minWidth: 250, cellRenderer: 'ProjectCell' },
    { field: 'status', headerName: 'Status', width: 140, cellRenderer: 'StatusCell' },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 160,
      valueFormatter: p => p.value ? new Date(p.value).toLocaleDateString() : ''
    },
    { field: 'actions', headerName: 'Actions', width: 120, cellRenderer: 'ActionsCell' }
  ]
  if (isAdmin.value) {
    cols.splice(1, 0, {
      field: 'user',
      headerName: 'User',
      width: 260,
      cellRenderer: 'UserCell',
      // IMPORTANT for v34: when the underlying value is an object, provide a valueFormatter
      // so the grid can coerce to string for filters/sorts/fallbacks (avoids warning #48).
      valueFormatter: p => {
        const u = p.value
        return u ? `${u.full_name ?? 'N/A'} <${u.email ?? 'N/A'}>` : ''
      }
    })
  }
  return cols
})

// materialize to a ref so we can preserve/restore column state on updates
const columnDefs = ref(baseColumnsComputed.value)
watch(baseColumnsComputed, (defs) => { columnDefs.value = defs })

// ---- default col def ----
const defaultColDef = ref({
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle'
})

// ---- grid options ----
const gridOptions = {
  getRowId: p => String(p.data.id) // stabilize updates
} // :contentReference[oaicite:3]{index=3}

// ---- helpers ----
const sizeToFitIfVisible = () => {
  const el = gridApi.value?.getGui?.()
  const visible = el && el.offsetParent !== null && el.clientWidth > 0
  if (visible && gridApi.value && !gridApi.value.isDestroyed()) {
    gridApi.value.sizeColumnsToFit()
  }
}

// ---- lifecycle ----
const onGridReady = (params) => {
  gridApi.value = params.api
  params.api.addEventListener('gridPreDestroy', () => { gridApi.value = null })
}

const onFirstDataRendered = () => { sizeToFitIfVisible() }
const onGridSizeChanged  = () => { sizeToFitIfVisible() }

onActivated(async () => { await nextTick(); sizeToFitIfVisible() })
onBeforeUnmount(() => { gridApi.value = null })

// ---- data ----
const loadProjects = async () => {
  try {
    const response = await http.get('/project')
    rowData.value = response.data.map(project => ({
      ...project,
      user: {
        full_name: project.owner?.full_name || 'N/A',
        email: project.owner?.email || 'N/A'
      }
    }))
    sizeToFitIfVisible()
  } catch (err) {
    console.error('Error loading projects:', err)
  }
}

// toggle admin view -> update defs with v31+ API and preserve user state
watch(isAdmin, async () => {
  const api = gridApi.value
  const savedState = api?.getColumnState?.() ?? null
  if (api && !api.isDestroyed()) {
    api.updateGridOptions({ columnDefs: baseColumnsComputed.value }) // v31+ options API
    if (savedState) api.applyColumnState({ state: savedState, applyOrder: true })
  }
  await loadProjects()
})

// initial load
onMounted(async () => { await loadProjects() })
</script>

<style lang="postcss">
:deep(.ag-center-cols-container) { width: 100%; }
:deep(.ag-row) { display: flex; align-items: center; }
:deep(.ag-cell) {
  display: flex; align-items: center; height: 100% !important;
  line-height: normal; padding-top: 0 !important; padding-bottom: 0 !important;
}
/* Theme class is injected by :theme */
</style>
