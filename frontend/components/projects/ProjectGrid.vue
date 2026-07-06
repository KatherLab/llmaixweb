<template>
  <div class="h-full flex flex-col min-h-0">
    <!-- Header with title and admin toggle -->
    <div class="flex items-center justify-between mb-3 pb-3 border-b border-default">
      <h2 class="text-lg font-semibold text-content">Your Projects</h2>
      <div v-if="isAdmin" class="flex items-center">
        <label class="inline-flex items-center gap-2 cursor-pointer select-none">
          <input
            v-model="showAllProjects"
            type="checkbox"
            class="rounded border-strong text-primary shadow-sm focus:ring-ring"
          />
          <span class="text-sm text-content-muted">Show all users' projects</span>
        </label>
      </div>
    </div>

    <!-- Content area -->
    <div class="flex-1 min-h-0">
      <!-- Loading Indicator -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <LoadingSpinner size="large" />
      </div>

      <DataTable
        v-else
        :columns="columns"
        :items="pagedProjects"
        row-key="id"
        row-clickable
        :pagination="tablePagination"
        :page-size-options="[20, 50, 100]"
        item-label="projects"
        empty-title="No projects found"
        @row-click="goToProject"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
      >
        <template #cell-name="{ row: project }">
          <span class="font-medium text-primary hover:text-primary cursor-pointer">
            {{ project.name }}
          </span>
        </template>

        <template #cell-document_count="{ row: project }">
          <span
            class="px-2.5 py-1 inline-flex text-xs leading-4 font-medium rounded-full bg-primary-soft text-primary border border-default"
          >
            {{ project.document_count }} document{{ project.document_count !== 1 ? 's' : '' }}
          </span>
        </template>

        <template #cell-user="{ row: project }">
          <div class="flex items-center">
            <div
              class="flex-shrink-0 h-8 w-8 rounded-full bg-primary-soft flex items-center justify-center"
            >
              <span class="text-primary font-medium text-xs">{{ project.user.initials }}</span>
            </div>
            <div class="ml-2">
              <div class="text-sm font-medium text-content">
                {{ project.user.full_name }}
              </div>
              <div class="text-xs text-content-subtle">{{ project.user.email }}</div>
            </div>
          </div>
        </template>

        <template #cell-created_at="{ row: project }">
          <span class="text-sm text-content-subtle">
            {{ project.created_at ? formatDate(project.created_at) : '' }}
          </span>
        </template>

        <template #row-actions="{ row: project }">
          <BaseButton variant="primary" size="sm" @click.stop="goToProject(project as ProjectRow)">
            View
          </BaseButton>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, type ComputedRef } from 'vue'
import { projectsApi } from '@/services/projectsApi'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import DataTable from '@/components/common/DataTable.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { formatDate } from '@/utils/formatters'
import { usePagination } from '@/composables/usePagination'
import type { Project, QueryParams } from '@/types'

interface ProjectRowUser {
  full_name: string
  email: string
  initials: string
}

interface ProjectRow extends Project {
  user: ProjectRowUser
}

interface TableColumn {
  key: string
  label: string
  sortable: boolean
}

interface TablePagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

const authStore = useAuthStore()
const router = useRouter()

const isAdmin = computed(() => authStore.user?.role === 'admin')
const showAllProjects = ref(false)
const isLoading = ref(true)

const projects = ref<ProjectRow[]>([])
const currentPage = ref(1)
const pageSize = ref(20)

const totalCount = computed(() => projects.value.length)

const pagination = usePagination({ getTotal: () => totalCount.value, pageSize: pageSize.value })

watch(totalCount, () => {
  if (currentPage.value > pagination.totalPages.value) {
    currentPage.value = pagination.totalPages.value
  }
})

const pagedProjects: ComputedRef<ProjectRow[]> = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return projects.value.slice(start, start + pageSize.value)
})

const tablePagination: ComputedRef<TablePagination> = computed(() => ({
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

const columns: ComputedRef<TableColumn[]> = computed(() => {
  const cols: TableColumn[] = [
    { key: 'name', label: 'Project', sortable: true },
    { key: 'document_count', label: 'Documents', sortable: true },
  ]
  if (isAdmin.value) {
    cols.push({ key: 'user', label: 'User', sortable: true })
  }
  cols.push({ key: 'created_at', label: 'Created', sortable: true })
  return cols
})

function goToProject(project: ProjectRow): void {
  router.push(`/projects/${project.id}`)
}

const loadProjects = async (): Promise<void> => {
  isLoading.value = true
  try {
    const params: QueryParams = isAdmin.value && showAllProjects.value ? { all: true } : {}
    const response = await projectsApi.list(params)
    projects.value = response.data.map((project: Project): ProjectRow => {
      const fullName = project.owner?.full_name || 'N/A'
      return {
        ...project,
        document_count: project.document_count ?? 0,
        user: {
          full_name: fullName,
          email: project.owner?.email || 'N/A',
          initials:
            fullName
              .split(' ')
              .map((n) => n[0])
              .join('') || '?',
        },
      }
    })
    currentPage.value = 1
  } catch (err) {
    console.error('Error loading projects:', err)
  } finally {
    isLoading.value = false
  }
}

// reset to page 1 + reload when admin toggle changes
watch(isAdmin, () => {
  showAllProjects.value = false
  void loadProjects()
})

// reload when "show all projects" toggle changes
watch(showAllProjects, () => {
  void loadProjects()
})

onMounted(async () => {
  await loadProjects()
})
</script>
