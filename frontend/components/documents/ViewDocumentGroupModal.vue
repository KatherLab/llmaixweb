<!-- ViewDocumentGroupModal.vue -->
<!--
  Document group viewer with a side document list — mirrors the Trial Results
  panel: a left rail of the group's documents + the existing DocumentViewer as
  the center. Click a doc in the rail (or use ←/→) to load it; prev/next
  crosses pages just like trial results.
-->
<template>
  <SlideOver
    :open="open"
    aria-label="Document group"
    max-width="max-w-[95rem]"
    body-class="!p-0 overflow-hidden"
    @close="$emit('close')"
  >
    <template #header>
      <div class="flex items-center justify-between gap-4 flex-1 min-w-0 pr-8">
        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <h3 class="text-base font-semibold text-content truncate">{{ group.name }}</h3>
            <span
              class="text-[11px] text-content-subtle bg-surface px-2 py-0.5 rounded-full border border-default"
            >
              {{ docTotal }} document{{ docTotal === 1 ? '' : 's' }}
            </span>
          </div>
          <p v-if="group.description" class="text-xs text-content-subtle mt-0.5 truncate">
            {{ group.description }}
          </p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <BaseButton variant="link" tone="blue" size="sm" @click="exportDocumentList">
            <Download class="h-4 w-4" />
            Export
          </BaseButton>
          <BaseButton variant="link" tone="blue" size="sm" @click="downloadAllDocuments">
            <Package class="h-4 w-4" />
            Download all
          </BaseButton>
          <BaseButton variant="secondary" size="sm" @click="$emit('edit', group)">
            <SquarePen class="h-4 w-4" />
            Edit
          </BaseButton>
        </div>
      </div>
    </template>

    <!-- Main 2-pane layout: doc list + viewer (always rendered while open) -->
    <div class="flex h-full min-h-0">
      <!-- Left rail: document list -->
      <aside
        :class="[
          'flex flex-col border-r border-default bg-surface-muted/40 shrink-0',
          leftRailOpen ? 'w-64' : 'w-0 -ml-px overflow-hidden',
        ]"
      >
        <div v-show="leftRailOpen" class="flex flex-col h-full min-w-0">
          <!-- Search -->
          <div class="p-3 border-b border-default shrink-0">
            <SearchInput
              v-model="search"
              placeholder="Search documents…"
              @input="debouncedFetchDocuments"
            />
          </div>

          <!-- Document list -->
          <div class="flex-1 min-h-0 overflow-y-auto p-2 space-y-0.5">
            <button
              v-for="(d, i) in documents"
              :key="d.id"
              type="button"
              :class="[
                'w-full text-left px-3 py-2 rounded-card border-l-2 transition-colors',
                d.id === activeDocId
                  ? 'bg-primary-soft border-primary'
                  : 'border-transparent hover:bg-surface',
              ]"
              @click="selectIndex(i)"
            >
              <div class="flex items-center gap-2 min-w-0">
                <FileIcon :file-type="d.original_file?.file_type ?? ''" :size="16" />
                <span class="text-sm text-content truncate flex-1">{{
                  d.document_name || d.original_file?.file_name || `Document #${d.id}`
                }}</span>
              </div>
              <div class="flex items-center gap-2 mt-0.5 pl-6">
                <span class="text-[10px] uppercase tracking-wide text-content-subtle truncate">
                  {{ d.preprocessing_config?.name || 'N/A' }}
                </span>
              </div>
            </button>
            <div v-if="docLoading" class="flex justify-center py-4">
              <LoadingSpinner size="small" inline label="" />
            </div>
            <div
              v-else-if="documents.length === 0"
              class="flex flex-col items-center justify-center py-8 px-3 text-center"
            >
              <p class="text-xs text-content-subtle">No documents match your search.</p>
              <button
                type="button"
                class="mt-2 text-xs font-medium text-primary hover:underline"
                @click="resetFilters"
              >
                Reset filters
              </button>
            </div>
          </div>

          <!-- Compact pagination -->
          <div class="p-2 border-t border-default flex items-center justify-between gap-1 shrink-0">
            <BaseButton
              variant="ghost"
              size="sm"
              :disabled="docPage <= 1"
              @click="handlePageChange(docPage - 1)"
            >
              <ChevronLeft class="h-4 w-4" />
            </BaseButton>
            <span class="text-xs text-content-muted tabular-nums">
              {{ docPage }} / {{ docTotalPages }}
            </span>
            <BaseButton
              variant="ghost"
              size="sm"
              :disabled="docPage >= docTotalPages"
              @click="handlePageChange(docPage + 1)"
            >
              <ChevronRight class="h-4 w-4" />
            </BaseButton>
          </div>
        </div>
      </aside>

      <!-- Center: main viewer -->
      <div class="flex-1 min-w-0 flex flex-col">
        <!-- Rail toggle -->
        <div
          class="flex items-center justify-between px-2 py-1 border-b border-default bg-surface shrink-0"
        >
          <BaseButton
            variant="ghost"
            size="sm"
            :title="leftRailOpen ? 'Hide document list' : 'Show document list'"
            @click="leftRailOpen = !leftRailOpen"
          >
            <PanelLeft class="h-4 w-4" />
          </BaseButton>
          <p class="text-xs text-content-subtle pr-2">
            <kbd class="px-1 py-0.5 bg-surface-sunken rounded">←</kbd> /
            <kbd class="px-1 py-0.5 bg-surface-sunken rounded">→</kbd> to move between documents
          </p>
        </div>

        <div class="flex-1 min-h-0">
          <DocumentViewerBody
            v-if="activeDoc"
            :document="activeDoc"
            :project-id="projectId"
            :open="true"
            @update-document="onUpdateDocument"
            @restored="onDocumentRestored"
          />
          <div
            v-else-if="docLoading"
            class="flex flex-col items-center justify-center h-full py-16"
          >
            <LoadingSpinner size="medium" inline label="" />
            <span class="mt-2 text-content-muted">Loading documents…</span>
          </div>
          <!-- No active doc and not loading: quiet placeholder. The rail stays
               visible with its own empty-list/reset UI, so we don't repeat a
               reset CTA here. -->
          <div
            v-else
            class="flex flex-col items-center justify-center h-full py-16 text-content-subtle"
          >
            <FileText class="h-10 w-10 mb-2 opacity-40" />
            <p class="text-sm">
              {{
                hasActiveFilters ? 'No documents match your search.' : 'Select a document to view.'
              }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Group details (collapsible) — metadata + usage stats, shown when rail is hidden or via a toggle -->
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
  </SlideOver>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { debounce } from 'perfect-debounce'
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Package,
  PanelLeft,
  SquarePen,
} from '@lucide/vue'
import { documentsApi } from '@/services/documentsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { useToast } from '@/composables/useToast'
import { formatDate } from '@/utils/formatters'
import FileIcon from '../common/FileIcon.vue'
import LoadingSpinner from '../common/LoadingSpinner.vue'
import SearchInput from '../common/SearchInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import SlideOver from '@/components/common/SlideOver.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import DocumentViewerBody from './DocumentViewerBody.vue'
import { useFileDownload } from '@/composables/useFileDownload'
import type { DocumentListItem, DocumentSetSummary } from '@/types'

