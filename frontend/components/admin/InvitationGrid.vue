<template>
  <DataTable
    :columns="columns"
    :items="pagedInvitations"
    row-key="id"
    :pagination="tablePagination"
    :page-size-options="[10, 25, 50]"
    item-label="invitations"
    empty-title="No invitations found"
    @page-change="handlePageChange"
    @page-size-change="handlePageSizeChange"
  >
    <template #cell-email="{ row: invitation }">
      <span class="text-sm font-medium text-content">{{ invitation.email }}</span>
    </template>

    <template #cell-is_used="{ row: invitation }">
      <span
        v-if="invitation.is_used"
        class="bg-surface-sunken text-content-muted px-2 py-0.5 rounded-full text-xs"
      >
        Yes
      </span>
      <span
        v-else
        class="bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-0.5 rounded-full text-xs"
      >
        No
      </span>
    </template>

    <template #row-actions="{ row: invitation }">
      <BaseButton
        variant="secondary"
        size="sm"
        tone="red"
        @click.stop="$emit('delete-requested', invitation as InvitationResponse)"
      >
        Delete
      </BaseButton>
    </template>
  </DataTable>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { InvitationResponse } from '@/types'
import DataTable from '@/components/common/DataTable.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { usePagination } from '@/composables/usePagination'

interface Props {
  rowData?: InvitationResponse[]
  search?: string
}

const props = withDefaults(defineProps<Props>(), {
  rowData: () => [],
  search: '',
})

defineEmits<{
  (e: 'delete-requested', invitation: InvitationResponse): void
}>()

const currentPage = ref(1)
const pageSize = ref(10)

// Client-side search (replaces ag-grid's quick-filter-text)
const filteredInvitations = computed(() => {
  const q = props.search.trim().toLowerCase()
  if (!q) return props.rowData
  return props.rowData.filter((inv) => (inv.email || '').toLowerCase().includes(q))
})

const totalCount = computed(() => filteredInvitations.value.length)

const pagination = usePagination({ getTotal: () => totalCount.value, pageSize: pageSize.value })

watch(totalCount, () => {
  if (currentPage.value > pagination.totalPages.value) {
    currentPage.value = pagination.totalPages.value
  }
})

const pagedInvitations = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredInvitations.value.slice(start, start + pageSize.value)
})

const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: pageSize.value,
  total: totalCount.value,
  total_pages: pagination.totalPages.value,
}))

function handlePageChange(page: number): void {
  currentPage.value = page
}
function handlePageSizeChange(size: number): void {
  pageSize.value = size
  currentPage.value = 1
}

const columns = [
  { key: 'email', label: 'Email', sortable: true },
  { key: 'is_used', label: 'Used', sortable: true },
]
</script>
