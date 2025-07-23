<template>
  <div>
    <AgGridVue
      :rowData="rowData"
      :columnDefs="columnDefs"
      :defaultColDef="defaultColDef"
      :pagination="true"
      :paginationAutoPageSize="true"
      style="width: 100%; height: 500px;"
      :theme="gridTheme"
      @grid-ready="onGridReady"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { api } from '@/services/api'
import { themeMaterial } from 'ag-grid-community'

// Build a clean, modern Material theme:
const gridTheme = themeMaterial.withParams({
  spacing: 12,
  borderRadius: 8,
  rowHeight: '56px',
  headerHeight: '48px',
  listItemHeight: '40px',
  accentColor: '#3b82f6',      // Tailwind blue-500
  rowHoverColor: '#f3f4f6',     // Tailwind gray-100
  headerBackgroundColor: '#f9fafb',
  headerTextColor: '#111827',
  headerCellHoverBackgroundColor: '#e0e7ff'
})

const columnDefs = ref([
  {
    field: 'full_name',
    headerName: 'User',
    flex: 2,
    minWidth: 220,
    cellRenderer: params => {
      const initials = params.value?.split(' ').map(n => n[0]).join('').toUpperCase()
      const div = document.createElement('div')
      div.className = 'flex items-center h-full'
      div.innerHTML = `
        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
          <span class="text-blue-800 font-medium">${initials}</span>
        </div>
        <div class="ml-3">
          <div class="text-sm font-medium text-gray-900">${params.value}</div>
          <div class="text-sm text-gray-500">${params.data.email}</div>
        </div>`
      return div
    }
  },
  {
    field: 'is_active',
    headerName: 'Status',
    width: 120,
    cellRenderer: params => {
      const cls = params.value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      const text = params.value ? 'Active' : 'Inactive'
      const div = document.createElement('div')
      div.className = 'flex items-center h-full'
      div.innerHTML = `<span class="px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full ${cls}">${text}</span>`
      return div
    }
  },
  {
    field: 'role',
    headerName: 'Role',
    width: 120,
    cellRenderer: params => {
      const div = document.createElement('div')
      div.className = 'flex items-center h-full'
      div.innerHTML = `<span class="capitalize">${params.value}</span>`
      return div
    }
  },
  {
    field: 'actions',
    headerName: 'Actions',
    width: 260,
    cellRenderer: params => {
      const isAdmin = params.data.role === 'admin'
      const div = document.createElement('div')
      div.className = 'flex items-center h-full justify-end gap-2'
      if (!isAdmin) {
        const toggleBtn = document.createElement('button')
        toggleBtn.className = `px-3 py-1.5 text-xs font-medium rounded text-white ${
          params.data.is_active ? 'bg-amber-500 hover:bg-amber-600' : 'bg-green-500 hover:bg-green-600'}`
        toggleBtn.textContent = params.data.is_active ? 'Disable' : 'Enable'
        toggleBtn.style.minWidth = '70px'
        toggleBtn.addEventListener('click', () => emit('toggle-requested', params.data))
        div.appendChild(toggleBtn)

        const deleteBtn = document.createElement('button')
        deleteBtn.className = 'px-3 py-1.5 text-xs font-medium rounded text-white bg-red-500 hover:bg-red-600'
        deleteBtn.textContent = 'Delete'
        deleteBtn.style.minWidth = '70px'
        deleteBtn.addEventListener('click', () => emit('delete-requested', params.data))
        div.appendChild(deleteBtn)
      }
      return div
    }
  }
])

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle'
}

const rowData = ref([])
const gridApi = ref(null)
const emit = defineEmits(['toggle-requested','delete-requested'])

function onGridReady(params) {
  gridApi.value = params.api
  params.api.sizeColumnsToFit()
  window.addEventListener('resize', () => params.api.sizeColumnsToFit())
}

onMounted(async () => {
  const resp = await api.get('/user')
  rowData.value = resp.data
  if (gridApi.value) gridApi.value.sizeColumnsToFit()
})
</script>

<style>
:deep(.ag-center-cols-container) {
  display: flex;
  align-items: center;
}
</style>