/** DocumentSetSummary as returned by the set list, optionally with `trial_id`. */
interface ViewGroup extends DocumentSetSummary {
  trial_id?: number | null
}

interface Props {
  open: boolean
  group: ViewGroup
  projectId: string | number
}

const props = defineProps<Props>()

defineEmits<{
  close: []
  edit: [group: ViewGroup]
}>()

const toast = useToast()
const { downloadBlob, downloadFromApi } = useFileDownload()

// Paginated documents of this set — fetched on demand instead of reading
// `group.documents` (which the set list no longer carries).
const documents = ref<DocumentListItem[]>([])
const docTotal = ref<number>(0)
const docPage = ref<number>(1)
const docPageSize = ref<number>(25)
const docLoading = ref<boolean>(false)
const search = ref('')

// Active document in the rail.
const activeDocId = ref<number | null>(null)
const leftRailOpen = ref(true)

const docTotalPages = computed<number>(() =>
  docPageSize.value ? Math.ceil(docTotal.value / docPageSize.value) : 1,
)

const activeDoc = computed<DocumentListItem | null>(
  () => documents.value.find((d) => d.id === activeDocId.value) ?? null,
)

const activeIndex = computed(() => documents.value.findIndex((d) => d.id === activeDocId.value))

const hasPrev = computed(() => !(docPage.value === 1 && activeIndex.value <= 0))
const hasNext = computed(
  () => !(docPage.value >= docTotalPages.value && activeIndex.value >= documents.value.length - 1),
)

