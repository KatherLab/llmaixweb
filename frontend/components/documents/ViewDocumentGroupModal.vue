<!-- ViewDocumentGroupModal.vue -->
<template>
  <BaseModal :open="open" size="xl" @close="$emit('close')">
    <template #header>
      <div class="flex items-center gap-3">
        <h3 class="text-xl font-semibold text-content">{{ group.name }}</h3>
        <BaseButton variant="primary" size="sm" @click="$emit('edit', group)">
          Edit Group
        </BaseButton>
      </div>
    </template>

    <div class="p-6">
      <!-- Group Info -->
      <div class="mb-6 space-y-4">
        <div>
          <h4 class="text-sm font-medium text-content-muted">Description</h4>
          <p class="mt-1 text-content">
            {{ group.description || 'No description provided' }}
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <h4 class="text-sm font-medium text-content-muted">Created</h4>
            <p class="mt-1 text-content">{{ formatDate(group.created_at) }}</p>
          </div>
          <div>
            <h4 class="text-sm font-medium text-content-muted">Last Updated</h4>
            <p class="mt-1 text-content">{{ formatDate(group.updated_at) }}</p>
          </div>
        </div>

        <div v-if="group.tags && group.tags.length > 0">
          <h4 class="text-sm font-medium text-content-muted mb-2">Tags</h4>
          <div class="flex flex-wrap gap-2">
            <StatusBadge
              v-for="tag in group.tags"
              :key="tag"
              color="blue"
              class="px-3 py-1 text-sm"
            >
              {{ tag }}
            </StatusBadge>
          </div>
        </div>

        <div v-if="group.preprocessing_config">
          <h4 class="text-sm font-medium text-content-muted">Preprocessing Configuration</h4>
          <p class="mt-1 text-content">{{ group.preprocessing_config.name }}</p>
        </div>

        <div v-if="group.trial_id">
          <h4 class="text-sm font-medium text-content-muted">Source Trial</h4>
          <p class="mt-1 text-content">Trial #{{ group.trial_id }}</p>
        </div>
      </div>

      <!-- Documents List -->
      <div>
        <div class="flex justify-between items-center mb-4">
          <h4 class="font-medium text-content">Documents ({{ docTotal }})</h4>
          <div class="flex items-center gap-2">
            <BaseButton variant="link" tone="blue" class="text-sm" @click="exportDocumentList">
              Export List
            </BaseButton>
            <BaseButton variant="link" tone="blue" class="text-sm" @click="downloadAllDocuments">
              Download All
            </BaseButton>
          </div>
        </div>

        <div :class="t.wrapper">
          <table :class="t.table">
            <thead :class="t.thead">
              <tr>
                <th :class="t.th">Document</th>
                <th :class="t.th">Configuration</th>
                <th :class="t.th">Created</th>
                <th :class="[t.th, 'relative']">
                  <span class="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody :class="t.tbody">
              <tr v-if="docLoading">
                <td colspan="4" class="px-4 py-8 text-center text-content-subtle">
                  Loading documents…
                </td>
              </tr>
              <tr v-else-if="documents.length === 0">
                <td colspan="4" class="px-4 py-8 text-center text-content-subtle">
                  No documents in this set
                </td>
              </tr>
              <tr v-for="doc in documents" :key="doc.id" :class="t.tr">
                <td :class="t.td">
                  <div class="flex items-center">
                    <FileIcon :file-type="doc.original_file?.file_type ?? ''" :size="32" />
                    <div class="ml-3">
                      <p class="text-sm font-medium text-content">
                        {{
                          doc.document_name || doc.original_file?.file_name || `Document #${doc.id}`
                        }}
                      </p>
                      <p
                        v-if="
                          doc.document_name &&
                          doc.original_file?.file_name &&
                          doc.document_name !== doc.original_file?.file_name
                        "
                        class="text-xs text-content-muted"
                      >
                        {{ doc.original_file?.file_name }}
                      </p>
                      <p v-else class="text-xs text-content-muted">
                        {{ formatFileSize(doc.original_file?.file_size) }}
                      </p>
                    </div>
                  </div>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-content">
                  {{ doc.preprocessing_config?.name || 'N/A' }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-content-muted">
                  {{ formatDate(doc.created_at) }}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                  <button class="text-primary hover:text-primary" @click="viewDocument(doc)">
                    View
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Pagination -->
          <PaginationControls
            v-if="docTotalPages > 1"
            v-model="docPage"
            :total-pages="docTotalPages"
            :visible-pages="docVisiblePages"
            :total-items="docTotal"
            :page-size="docPageSize"
          />
        </div>
      </div>

      <!-- Usage Statistics -->
      <div class="mt-6 bg-surface-muted rounded-card p-4">
        <h4 class="font-medium text-content mb-3">Usage Statistics</h4>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <p class="text-sm text-content-muted">Used in Trials</p>
            <p class="text-2xl font-semibold text-content">
              {{ usageStats.trialsCount }}
            </p>
          </div>
          <div>
            <p class="text-sm text-content-muted">Total Extractions</p>
            <p class="text-2xl font-semibold text-content">
              {{ usageStats.extractionsCount }}
            </p>
          </div>
          <div>
            <p class="text-sm text-content-muted">Last Used</p>
            <p class="text-sm font-medium text-content">
              {{ usageStats.lastUsed ? formatDate(usageStats.lastUsed) : 'Never' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Download all documents confirmation -->
    <ConfirmationDialog
      :open="showDownloadAllConfirm"
      title="Download all documents?"
      :message="`This will download all ${docTotal} documents as a ZIP archive.`"
      confirm-text="Download"
      cancel-text="Cancel"
      confirm-variant="primary"
      @confirm="executeDownloadAll"
      @cancel="showDownloadAllConfirm = false"
    />
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { documentsApi } from '@/services/documentsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { useToast } from '@/composables/useToast'
import { formatDate, formatFileSize } from '@/utils/formatters'
import { computeVisiblePages } from '@/composables/usePagination'
import FileIcon from '../common/FileIcon.vue'
import PaginationControls from '../common/PaginationControls.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useFileDownload } from '@/composables/useFileDownload'
import { useTableClasses } from '@/composables/useTableClasses'
import type { DocumentListItem, DocumentSetSummary } from '@/types'

/** DocumentSetSummary as returned by the set list, optionally with `trial_id`. */
interface ViewGroup extends DocumentSetSummary {
  trial_id?: number | null
}

/** Local usage-stats state shape (camelCase keys, as read by the template). */
interface UsageStats {
  trialsCount: number
  extractionsCount: number
  lastUsed: string | null
  [key: string]: unknown
}

interface Props {
  open: boolean
  group: ViewGroup
  projectId: string | number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  edit: [group: ViewGroup]
  'view-document': [doc: DocumentListItem]
}>()

const t = useTableClasses()

const toast = useToast()
const { downloadBlob, downloadFromApi } = useFileDownload()
const usageStats = ref<UsageStats>({
  trialsCount: 0,
  extractionsCount: 0,
  lastUsed: null,
})

// Paginated documents of this set — fetched on demand instead of reading
// `group.documents` (which the set list no longer carries).
// `docTotal` is (re)set from `group.document_count` on each open in the watch
// below; default 0 here because the component stays mounted (enabling the close
// transition) and `group` may be null while closed.
const documents = ref<DocumentListItem[]>([])
const docTotal = ref<number>(0)
const docPage = ref<number>(1)
const docPageSize = ref<number>(25)
const docLoading = ref<boolean>(false)

const docTotalPages = computed<number>(() =>
  docPageSize.value ? Math.ceil(docTotal.value / docPageSize.value) : 1,
)

const docVisiblePages = computed(() => computeVisiblePages(docPage.value, docTotalPages.value))

const fetchDocuments = async (): Promise<void> => {
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

// Fetch documents when the page changes (driven by PaginationControls v-model)
watch(docPage, () => {
  fetchDocuments()
})

// Load usage statistics + first page of documents whenever the modal opens
// (component stays mounted to enable the close transition). Immediate so the
// first open also loads.
watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      docPage.value = 1
      docTotal.value = props.group.document_count ?? 0
      try {
        const response = await documentSetsApi.getStats(props.projectId, props.group.id)
        usageStats.value = response.data as unknown as UsageStats
      } catch (error) {
        console.error('Failed to load usage stats:', error)
      }
      await fetchDocuments()
    }
  },
  { immediate: true },
)

const viewDocument = (doc: DocumentListItem): void => {
  emit('view-document', doc)
}

const exportDocumentList = (): void => {
  const data = documents.value.map((doc) => ({
    id: doc.id,
    filename: doc.original_file?.file_name || `Document #${doc.id}`,
    configuration: doc.preprocessing_config?.name || 'N/A',
    created: formatDate(doc.created_at),
  }))

  const csv = [
    ['ID', 'Filename', 'Configuration', 'Created'],
    ...data.map((row) => [String(row.id), row.filename, row.configuration, row.created]),
  ]
    .map((row) => row.join(','))
    .join('\n')

  downloadBlob(
    csv as unknown as Blob,
    `${props.group.name.replace(/[^a-z0-9]/gi, '_')}_documents.csv`,
    'text/csv',
  )

  toast.success('Document list exported')
}

const showDownloadAllConfirm = ref<boolean>(false)
const downloadAllDocuments = (): void => {
  showDownloadAllConfirm.value = true
}
const executeDownloadAll = async (): Promise<void> => {
  showDownloadAllConfirm.value = false
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
