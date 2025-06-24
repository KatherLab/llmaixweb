<template>
  <div class="ag-theme-material" style="height: 500px; width: 100%">
    <AgGridVue
      :rowData="rowData"
      :columnDefs="columnDefs"
      :defaultColDef="defaultColDef"
      :pagination="true"
      :paginationAutoPageSize="true"
      style="width: 100%; height: 100%"
      :theme="gridTheme"
      @grid-ready="onGridReady"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { themeMaterial } from 'ag-grid-community'

const authStore = useAuthStore()
const router = useRouter()

// Theme customization
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

// Reactive state
const rowData = ref([])
const gridApi = ref(null)

// Role-based visibility
const isAdmin = computed(() => authStore.user?.role === 'admin')

// Column definitions (with conditional admin column)
const columnDefs = computed(() => {
  const baseColumns = [
    {
      field: 'name',
      headerName: 'Project',
      flex: 2,
      minWidth: 250,
      cellRenderer: params => {
        const div = document.createElement('div')
        div.className = 'flex items-center h-full cursor-pointer text-blue-600 hover:text-blue-800'
        div.innerHTML = `
          <div class="flex items-center">
            <svg class="h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span class="font-medium">${params.value}</span>
          </div>`
        div.addEventListener('click', () => router.push(`/projects/${params.data.id}`))
        return div
      }
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 140,
      cellRenderer: params => {
        const statusColors = {
          active: 'bg-green-100 text-green-800',
          inactive: 'bg-red-100 text-red-800',
          pending: 'bg-yellow-100 text-yellow-800'
        }
        const div = document.createElement('div')
        div.className = 'flex items-center h-full'
        div.innerHTML = `
          <span class="px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColors[params.value] || 'bg-gray-100 text-gray-800'}">
            ${params.value.charAt(0).toUpperCase() + params.value.slice(1)}
          </span>`
        return div
      }
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 160,
      valueFormatter: params => new Date(params.value).toLocaleDateString()
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 120,
      cellRenderer: params => {
        const div = document.createElement('div')
        div.className = 'flex items-center h-full justify-end'
        const viewBtn = document.createElement('button')
        viewBtn.className = 'inline-flex items-center px-3 py-1.5 text-xs font-medium rounded text-white bg-blue-500 hover:bg-blue-600'
        viewBtn.innerHTML = `
          <svg class="h-4 w-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          View`
        viewBtn.addEventListener('click', () => router.push(`/projects/${params.data.id}`))
        div.appendChild(viewBtn)
        return div
      }
    }
  ]

  // Add user column for admins
  if (isAdmin.value) {
    baseColumns.splice(1, 0, {
      field: 'user',
      headerName: 'User',
      width: 200,
      valueFormatter: params => {
        const user = params.value
        return user ? `${user.full_name} <${user.email}>` : ''
      },
      cellRenderer: params => {
        const user = params.value
        const initials = (user?.full_name?.split(' ').map(n => n[0]).join('') || '?')
        const div = document.createElement('div')
        div.className = 'flex items-center h-full'
        div.innerHTML = `
          <div class="flex items-center">
            <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
              <span class="text-blue-800 font-medium">${initials}</span>
            </div>
            <div class="ml-3">
              <div class="text-sm font-medium text-gray-900">${user?.full_name || 'N/A'}</div>
              <div class="text-sm text-gray-500">${user?.email || 'N/A'}</div>
            </div>
          </div>
        `
        return div
      }
    })
  }

  return baseColumns
})

// Default column settings
const defaultColDef = ref({
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle'
})

// Grid lifecycle
const onGridReady = (params) => {
  gridApi.value = params.api

  // Handle grid destroy
  params.api.addEventListener('gridPreDestroy', () => {
    gridApi.value = null
  })

  // Resize handler
  const resizeHandler = () => {
    if (gridApi.value && !gridApi.value.isDestroyed()) {
      setTimeout(() => gridApi.value.sizeColumnsToFit())
    }
  }

  window.addEventListener('resize', resizeHandler)

  // Initial column fit
  setTimeout(() => {
    if (gridApi.value && !gridApi.value.isDestroyed()) {
      gridApi.value.sizeColumnsToFit()
    }
  })
}

// Load projects
const loadProjects = async () => {
  try {
    const endpoint = isAdmin.value ? '/project' : '/project' //`/project/user/${authStore.user.id}`
    const response = await api.get(endpoint)
    rowData.value = response.data.map(project => ({
      ...project,
      user: {
        full_name: project.owner?.full_name || 'N/A',
        email: project.owner?.email || 'N/A'
      }
    }))

    if (gridApi.value && !gridApi.value.isDestroyed()) {
      setTimeout(() => gridApi.value.sizeColumnsToFit())
    }
  } catch (error) {
    console.error('Error loading projects:', error)
  }
}

// Watch for role changes
watch(isAdmin, async (newVal) => {
  if (gridApi.value && !gridApi.value.isDestroyed()) {
    gridApi.value.setColumnDefs(columnDefs.value)
    await loadProjects()
  }
})

// Initial load
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

.ag-theme-material {
  @apply bg-white;
}
</style>