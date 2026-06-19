<!-- DocumentsGroups.vue -->
<template>
  <div class="space-y-4">
    <!-- Actions Bar -->
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-4">
        <button
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          @click="showCreateModal = true"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 4v16m8-8H4"
            />
          </svg>
          Create Group
        </button>

        <div class="relative">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search groups..."
            class="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <svg
            class="absolute left-3 top-2.5 h-5 w-5 text-gray-400 dark:text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <span class="text-sm text-gray-500 dark:text-gray-400">
          {{ totalCount }} group{{ totalCount !== 1 ? 's' : '' }}
        </span>
      </div>
    </div>

    <!-- Document Groups Table -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="large" />
    </div>

    <div
      v-else-if="serverItems.length === 0"
      class="bg-gray-50 dark:bg-slate-800 rounded-lg p-12 text-center"
    >
      <svg
        class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
        />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No document groups</h3>
      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        {{
          searchQuery
            ? 'Try adjusting your search'
            : 'Create your first group to organize documents'
        }}
      </p>
    </div>

    <div
      v-else
      class="bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
    >
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-slate-800">
            <tr>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Group Name
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Documents
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Configuration
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Tags
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Type
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Created
              </th>
              <th class="relative px-6 py-3">
                <span class="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-slate-900 divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="group in serverItems"
              :key="group.id"
              class="hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
            >
              <td class="px-6 py-4">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900 dark:text-white">{{
                      group.name
                    }}</span>
                    <span
                      v-if="group.is_auto_generated"
                      class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                      title="Auto-generated during preprocessing"
                    >
                      Auto
                    </span>
                  </div>
                  <div
                    v-if="group.description"
                    class="text-xs text-gray-500 dark:text-gray-400 truncate max-w-md"
                  >
                    {{ group.description }}
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span class="text-sm text-gray-900 dark:text-white">{{
                  group.document_count ?? 0
                }}</span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  v-if="group.preprocessing_config"
                  class="text-sm text-gray-900 dark:text-white"
                >
                  {{ group.preprocessing_config.name }}
                </span>
                <span v-else class="text-sm text-gray-500 dark:text-gray-400">Mixed</span>
              </td>
              <td class="px-6 py-4">
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="tag in (group.tags || []).slice(0, 5)"
                    :key="tag"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
                  >
                    {{ tag }}
                  </span>
                  <span
                    v-if="(group.tags || []).length > 5"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                  >
                    +{{ group.tags.length - 5 }}
                  </span>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                    group.is_auto_generated
                      ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
                      : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
                  ]"
                >
                  {{ group.is_auto_generated ? 'Auto-generated' : 'Manual' }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {{ formatDate(group.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div class="flex items-center justify-end space-x-2">
                  <button
                    class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    title="View"
                    @click="viewGroup(group)"
                  >
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="!group.is_auto_generated"
                    class="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300"
                    title="Edit"
                    @click="editGroup(group)"
                  >
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <button
                    class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                    :title="group.trials_count > 0 ? 'Cannot delete - used by trial' : 'Delete'"
                    :disabled="group.trials_count > 0"
                    @click="deleteGroup(group)"
                  >
                    <svg
                      class="h-5 w-5"
                      :class="group.trials_count > 0 ? 'opacity-50 cursor-not-allowed' : ''"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pagination -->
    <div
      v-if="totalPages > 1"
      class="bg-white dark:bg-slate-900 px-4 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 sm:px-6"
    >
      <div class="flex-1 flex justify-between sm:hidden">
        <button
          :disabled="currentPage === 1"
          class="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
          @click="currentPage--"
        >
          Previous
        </button>
        <button
          :disabled="currentPage === totalPages"
          class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
          @click="currentPage++"
        >
          Next
        </button>
      </div>
      <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div>
          <p class="text-sm text-gray-700 dark:text-gray-300">
            Showing
            <span class="font-medium">{{ (currentPage - 1) * itemsPerPage + 1 }}</span>
            to
            <span class="font-medium">{{ Math.min(currentPage * itemsPerPage, totalCount) }}</span>
            of
            <span class="font-medium">{{ totalCount }}</span>
            results
          </p>
        </div>
        <div>
          <nav
            class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
            aria-label="Pagination"
          >
            <button
              :disabled="currentPage === 1"
              class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-slate-900 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="currentPage = 1"
            >
              <span class="sr-only">First</span>
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                />
              </svg>
            </button>
            <button
              v-for="page in visiblePages"
              :key="page"
              :class="[
                'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
                page === currentPage
                  ? 'z-10 bg-blue-50 dark:bg-blue-900 border-blue-500 dark:border-blue-400 text-blue-600 dark:text-blue-400'
                  : 'bg-white dark:bg-slate-900 border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800',
              ]"
              @click="currentPage = page"
            >
              {{ page }}
            </button>
            <button
              :disabled="currentPage === totalPages"
              class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-slate-900 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="currentPage = totalPages"
            >
              <span class="sr-only">Last</span>
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 5l7 7-7 7M5 5l7 7-7 7"
                />
              </svg>
            </button>
          </nav>
        </div>
      </div>
    </div>

    <!-- Create/Edit Group Modal -->
    <CreateDocumentGroupModal
      v-if="showCreateModal || editingGroup"
      :group="editingGroup"
      :project-id="projectId"
      @close="closeModal"
      @save="handleSaveGroup"
    />

    <!-- View Group Modal -->
    <ViewDocumentGroupModal
      v-if="viewingGroup"
      :group="viewingGroup"
      :project-id="projectId"
      @close="viewingGroup = null"
      @edit="editGroup"
      @view-document="viewDocumentFromGroup"
    />

    <!-- Delete Group Confirmation Modal -->
    <Teleport to="body">
      <transition name="fade">
        <div
          v-if="showDeleteModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md"
          @click.self="showDeleteModal = false"
        >
          <div
            class="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-gray-200"
            @click.stop
          >
            <div class="px-6 py-4 border-b bg-red-50 rounded-t-2xl">
              <div class="flex items-center gap-3">
                <svg
                  class="h-6 w-6 text-red-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <h3 class="text-lg font-semibold text-red-900">Delete Document Group</h3>
              </div>
            </div>

            <div class="p-6 space-y-4">
              <p class="text-gray-700">
                Are you sure you want to delete "<strong>{{ groupToDelete?.name }}</strong
                >"?
              </p>

              <div
                v-if="groupToDelete?.document_count > 0"
                class="bg-yellow-50 border border-yellow-200 rounded-lg p-3"
              >
                <p class="text-sm text-yellow-800">
                  This group contains
                  <strong>{{ groupToDelete.document_count }}</strong> document(s).
                </p>
              </div>

              <div v-if="groupToDelete?.document_count > 0" class="flex items-center">
                <input
                  v-model="deleteDocumentsToo"
                  type="checkbox"
                  class="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                />
                <label class="ml-2 text-sm text-gray-700">
                  Also delete all documents in this group (if not referenced elsewhere)
                </label>
              </div>

              <div class="flex items-center">
                <input
                  v-model="confirmDeleteGroup"
                  type="checkbox"
                  class="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                />
                <label class="ml-2 text-sm text-gray-700">
                  I understand that this action cannot be undone
                </label>
              </div>
            </div>

            <div class="px-6 py-4 bg-gray-50 border-t rounded-b-2xl flex justify-end gap-3">
              <button
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                @click="showDeleteModal = false"
              >
                Cancel
              </button>
              <button
                :disabled="!canDeleteGroup"
                class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-300 disabled:cursor-not-allowed"
                @click="confirmDeleteGroupAction"
              >
                <span v-if="isDeleting" class="flex items-center gap-2">
                  <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    />
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Deleting...
                </span>
                <span v-else>Delete</span>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/services/api'
import { useToast } from 'vue-toastification'
import { formatDate } from '@/utils/formatters'
import CreateDocumentGroupModal from './CreateDocumentGroupModal.vue'
import ViewDocumentGroupModal from './ViewDocumentGroupModal.vue'
import LoadingSpinner from '../common/LoadingSpinner.vue'

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
  documentSets: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['refresh', 'view-document'])

const toast = useToast()

// State
const searchQuery = ref('')
const showCreateModal = ref(false)
const editingGroup = ref(null)
const viewingGroup = ref(null)
const isLoading = ref(true)
const serverItems = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const itemsPerPage = ref(20)

// Delete modal state
const showDeleteModal = ref(false)
const groupToDelete = ref(null)
const deleteDocumentsToo = ref(false)
const confirmDeleteGroup = ref(false)
const isDeleting = ref(false)

// Server-side pagination
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / itemsPerPage.value)))

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 3) {
      for (let i = 1; i <= 5; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 2) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) {
        pages.push(i)
      }
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    }
  }

  return pages.filter((p) => p === '...' || (p >= 1 && p <= total))
})

