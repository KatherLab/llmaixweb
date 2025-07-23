<template>
  <AgGridVue
    :rowData="rowData"
    :columnDefs="columnDefs"
    :defaultColDef="defaultColDef"
    pagination
    paginationAutoPageSize
    style="width:100%;height:320px"
    class="mx-auto"
    :quickFilterText="search"
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
  onGridReady: Function
})
function gridReady(params) {
  props.onGridReady?.(params)
}
</script>
