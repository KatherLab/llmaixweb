<template>
  <div class="h-full flex flex-col min-h-0">
    <!-- Header with title and admin toggle -->
    <div
      class="flex items-center justify-between mb-3 pb-3 border-b border-gray-200 dark:border-slate-700"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Your Projects</h2>
      <div v-if="isAdmin" class="flex items-center">
        <label class="inline-flex items-center gap-2 cursor-pointer select-none">
          <input
            v-model="showAllProjects"
            type="checkbox"
            class="rounded border-gray-300 dark:border-slate-600 text-blue-600 dark:text-blue-400 shadow-sm focus:ring-blue-500"
          />
          <span class="text-sm text-gray-700 dark:text-slate-300">Show all users' projects</span>
        </label>
      </div>
    </div>

    <!-- Content area -->
    <div class="flex-1 min-h-0">
      <!-- Loading Indicator -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <LoadingSpinner size="large" />
      </div>

      <!-- Grid -->
      <div v-else class="h-full">
        <AgGridVue
          :row-data="rowData"
          :column-defs="columnDefs"
          :default-col-def="defaultColDef"
          :grid-options="gridOptions"
          :pagination="true"
          :pagination-page-size="20"
          :pagination-auto-page-size="false"
          :theme="gridTheme"
          :components="components"
          class="h-full w-full"
          @grid-ready="onGridReady"
          @first-data-rendered="onFirstDataRendered"
          @grid-size-changed="onGridSizeChanged"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
  onActivated,
  nextTick,
  defineComponent,
  h,
} from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { projectsApi } from '@/services/projectsApi'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useGridTheme } from '@/composables/useGridTheme'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatDate } from '@/utils/formatters'

// ---- auth / router ----
const authStore = useAuthStore()
const router = useRouter()

// ---- theme (v34 :theme) ----
// Shared ag-grid theme with dark-mode support (re-themes on toggle)
const { gridTheme } = useGridTheme({ rowHeight: 56, controlBorderRadius: 8 })

// ---- state ----
const rowData = ref([])
const gridApi = ref(null)
const isAdmin = computed(() => authStore.user?.role === 'admin')
const showAllProjects = ref(false)
const isLoading = ref(true)

// ---- Vue cell components (render functions; no runtime compiler needed) ----
const ProjectCell = defineComponent({
  name: 'ProjectCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const router = useRouter()
    const go = () => router.push(`/projects/${props.params.data.id}`)
    return () =>
      h(
        'div',
        {
          class:
            'flex items-center h-full cursor-pointer text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300',
          onClick: go,
        },
        [h('span', { class: 'font-medium' }, String(props.params.value ?? ''))],
      )
  },
})

const DocumentCountCell = defineComponent({
  name: 'DocumentCountCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    return () => {
      const count = props.params.value ?? 0
      return h('div', { class: 'flex items-center h-full' }, [
        h(
          'span',
          {
            class:
              'px-2.5 py-1 inline-flex text-xs leading-4 font-medium rounded-full bg-blue-50 dark:bg-slate-700 text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-slate-600',
          },
          `${count} document${count !== 1 ? 's' : ''}`,
        ),
      ])
    }
  },
})

const ActionsCell = defineComponent({
  name: 'ActionsCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    const router = useRouter()
    const view = () => router.push(`/projects/${props.params.data.id}`)
    return () =>
      h('div', { class: 'flex items-center h-full justify-end' }, [
        h(
          'button',
          {
            class:
              'inline-flex items-center px-2.5 py-1 text-xs font-medium rounded text-white bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-500',
            onClick: (e) => {
              e.stopPropagation()
              view()
            },
          },
          'View',
        ),
      ])
  },
})

