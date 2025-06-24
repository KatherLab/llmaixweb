<template>
  <div>
    <!-- The AG Grid component with modern material theme -->
    <AgGridVue
      :rowData="rowData"
      :columnDefs="columnDefs"
      :defaultColDef="defaultColDef"
      :pagination="true"
      :paginationAutoPageSize="true"
      style="width: 100%; height: 500px"
      :theme="gridTheme"
      @grid-ready="onGridReady"
    >
    </AgGridVue>
  </div>
</template>

<script setup>
import { ref, onMounted, defineExpose } from 'vue';
import { AgGridVue } from 'ag-grid-vue3';
import { api } from '@/services/api';
import { themeMaterial } from 'ag-grid-community'; // Import Material theme

// Create customized Material theme
const gridTheme = themeMaterial.withParams({
  // Customize colors and spacing
  spacing: 16,
  borderRadius: 4, // Material design typically uses smaller border radius
  rowHeight: 56, // Increased for better vertical alignment
  headerHeight: 48,
  accentColor: '#3b82f6', // blue-500
  rowHoverColor: '#f3f4f6', // gray-100
  primaryColor: '#3b82f6', // blue-500
  cellHorizontalPadding: 16
});

// Define props and emits
const emit = defineEmits(['toggle-requested', 'delete-requested']);

const columnDefs = ref([
  {
    field: 'full_name',
    headerName: 'User',
    flex: 2,
    minWidth: 220,
    cellRenderer: params => {
      const initials = getUserInitials(params.value);
      const div = document.createElement('div');
      div.className = 'flex items-center h-full';
      div.innerHTML = `
        <div class="flex items-center">
          <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
            <span class="text-blue-800 font-medium">${initials}</span>
          </div>
          <div class="ml-3">
            <div class="text-sm font-medium text-gray-900">${params.value}</div>
            <div class="text-sm text-gray-500">${params.data.email}</div>
          </div>
        </div>
      `;
      return div;
    },
  },
  {
    field: 'is_active',
    headerName: 'Status',
    width: 120,
    cellRenderer: params => {
      const div = document.createElement('div');
      div.className = 'flex items-center h-full';
      div.innerHTML = `
        <span class="px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full ${
          params.value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }">
          ${params.value ? 'Active' : 'Inactive'}
        </span>
      `;
      return div;
    },
  },
  {
    field: 'role',
    headerName: 'Role',
    width: 120,
    cellRenderer: params => {
      const div = document.createElement('div');
      div.className = 'flex items-center h-full';
      div.innerHTML = `<span class="capitalize">${params.value}</span>`;
      return div;
    },
  },
  {
    field: 'actions',
    headerName: 'Actions',
    width: 180,
    cellRenderer: params => {
      const isAdmin = params.data.role === 'admin';
      const div = document.createElement('div');
      div.className = 'flex items-center h-full justify-end gap-2';

      // Only create toggle button if not admin
      if (!isAdmin) {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'px-3 py-1.5 text-xs font-medium rounded text-white ' +
          (params.data.is_active ? 'bg-amber-500 hover:bg-amber-600' : 'bg-green-500 hover:bg-green-600');
        toggleBtn.textContent = params.data.is_active ? 'Disable' : 'Enable';
        toggleBtn.style.minWidth = '70px'; // Ensure minimum width for button
        toggleBtn.addEventListener('click', () => {
          // Use emit function to communicate with parent
          emit('toggle-requested', params.data);
        });
        div.appendChild(toggleBtn);
      }

      // Only create delete button if not admin
      if (!isAdmin) {
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'px-3 py-1.5 text-xs font-medium rounded text-white bg-red-500 hover:bg-red-600';
        deleteBtn.textContent = 'Delete';
        deleteBtn.style.minWidth = '70px'; // Ensure minimum width for button
        deleteBtn.addEventListener('click', () => {
          // Use emit function to communicate with parent
          emit('delete-requested', params.data);
        });
        div.appendChild(deleteBtn);
      }

      return div;
    },
  },
]);

const rowData = ref([]);
const defaultColDef = ref({
  sortable: true,
  filter: true,
  resizable: true,
  cellClass: 'align-middle', // Align all cells vertically middle
});

// Grid API reference
const gridApi = ref(null);

// Handle grid ready event
const onGridReady = (params) => {
  gridApi.value = params.api;

  // Auto-size columns to fit the available space
  setTimeout(() => {
    params.api.sizeColumnsToFit();
  });

  // Handle window resize
  window.addEventListener('resize', () => {
    setTimeout(() => {
      params.api.sizeColumnsToFit();
    });
  });
};

// Load data on mount
onMounted(async () => {
  await loadUsers();
});

// Methods to fetch and manage users
const loadUsers = async () => {
  try {
    const response = await api.get('/user');
    rowData.value = response.data;

    // Resize columns after data is loaded
    if (gridApi.value) {
      setTimeout(() => {
        gridApi.value.sizeColumnsToFit();
      });
    }
  } catch (error) {
    console.error('Error loading users:', error);
  }
};

const getUserInitials = (name) => {
  if (!name) return '';
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase();
};

// Expose methods to parent component
defineExpose({
  loadUsers
});
</script>

<style>
/* Additional styling for better vertical alignment */
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
</style>