const canDeleteGroup = computed(() => {
  return confirmDeleteGroup.value && !isDeleting.value
})

// Fetch document sets with server-side pagination + search
const fetchDocumentSets = async () => {
  isLoading.value = true
  try {
    const { data } = await api.get(`/project/${props.projectId}/document-set`, {
      params: {
        include_auto_generated: true,
        search: searchQuery.value || undefined,
        limit: itemsPerPage.value,
        offset: (currentPage.value - 1) * itemsPerPage.value,
      },
    })

    serverItems.value = data.items || []
    totalCount.value = data.total ?? serverItems.value.length

    // Safety: if we're on a page that no longer exists, pull back to the last page
    if (
      serverItems.value.length === 0 &&
      totalCount.value > 0 &&
      currentPage.value > totalPages.value
    ) {
      currentPage.value = totalPages.value
      await fetchDocumentSets()
    }
  } catch (error) {
    toast.error('Failed to load document groups')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// Methods
const editGroup = (group) => {
  editingGroup.value = group
  showCreateModal.value = false
}

const viewGroup = (group) => {
  viewingGroup.value = group
}

const viewDocumentFromGroup = (doc) => {
  emit('view-document', doc)
}

const deleteGroup = (group) => {
  if (group.trials_count > 0) {
    toast.warning('Cannot delete group - it is used by a trial')
    return
  }

  groupToDelete.value = group
  deleteDocumentsToo.value = false
  confirmDeleteGroup.value = false
  showDeleteModal.value = true
}

const confirmDeleteGroupAction = async () => {
  if (!canDeleteGroup.value || !groupToDelete.value) return

  isDeleting.value = true

  try {
    // Use backend cascade delete with query parameter
    const params = deleteDocumentsToo.value ? { delete_documents: true } : undefined
    const response = await api.delete(
      `/project/${props.projectId}/document-set/${groupToDelete.value.id}`,
      { params },
    )

    // Parse response - handle both 200 OK with body and 204 No Content
    const deletedDocs = response.data?.deleted_document_ids || []

    if (deleteDocumentsToo.value) {
      if (deletedDocs.length > 0) {
        toast.success(`Group and ${deletedDocs.length} document(s) deleted successfully`)
      } else {
        // No documents were deleted - they must all be referenced elsewhere
        toast.warning('Group deleted, but documents could not be deleted (referenced elsewhere).')
      }
    } else {
      toast.success('Document group deleted successfully')
    }

    showDeleteModal.value = false
    groupToDelete.value = null
    deleteDocumentsToo.value = false
    confirmDeleteGroup.value = false
    emit('refresh')
    currentPage.value = 1
    fetchDocumentSets()
  } catch (error) {
    toast.error(error?.response?.data?.detail || 'Failed to delete document group')
    console.error(error)
  } finally {
    isDeleting.value = false
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingGroup.value = null
}

const handleSaveGroup = async (groupData) => {
  try {
    if (editingGroup.value) {
      await api.patch(
        `/project/${props.projectId}/document-set/${editingGroup.value.id}`,
        groupData,
      )
      toast.success('Document group updated successfully')
    } else {
      await api.post(`/project/${props.projectId}/document-set`, groupData)
      toast.success('Document group created successfully')
    }
    closeModal()
    emit('refresh')
    currentPage.value = 1
    fetchDocumentSets()
  } catch (error) {
    toast.error('Failed to save document group')
    console.error(error)
  }
}

// Watch for search query changes (debounced → server-side search)
let searchDebounce = null
watch(searchQuery, () => {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    currentPage.value = 1
    fetchDocumentSets()
  }, 300)
})

// Watch for page changes
watch([currentPage, itemsPerPage], fetchDocumentSets)

// Lifecycle
onMounted(() => {
  fetchDocumentSets()
})
</script>