const UserCell = defineComponent({
  name: 'UserCell',
  props: { params: { type: Object, required: true } },
  setup(props) {
    return () => {
      const user = props.params.value || {}
      const initials =
        (user.full_name || '')
          .split(' ')
          .map((n) => n[0])
          .join('') || '?'
      return h('div', { class: 'flex items-center h-full' }, [
        h('div', { class: 'flex items-center' }, [
          h(
            'div',
            {
              class:
                'flex-shrink-0 h-8 w-8 rounded-full bg-blue-100 dark:bg-slate-700 flex items-center justify-center',
            },
            [
              h(
                'span',
                { class: 'text-blue-800 dark:text-blue-300 font-medium text-xs' },
                initials,
              ),
            ],
          ),
          h('div', { class: 'ml-2' }, [
            h(
              'div',
              { class: 'text-sm font-medium text-gray-900 dark:text-white' },
              user.full_name || 'N/A',
            ),
            h('div', { class: 'text-xs text-gray-500 dark:text-slate-400' }, user.email || 'N/A'),
          ]),
        ]),
      ])
    }
  },
})

const components = { ProjectCell, DocumentCountCell, ActionsCell, UserCell } // ag-grid-vue3 will use these by name. :contentReference[oaicite:2]{index=2}

// ---- column defs ----
const baseColumnsComputed = computed(() => {
  const cols = [
    { field: 'name', headerName: 'Project', flex: 2, minWidth: 250, cellRenderer: 'ProjectCell' },
    {
      field: 'document_count',
      headerName: 'Documents',
      width: 140,
      cellRenderer: 'DocumentCountCell',
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 160,
      valueFormatter: (p) => (p.value ? formatDate(p.value) : ''),
    },
    { field: 'actions', headerName: 'Actions', width: 120, cellRenderer: 'ActionsCell' },
  ]
  if (isAdmin.value) {
    cols.splice(1, 0, {
      field: 'user',
      headerName: 'User',
      width: 260,
      cellRenderer: 'UserCell',
      // IMPORTANT for v34: when the underlying value is an object, provide a valueFormatter
      // so the grid can coerce to string for filters/sorts/fallbacks (avoids warning #48).
      valueFormatter: (p) => {
        const u = p.value
        return u ? `${u.full_name ?? 'N/A'} <${u.email ?? 'N/A'}>` : ''
      },
    })
  }
  return cols
})

// materialize to a ref so we can preserve/restore column state on updates
const columnDefs = ref(baseColumnsComputed.value)
watch(baseColumnsComputed, (defs) => {
  columnDefs.value = defs
})

// ---- default col def ----
const defaultColDef = ref({
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle',
})

// ---- grid options ----
const gridOptions = {
  getRowId: (p) => String(p.data.id), // stabilize updates
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
  params.api.addEventListener('gridPreDestroy', () => {
    gridApi.value = null
  })
}

const onFirstDataRendered = () => {
  sizeToFitIfVisible()
}
const onGridSizeChanged = () => {
  sizeToFitIfVisible()
}

onActivated(async () => {
  await nextTick()
  sizeToFitIfVisible()
})
onBeforeUnmount(() => {
  gridApi.value = null
})

// ---- data ----
const loadProjects = async () => {
  isLoading.value = true
  try {
    const params = isAdmin.value && showAllProjects.value ? { all: true } : {}
    const response = await projectsApi.list(params)
    rowData.value = response.data.map((project) => ({
      ...project,
      document_count: project.document_count ?? 0,
      user: {
        full_name: project.owner?.full_name || 'N/A',
        email: project.owner?.email || 'N/A',
      },
    }))
    sizeToFitIfVisible()
  } catch (err) {
    console.error('Error loading projects:', err)
  } finally {
    isLoading.value = false
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
  showAllProjects.value = false
  await loadProjects()
})

// reload when show all projects toggle changes
watch(showAllProjects, async () => {
  await loadProjects()
})

// initial load
onMounted(async () => {
  await loadProjects()
})
</script>

<style lang="postcss">
:deep(.ag-center-cols-container) {
  width: 100%;
}
:deep(.ag-row) {
  display: flex;
  align-items: center;
}
:deep(.ag-cell) {
  display: flex;
  align-items: center;
  height: 100% !important;
  line-height: normal;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
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
html.dark :deep(.ag-header-cell-label-container) {
  color: #e2e8f0 !important;
}
html.dark :deep(.ag-header-filter-input) {
  background-color: #334155 !important;
  border-color: #475569 !important;
  color: #e2e8f0 !important;
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
