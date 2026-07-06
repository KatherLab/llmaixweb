<template>
  <DataTable
    :columns="columns"
    :items="pagedUsers"
    row-key="id"
    row-clickable
    :pagination="tablePagination"
    :page-size-options="[10, 25, 50]"
    item-label="users"
    empty-title="No users found"
    @row-click="$emit('edit-requested', $event as UserResponse)"
    @page-change="handlePageChange"
    @page-size-change="handlePageSizeChange"
  >
    <template #cell-full_name="{ row: user }">
      <div class="flex items-center">
        <div
          class="flex-shrink-0 h-10 w-10 rounded-full bg-primary-soft flex items-center justify-center"
        >
          <span class="text-primary font-medium">{{ initials(user as UserResponse) }}</span>
        </div>
        <div class="ml-3">
          <div class="text-sm font-medium text-content">
            {{ user.full_name || 'N/A' }}
          </div>
          <div class="text-sm text-content-subtle">{{ user.email }}</div>
        </div>
      </div>
    </template>

    <template #cell-is_active="{ row: user }">
      <span
        :class="[
          'px-3 py-1.5 inline-flex text-xs leading-5 font-semibold rounded-full',
          user.is_active
            ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400'
            : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
        ]"
      >
        {{ user.is_active ? 'Active' : 'Inactive' }}
      </span>
    </template>

    <template #cell-role="{ row: user }">
      <span class="text-content capitalize">{{ user.role }}</span>
    </template>

    <template #row-actions="{ row: user }">
      <BaseButton
        variant="secondary"
        size="sm"
        @click.stop="$emit('edit-requested', user as UserResponse)"
      >
        Edit
      </BaseButton>
    </template>
  </DataTable>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { UserResponse } from '@/types'
import DataTable from '@/components/common/DataTable.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { usePagination } from '@/composables/usePagination'

interface Props {
  rowData?: UserResponse[]
  search?: string
}

const props = withDefaults(defineProps<Props>(), {
  rowData: () => [],
  search: '',
})

defineEmits<{
  (e: 'edit-requested', user: UserResponse): void
}>()

const currentPage = ref(1)
const pageSize = ref(10)

// Client-side search (the original ag-grid `search` prop was never wired — this fixes it)
const filteredUsers = computed(() => {
  const q = props.search.trim().toLowerCase()
  if (!q) return props.rowData
  return props.rowData.filter(
    (u) =>
      (u.full_name || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q),
  )
})

const totalCount = computed(() => filteredUsers.value.length)

// usePagination reads getTotal eagerly — totalCount is a computed declared above, safe.
const pagination = usePagination({ getTotal: () => totalCount.value, pageSize: pageSize.value })

// keep currentPage valid when the filtered set shrinks
watch(totalCount, () => {
  if (currentPage.value > pagination.totalPages.value) {
    currentPage.value = pagination.totalPages.value
  }
})

const pagedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredUsers.value.slice(start, start + pageSize.value)
})

const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: pageSize.value,
  total: totalCount.value,
  total_pages: pagination.totalPages.value,
}))

// Override the pagination object shape DataTable expects
function handlePageChange(page: number): void {
  currentPage.value = page
}
function handlePageSizeChange(size: number): void {
  pageSize.value = size
  currentPage.value = 1
}

const initials = (user: UserResponse): string => {
  const name = user.full_name || ''
  if (!name) return '?'
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
}

const columns = [
  { key: 'full_name', label: 'User', sortable: true },
  { key: 'is_active', label: 'Status', sortable: true },
  { key: 'role', label: 'Role', sortable: true },
]
</script>
