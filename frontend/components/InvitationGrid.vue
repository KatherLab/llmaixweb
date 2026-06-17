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
import { ref } from 'vue'
import { AgGridVue } from 'ag-grid-vue3'
import { themeMaterial } from 'ag-grid-community'

const props = defineProps({
  rowData: { type: Array, default: () => [] },
  columnDefs: { type: Array, default: () => [] },
  defaultColDef: { type: Object, default: () => ({}) },
  search: { type: String, default: '' },
  theme: { type: Object, default: null },
  onGridReady: { type: Function, default: null },
})

// Theme with dark mode support
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
    rowHeight: 40,
    headerHeight: 48,
    listItemHeight: 40,
    accentColor: '#3b82f6',
    rowHoverColor: darkMode ? '#1e293b' : '#f3f4f6',
    headerBackgroundColor: darkMode ? '#1e293b' : '#f9fafb',
    headerTextColor: darkMode ? '#e2e8f0' : '#111827',
    headerCellHoverBackgroundColor: darkMode ? '#334155' : '#e0e7ff',
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

function gridReady(params) {
  props.onGridReady?.(params)
}
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
