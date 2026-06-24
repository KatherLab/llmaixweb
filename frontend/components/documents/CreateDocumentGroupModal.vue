<template>
  <teleport to="body">
    <transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md"
        @click="handleBackgroundClick"
      >
        <!-- Modal Content -->
        <div
          class="relative bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-gray-200"
          @click.stop
        >
          <!-- Header -->
          <div
            class="px-6 py-4 border-b bg-gray-50 rounded-t-2xl flex justify-between items-center"
          >
            <h3 class="text-xl font-semibold text-gray-900">
              {{ group ? 'Edit Document Group' : 'Create Document Group' }}
            </h3>
            <button
              class="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close"
              @click="tryClose"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="p-6 overflow-y-auto flex-1">
            <!-- Group Name -->
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Group Name <span class="text-red-500">*</span>
              </label>
              <input
                v-model="formData.name"
                type="text"
                class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Q4 Financial Reports"
              />
            </div>

            <!-- Description -->
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                v-model="formData.description"
                rows="3"
                class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Describe the purpose of this document group..."
              />
            </div>

            <!-- Tags -->
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-1">Tags</label>
              <div class="flex flex-wrap gap-2 mb-2">
                <span
                  v-for="(tag, index) in formData.tags"
                  :key="index"
                  class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                >
                  {{ tag }}
                  <button class="ml-2 text-blue-600 hover:text-blue-800" @click="removeTag(index)">
                    <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="newTag"
                  type="text"
                  class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Add a tag..."
                  @keyup.enter="addTag"
                />
                <button
                  :disabled="!newTag.trim()"
                  class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300"
                  @click="addTag"
                >
                  Add
                </button>
              </div>
            </div>

            <!-- Document Selection -->
            <div class="mb-4">
              <div class="flex justify-between items-center mb-2">
                <label class="block text-sm font-medium text-gray-700">
                  Select Documents <span class="text-red-500">*</span>
                </label>
                <span class="text-sm text-gray-500">
                  {{ selectedCount }} selected
                  <span v-if="loadingExisting" class="text-gray-400">(loading existing…)</span>
                </span>
              </div>

              <!-- Search (server-side) -->
              <div class="flex gap-2 mb-2">
                <input
                  v-model="searchTerm"
                  type="text"
                  placeholder="Search documents..."
                  class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  @input="onSearchInput"
                />
              </div>

              <!-- Document List -->
              <div class="border rounded-md overflow-hidden max-h-64 overflow-y-auto">
                <div v-if="searchLoading" class="p-4 text-center text-gray-500">Searching…</div>
                <div v-else-if="searchResults.length === 0" class="p-4 text-center text-gray-500">
                  No documents found
                </div>
                <div v-else>
                  <div
                    v-for="doc in searchResults"
                    :key="doc.id"
                    :class="[
                      'p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 flex items-center',
                      { 'bg-blue-50': isSelected(doc.id) },
                    ]"
                    @click="toggleDocument(doc.id)"
                  >
                    <input
                      type="checkbox"
                      :checked="isSelected(doc.id)"
                      class="mr-3"
                      readonly
                      @click.stop
                    />
                    <div class="flex-1">
                      <div class="font-medium text-sm">
                        {{ doc.original_file?.file_name || `Document #${doc.id}` }}
                      </div>
                      <div class="text-xs text-gray-500">
                        Config: {{ doc.preprocessing_config?.name || 'N/A' }} • Created:
                        {{ formatDate(doc.created_at) }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Pagination + bulk actions -->
              <div class="flex items-center justify-between gap-2 mt-2">
                <div class="flex gap-2">
                  <button class="text-sm text-blue-600 hover:text-blue-800" @click="selectAll">
                    Select All Visible
                  </button>
                  <span class="text-gray-300">|</span>
                  <button class="text-sm text-blue-600 hover:text-blue-800" @click="clearSelection">
                    Clear Selection
                  </button>
                </div>
                <div v-if="searchTotalPages > 1" class="flex items-center gap-2">
                  <span class="text-xs text-gray-500">
                    {{ searchPage }}/{{ searchTotalPages }}
                  </span>
                  <button
                    class="px-2 py-1 text-sm border rounded disabled:opacity-50"
                    :disabled="searchPage <= 1"
                    @click="prevSearchPage"
                  >
                    Prev
                  </button>
                  <button
                    class="px-2 py-1 text-sm border rounded disabled:opacity-50"
                    :disabled="searchPage >= searchTotalPages"
                    @click="nextSearchPage"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-6 py-4 border-t bg-gray-50 rounded-b-2xl flex justify-end gap-2">
            <button class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md" @click="tryClose">
              Cancel
            </button>
            <button
              :disabled="!isFormValid"
              class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-md disabled:bg-blue-300 disabled:cursor-not-allowed"
              @click="handleSave"
            >
              {{ group ? 'Update' : 'Create' }} Group
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { documentsApi } from '@/services/documentsApi'
import { formatDate } from '@/utils/formatters'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  group: { type: Object, default: null },
  projectId: { type: [String, Number], required: true },
  visible: { type: Boolean, default: true }, // allow parent to show/hide
  selectedDocumentIds: { type: Array, default: null }, // optional pre-selected documents
})

