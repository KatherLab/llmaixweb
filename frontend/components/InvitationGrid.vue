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
    :theme="theme"
    @grid-ready="gridReady"
  />
</template>

<script setup>
import { AgGridVue } from 'ag-grid-vue3'
const props = defineProps({
  rowData: Array,
  columnDefs: Array,
  defaultColDef: Object,
  search: String,
  theme: Object,
  onGridReady: Function,
})
function gridReady(params) {
  props.onGridReady?.(params)
}
</script>
