<!-- ViewDocumentGroupModal.vue -->
<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md"
        @click="$emit('close')"
      >
        <div
          class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col border border-gray-200"
          @click.stop
        >
          <div
            class="px-6 py-4 border-b bg-gray-50 rounded-t-2xl flex justify-between items-center"
          >
            <h3 class="text-xl font-semibold text-gray-900">{{ group.name }}</h3>
            <div class="flex items-center gap-2">
              <button
                class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
                @click="$emit('edit', group)"
              >
                Edit Group
              </button>
              <button
                class="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Close"
                @click="$emit('close')"
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
          </div>

          <div class="p-6 overflow-y-auto flex-1">
            <!-- Group Info -->
            <div class="mb-6 space-y-4">
              <div>
                <h4 class="text-sm font-medium text-gray-700">Description</h4>
                <p class="mt-1 text-gray-900">
                  {{ group.description || 'No description provided' }}
                </p>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <h4 class="text-sm font-medium text-gray-700">Created</h4>
                  <p class="mt-1 text-gray-900">{{ formatDate(group.created_at) }}</p>
                </div>
                <div>
                  <h4 class="text-sm font-medium text-gray-700">Last Updated</h4>
                  <p class="mt-1 text-gray-900">{{ formatDate(group.updated_at) }}</p>
                </div>
              </div>

              <div v-if="group.tags && group.tags.length > 0">
                <h4 class="text-sm font-medium text-gray-700 mb-2">Tags</h4>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="tag in group.tags"
                    :key="tag"
                    class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>

              <div v-if="group.preprocessing_config">
                <h4 class="text-sm font-medium text-gray-700">Preprocessing Configuration</h4>
                <p class="mt-1 text-gray-900">{{ group.preprocessing_config.name }}</p>
              </div>

              <div v-if="group.trial_id">
                <h4 class="text-sm font-medium text-gray-700">Source Trial</h4>
                <p class="mt-1 text-gray-900">Trial #{{ group.trial_id }}</p>
              </div>
            </div>

            <!-- Documents List -->
            <div>
              <div class="flex justify-between items-center mb-4">
                <h4 class="font-medium text-gray-900">Documents ({{ docTotal }})</h4>
                <div class="flex items-center gap-2">
                  <button
                    class="text-sm text-blue-600 hover:text-blue-800"
                    @click="exportDocumentList"
                  >
                    Export List
                  </button>
                  <button
                    class="text-sm text-blue-600 hover:text-blue-800"
                    @click="downloadAllDocuments"
                  >
                    Download All
                  </button>
                </div>
              </div>

              <div class="border rounded-lg overflow-hidden">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th
                        class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        Document
                      </th>
                      <th
                        class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        Configuration
                      </th>
                      <th
                        class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                      >
                        Created
                      </th>
                      <th class="relative px-6 py-3">
                        <span class="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-if="docLoading">
                      <td colspan="4" class="px-6 py-8 text-center text-gray-400">
                        Loading documents…
                      </td>
                    </tr>
                    <tr v-else-if="documents.length === 0">
                      <td colspan="4" class="px-6 py-8 text-center text-gray-400">
                        No documents in this set
                      </td>
                    </tr>
                    <tr v-for="doc in documents" :key="doc.id" class="hover:bg-gray-50">
                      <td class="px-6 py-4">
                        <div class="flex items-center">
                          <FileIcon :file-type="doc.original_file?.file_type" :size="32" />
                          <div class="ml-3">
                            <p class="text-sm font-medium text-gray-900">
                              {{
                                doc.document_name ||
                                doc.original_file?.file_name ||
                                `Document #${doc.id}`
                              }}
                            </p>
                            <p
                              v-if="
                                doc.document_name &&
                                doc.original_file?.file_name &&
                                doc.document_name !== doc.original_file?.file_name
                              "
                              class="text-xs text-gray-500"
                            >
                              {{ doc.original_file?.file_name }}
                            </p>
                            <p v-else class="text-xs text-gray-500">
                              {{ formatFileSize(doc.original_file?.file_size) }}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {{ doc.preprocessing_config?.name || 'N/A' }}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {{ formatDate(doc.created_at) }}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          class="text-blue-600 hover:text-blue-900"
                          @click="viewDocument(doc)"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <!-- Pagination -->
                <div
                  v-if="docTotalPages > 1"
                  class="bg-gray-50 px-4 py-2 flex items-center justify-between border-t"
                >
                  <span class="text-xs text-gray-500">
                    Page {{ docPage }} of {{ docTotalPages }} ({{ docTotal }} documents)
                  </span>
                  <div class="flex gap-2">
                    <button
                      class="px-3 py-1 text-sm border rounded disabled:opacity-50"
                      :disabled="docPage <= 1"
                      @click="prevDocPage"
                    >
                      Previous
                    </button>
                    <button
                      class="px-3 py-1 text-sm border rounded disabled:opacity-50"
                      :disabled="docPage >= docTotalPages"
                      @click="nextDocPage"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Usage Statistics -->
            <div class="mt-6 bg-gray-50 rounded-lg p-4">
              <h4 class="font-medium text-gray-900 mb-3">Usage Statistics</h4>
              <div class="grid grid-cols-3 gap-4">
                <div>
                  <p class="text-sm text-gray-600">Used in Trials</p>
                  <p class="text-2xl font-semibold text-gray-900">{{ usageStats.trialsCount }}</p>
                </div>
                <div>
                  <p class="text-sm text-gray-600">Total Extractions</p>
                  <p class="text-2xl font-semibold text-gray-900">
                    {{ usageStats.extractionsCount }}
                  </p>
                </div>
                <div>
                  <p class="text-sm text-gray-600">Last Used</p>
                  <p class="text-sm font-medium text-gray-900">
                    {{ usageStats.lastUsed ? formatDate(usageStats.lastUsed) : 'Never' }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { documentsApi } from '@/services/documentsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { useToast } from 'vue-toastification'
import { formatDate, formatFileSize } from '@/utils/formatters'
import FileIcon from '../common/FileIcon.vue'
import { useScrollLock } from '@/composables/useScrollLock'
import { useFileDownload } from '@/composables/useFileDownload'

useScrollLock({ autoLock: true })

const props = defineProps({
  group: {
    type: Object,
    required: true,
  },
  projectId: {
    type: [String, Number],
    required: true,
  },
})

const emit = defineEmits(['close', 'edit', 'view-document'])

const toast = useToast()
const { downloadBlob, downloadFromApi } = useFileDownload()
const usageStats = ref({
  trialsCount: 0,
  extractionsCount: 0,
  lastUsed: null,
})

// Paginated documents of this set — fetched on demand instead of reading
// `group.documents` (which the set list no longer carries).
const documents = ref([])
const docTotal = ref(props.group.document_count ?? 0)
const docPage = ref(1)
const docPageSize = ref(25)
const docLoading = ref(false)

const docTotalPages = computed(() =>
  docPageSize.value ? Math.ceil(docTotal.value / docPageSize.value) : 1,
)

const fetchDocuments = async () => {
  docLoading.value = true
  try {
    const { data } = await documentsApi.list(props.projectId, {
      document_set_id: props.group.id,
      limit: docPageSize.value,
      offset: (docPage.value - 1) * docPageSize.value,
      compute_stats: false,
    })
    documents.value = data.items || []
    docTotal.value = data.total ?? documents.value.length
  } catch (error) {
    console.error('Failed to load set documents:', error)
    documents.value = []
  } finally {
    docLoading.value = false
  }
}

const prevDocPage = () => {
  if (docPage.value > 1) {
    docPage.value--
    fetchDocuments()
  }
}

const nextDocPage = () => {
  if (docPage.value < docTotalPages.value) {
    docPage.value++
    fetchDocuments()
  }
}

// Load usage statistics + first page of documents
onMounted(async () => {
  try {
    const response = await documentSetsApi.getStats(props.projectId, props.group.id)
    usageStats.value = response.data
  } catch (error) {
    console.error('Failed to load usage stats:', error)
  }
  await fetchDocuments()
})

const viewDocument = (doc) => {
  emit('view-document', doc)
}

const exportDocumentList = () => {
  const data = documents.value.map((doc) => ({
    id: doc.id,
    filename: doc.original_file?.file_name || `Document #${doc.id}`,
    configuration: doc.preprocessing_config?.name || 'N/A',
    created: formatDate(doc.created_at),
  }))

  const csv = [
    ['ID', 'Filename', 'Configuration', 'Created'],
    ...data.map((row) => [row.id, row.filename, row.configuration, row.created]),
  ]
    .map((row) => row.join(','))
    .join('\n')

  downloadBlob(csv, `${props.group.name.replace(/[^a-z0-9]/gi, '_')}_documents.csv`, 'text/csv')

  toast.success('Document list exported')
}

const downloadAllDocuments = async () => {
  if (!confirm(`Download all ${docTotal.value} documents?`)) {
    return
  }

  try {
    await downloadFromApi(
      () => documentSetsApi.downloadAll(props.projectId, props.group.id),
      `${props.group.name.replace(/[^a-z0-9]/gi, '_')}_documents.zip`,
    )

    toast.success('Download started')
  } catch (error) {
    toast.error('Failed to download documents')
    console.error(error)
  }
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