const emit = defineEmits(['close', 'save'])

useScrollLock({ autoLock: true })

const formData = ref({
  name: '',
  description: '',
  tags: [],
})

const initialFormState = ref('')
const newTag = ref('')

// Selection is held as a Set of document ids so it persists across search pages.
const selectedIds = ref(new Set())
const selectedCount = computed(() => selectedIds.value.size)

// Server-side paginated search (replaces loading every document into memory).
const searchTerm = ref('')
const searchResults = ref([])
const searchTotal = ref(0)
const searchPage = ref(1)
const searchPageSize = ref(50)
const searchLoading = ref(false)
const loadingExisting = ref(false)

const searchTotalPages = computed(() =>
  searchPageSize.value ? Math.ceil(searchTotal.value / searchPageSize.value) : 1,
)

// Serialize form for dirty check
function serializeForm(data) {
  return JSON.stringify({
    name: data.name,
    description: data.description,
    tags: [...data.tags].sort(),
    document_ids: [...selectedIds.value].sort(),
  })
}

let searchDebounce = null
const onSearchInput = () => {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    searchPage.value = 1
    fetchSearch()
  }, 300)
}

const fetchSearch = async () => {
  searchLoading.value = true
  try {
    const { data } = await documentsApi.list(props.projectId, {
      search: searchTerm.value || undefined,
      limit: searchPageSize.value,
      offset: (searchPage.value - 1) * searchPageSize.value,
      compute_stats: false,
    })
    searchResults.value = data.items || []
    searchTotal.value = data.total ?? searchResults.value.length
  } catch (error) {
    console.error('Failed to search documents:', error)
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

const prevSearchPage = () => {
  if (searchPage.value > 1) {
    searchPage.value--
    fetchSearch()
  }
}

const nextSearchPage = () => {
  if (searchPage.value < searchTotalPages.value) {
    searchPage.value++
    fetchSearch()
  }
}

// In edit mode, pre-select the documents already in this set. Fetched by
// document_set_id (ids only — list items carry no `text`), accumulated across
// pages so selection survives regardless of set size.
const loadExistingSelection = async () => {
  if (!props.group) return
  loadingExisting.value = true
  try {
    const PAGE = 500
    let offset = 0
    let hasMore = true
    while (hasMore) {
      const { data } = await documentsApi.list(props.projectId, {
        document_set_id: props.group.id,
        limit: PAGE,
        offset,
        compute_stats: false,
      })
      const items = data.items || []
      const next = new Set(selectedIds.value)
      for (const d of items) next.add(d.id)
      selectedIds.value = next
      hasMore = items.length === PAGE
      offset += PAGE
    }
  } catch (error) {
    console.error('Failed to load existing selection:', error)
  } finally {
    loadingExisting.value = false
  }
}

// Setup initial data and save initial state for dirty check
onMounted(async () => {
  if (props.group) {
    formData.value = {
      name: props.group.name,
      description: props.group.description || '',
      tags: [...(props.group.tags || [])],
    }
    await loadExistingSelection()
  } else if (props.selectedDocumentIds && props.selectedDocumentIds.length > 0) {
    const next = new Set(selectedIds.value)
    props.selectedDocumentIds.forEach((id) => next.add(id))
    selectedIds.value = next
  }
  initialFormState.value = serializeForm(formData.value)
  await fetchSearch()
})

// Computed
const isFormValid = computed(() => {
  return formData.value.name.trim() && selectedIds.value.size > 0
})

const isDirty = computed(() => {
  return serializeForm(formData.value) !== initialFormState.value
})

const isSelected = (id) => selectedIds.value.has(id)

// Methods
const addTag = () => {
  const tag = newTag.value.trim()
  if (tag && !formData.value.tags.includes(tag)) {
    formData.value.tags.push(tag)
    newTag.value = ''
  }
}
const removeTag = (index) => {
  formData.value.tags.splice(index, 1)
}
const toggleDocument = (docId) => {
  const next = new Set(selectedIds.value)
  if (next.has(docId)) {
    next.delete(docId)
  } else {
    next.add(docId)
  }
  selectedIds.value = next
}
const selectAll = () => {
  const next = new Set(selectedIds.value)
  searchResults.value.forEach((d) => next.add(d.id))
  selectedIds.value = next
}
const clearSelection = () => {
  selectedIds.value = new Set()
}

// Close handlers with confirmation if dirty
const tryClose = () => {
  if (isDirty.value) {
    if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
      emit('close')
    }
  } else {
    emit('close')
  }
}
const handleBackgroundClick = (e) => {
  if (e.target === e.currentTarget) {
    tryClose()
  }
}
const handleSave = () => {
  emit('save', {
    name: formData.value.name.trim(),
    description: formData.value.description.trim(),
    tags: formData.value.tags,
    document_ids: [...selectedIds.value],
  })
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