const fetchDocuments = async (): Promise<void> => {
  docLoading.value = true
  try {
    const { data } = await documentsApi.list(props.projectId, {
      document_set_id: props.group.id,
      limit: docPageSize.value,
      offset: (docPage.value - 1) * docPageSize.value,
      compute_stats: false,
      // Oldest-first so a row-by-row set reads in its natural ID001→ID150 order
      // (and paginates deterministically — see the endpoint's sort tie-breaker).
      sort: 'created_asc',
      ...(search.value ? { search: search.value } : {}),
    })
    documents.value = data.items || []
    docTotal.value = data.total ?? documents.value.length
    // Keep the selection valid: pick the first doc of the new page if the
    // active one is no longer present.
    if (!documents.value.some((d) => d.id === activeDocId.value)) {
      activeDocId.value = documents.value[0]?.id ?? null
    }
  } catch (error) {
    console.error('Failed to load set documents:', error)
    documents.value = []
  } finally {
    docLoading.value = false
  }
}

// A version was restored to a new latest (no reprocessing). Refresh the set's
// documents so the rail reflects the new latest instead of the archived one.
async function onDocumentRestored(newDocId: number): Promise<void> {
  activeDocId.value = newDocId
  await fetchDocuments()
}

const debouncedFetchDocuments = debounce(() => {
  docPage.value = 1
  activeDocId.value = null
  fetchDocuments()
}, 300)

// Whether a filter is active — drives the "Reset filters" CTA so users are
// never stranded with an empty list and no way back.
const hasActiveFilters = computed(() => !!search.value)

function resetFilters(): void {
  search.value = ''
  docPage.value = 1
  activeDocId.value = null
  fetchDocuments()
}

async function handlePageChange(page: number): Promise<void> {
  if (page < 1 || page > docTotalPages.value || page === docPage.value) return
  docPage.value = page
  await fetchDocuments()
}

function selectIndex(i: number): void {
  const doc = documents.value[i]
  if (doc) activeDocId.value = doc.id
}

async function goPrev(): Promise<void> {
  if (!hasPrev.value) return
  if (activeIndex.value > 0) {
    activeDocId.value = documents.value[activeIndex.value - 1]!.id
    return
  }
  // Cross to previous page
  if (docPage.value > 1) {
    docPage.value--
    await fetchDocuments()
    activeDocId.value = documents.value[documents.value.length - 1]?.id ?? null
  }
}

async function goNext(): Promise<void> {
  if (!hasNext.value) return
  if (activeIndex.value < documents.value.length - 1) {
    activeDocId.value = documents.value[activeIndex.value + 1]!.id
    return
  }
  // Cross to next page
  if (docPage.value < docTotalPages.value) {
    docPage.value++
    await fetchDocuments()
    activeDocId.value = documents.value[0]?.id ?? null
  }
}

function onUpdateDocument(version: DocumentListItem): void {
  const idx = documents.value.findIndex((d) => d.id === version.id)
  if (idx >= 0) documents.value[idx] = version
}

// ←/→ keyboard navigation between documents. The body viewer doesn't own
// prev/next (no header nav in the embedded context), so the modal drives it
// directly — mirroring TrialResults' listener. Ignored while focus is in an
// editable field so users can type in search.
function onKeydown(e: KeyboardEvent): void {
  if (!props.open) return
  const target = e.target as HTMLElement | null
  const tag = target?.tagName
  const editable =
    tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable
  if (editable) return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    goPrev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    goNext()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
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
      search.value = ''
      activeDocId.value = null
      leftRailOpen.value = true
      await fetchDocuments()
      // Auto-select the first document.
      if (activeDocId.value === null) activeDocId.value = documents.value[0]?.id ?? null
    }
  },
  { immediate: true },
)

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
