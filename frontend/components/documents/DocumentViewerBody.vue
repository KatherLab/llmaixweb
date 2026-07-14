<!--
  Body-only document viewer (no SlideOver chrome).

  Renders the SplitPane (original file | extracted text), the version-history
  sidebar, and the document info sidebar — i.e. everything except the header
  bar + nav. Designed to be embedded inline by hosts that own their own chrome:
  - DocumentViewer.vue wraps it in a SlideOver (standalone use from the documents table).
  - ViewDocumentGroupModal.vue embeds it as the center pane next to its doc rail.

  Mirrors TrialResultViewer: a plain <div> that fills its parent's height.
-->
<template>
  <div class="flex flex-1 overflow-hidden relative h-full min-h-0">
    <div class="flex-1 overflow-hidden">
      <SplitPane
        v-if="hasDisplayableOriginalFile"
        left-label="Original"
        right-label="Text"
        :mode="splitMode"
        :collapsible="false"
      >
        <template #left>
          <DocumentFilePreview
            v-if="originalFileType === 'pdf' && originalPdfUrl"
            view-mode="pdf"
            :original-pdf-url="originalPdfUrl"
          />
          <DocumentFilePreview
            v-else-if="originalFileType === 'image' && originalImageUrl"
            view-mode="image"
            :original-image-url="originalImageUrl"
          />
          <div
            v-else
            class="flex items-center justify-center h-full text-sm text-content-subtle italic"
          >
            No original file available
          </div>
        </template>
        <template #right>
          <DocumentTextView :text-loading="textLoading" :safe-markdown="safeMarkdown" />
        </template>
      </SplitPane>
      <DocumentTextView v-else :text-loading="textLoading" :safe-markdown="safeMarkdown" />
    </div>

    <!-- Version History Sidebar (overlays on top of Document Info when shown) -->
    <VersionHistorySidebar
      v-if="showVersionHistory"
      :loading-versions="loadingVersions"
      :versions="versions"
      :selected-version="selectedVersion"
      :version-count="versionCount"
      @close="$emit('update:showVersionHistory', false)"
      @select-version="selectVersion"
    />

    <!-- Sidebar -->
    <DocumentInfoSidebar
      :document="document"
      :selected-version="selectedVersion"
      :full-text="fullText"
      @restore-version="restoreVersion"
      @reprocess="(payload) => emit('reprocess', payload)"
    />

    <!-- Restore archived version confirmation -->
    <ConfirmationDialog
      :open="showRestoreConfirm"
      title="Restore archived version?"
      message="This makes the selected version the latest again. Nothing is reprocessed."
      confirm-text="Restore"
      cancel-text="Cancel"
      confirm-variant="primary"
      @confirm="confirmRestore"
      @cancel="showRestoreConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useFileDownload } from '@/composables/useFileDownload'
import { extractErrorMessage } from '@/utils/errors'
import SplitPane from '@/components/common/SplitPane.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import DocumentFilePreview from './DocumentFilePreview.vue'
import DocumentTextView from './DocumentTextView.vue'
import VersionHistorySidebar from './VersionHistorySidebar.vue'
import DocumentInfoSidebar from './DocumentInfoSidebar.vue'
import type { DocumentListItem, DocumentFilter } from '@/types'

interface Props {
  document: DocumentListItem
  projectId: string | number
  // Drives load-on-open + object-URL revocation on close. Hosts that keep the
  // body mounted while open (e.g. the group modal) pass `true`.
  open?: boolean
  // Version-history sidebar visibility — owned by the host header toggle.
  showVersionHistory?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  open: true,
  showVersionHistory: false,
})

const emit = defineEmits<{
  reprocess: [payload: Partial<DocumentListItem>]
  // Emitted after a true (no-reprocess) version restore, carrying the new latest
  // document's id so the host can refresh its list.
  restored: [documentId: number]
  'update-document': [version: DocumentListItem]
  'update:showVersionHistory': [value: boolean]
  // Notifies the host header of the real archived-version count once the
  // versions fetch resolves, so the History badge isn't stuck on a hardcode.
  'update:versionCount': [count: number]
}>()

const toast = useToast()
const { downloadBlob } = useFileDownload()

// Segmented-control state: 'text' | 'file' | 'both'. Maps to a SplitPane mode
// (right | left | split).
type SegmentedView = 'text' | 'file' | 'both'
const segmentedValue = ref<SegmentedView>('both')
const originalPdfUrl = ref<string>('')
const originalImageUrl = ref<string>('')

// Version history state
const versions = ref<DocumentListItem[]>([])
const loadingVersions = ref<boolean>(false)
const selectedVersion = ref<DocumentListItem | null>(null)

// Full text is fetched on demand (GET /document/{id}); list items no longer
// carry the (potentially large) `text` column.
const fullText = ref<string | null>(null)
const textLoading = ref<boolean>(false)

// Check if document has an original file that can be displayed.
// For TXT files and row-by-row CSV/XLSX, the "original file" exists but
// shouldn't show split-screen — the extracted text IS the original content
// (TXT) or represents partial data (CSV row).
const hasDisplayableOriginalFile = computed<boolean>(() => {
  if (!props.document.original_file?.id) return false
  if (!props.document.original_file?.file_type) return false

  const fileType = props.document.original_file.file_type
  const isPlainText = fileType === 'text/plain'
  const isCsvXlsxRowByRow = props.document.meta_data?.preprocessing_strategy === 'row_by_row'

  if (isPlainText || isCsvXlsxRowByRow) return false

  return true
})

const hasText = computed<boolean>(() => !!fullText.value)

const versionCount = computed<number>(() => versions.value.length || 1)

// Push the real count up to the host header so the History badge reflects
// archived versions rather than a hardcoded 1.
watch(versionCount, (count) => emit('update:versionCount', count), { immediate: true })

const originalFileType = computed<'pdf' | 'image' | 'other' | null>(() => {
  const fileType = props.document.original_file?.file_type
  if (!fileType) return null
  if (fileType.includes('pdf')) return 'pdf'
  if (fileType.includes('image')) return 'image'
  return 'other'
})

const splitMode = computed<'split' | 'left' | 'right'>(() => {
  if (segmentedValue.value === 'both') return 'split'
  if (segmentedValue.value === 'file') return 'left'
  return 'right'
})

function onSegmentedChange(value: string | number | boolean): void {
  segmentedValue.value = String(value) as SegmentedView
}

// Set default view: split (file + text) if both available, else file-only,
// else text-only.
const setDefaultView = (): void => {
  if (hasDisplayableOriginalFile.value && hasText.value) {
    segmentedValue.value = 'both'
  } else if (hasDisplayableOriginalFile.value) {
    segmentedValue.value = 'file'
  } else {
    segmentedValue.value = 'text'
  }
}

// Markdown rendering with XSS sanitizing
const safeMarkdown = computed<string>(() => {
  const text = fullText.value
  if (!text) return '<em>No text content available</em>'
  return DOMPurify.sanitize(marked.parse(text) as string)
})

const downloadDocument = async (): Promise<void> => {
  try {
    const fileId = props.document.preprocessed_file?.id || props.document.original_file?.id
    if (!fileId) {
      toast.error('No file available for download')
      return
    }
    const response = await filesApi.getContent(props.projectId, fileId)
    downloadBlob(
      response.data,
      props.document.original_file?.file_name || `document_${props.document.id}.pdf`,
    )
  } catch (error) {
    toast.error('Failed to download document')
    console.error(error)
  }
}

// Fetch the full document (with text) for a given document id.
const fetchFullText = async (docId: number | null | undefined): Promise<void> => {
  if (!docId) return
  textLoading.value = true
  try {
    const { data } = await documentsApi.get(props.projectId, docId)
    fullText.value = data?.text ?? null
  } catch (error) {
    console.error('Failed to load document text:', error)
    fullText.value = null
  } finally {
    textLoading.value = false
  }
}

// Fetch all versions of this document
const fetchVersions = async (): Promise<void> => {
  if (!props.document.original_file_id) return

  loadingVersions.value = true
  try {
    const response = await documentsApi.list(props.projectId, {
      file_id: props.document.original_file_id,
      config_id: props.document.preprocessing_config_id,
      include_archived: true,
      limit: 100,
    } as DocumentFilter)

    const docName = props.document.document_name || props.document.original_file?.file_name
    versions.value = (response.data.items || [])
      .filter((d) => d.document_name === docName)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    selectedVersion.value =
      versions.value.find((v) => v.id === props.document.id) || versions.value[0] || null
  } catch (error) {
    console.error('Failed to fetch document versions:', error)
    versions.value = []
  } finally {
    loadingVersions.value = false
  }
}

// Select a version to view
const selectVersion = (version: DocumentListItem): void => {
  selectedVersion.value = version
  fetchFullText(version.id)
  emit('update-document', version)
}

// Restore an archived version (creates a new latest version with same content).
const showRestoreConfirm = ref<boolean>(false)
const pendingRestoreVersion = ref<DocumentListItem | null>(null)
const restoreVersion = (version: DocumentListItem): void => {
  pendingRestoreVersion.value = version
  showRestoreConfirm.value = true
}
const confirmRestore = async (): Promise<void> => {
  const version = pendingRestoreVersion.value
  showRestoreConfirm.value = false
  pendingRestoreVersion.value = null
  if (!version) return

  try {
    // True restore: copy this version's content into a new latest version. No
    // reprocessing — the restored text is exactly the archived version's text.
    const { data } = await documentsApi.restoreVersion(props.projectId, version.id)
    toast.success('Version restored')
    // Refresh the version list, then show the freshly restored latest version.
    await fetchVersions()
    const newLatest = versions.value.find((v) => v.is_latest) || versions.value[0] || null
    if (newLatest) selectVersion(newLatest)
    // Let the host refresh its document list so the new latest is reflected there.
    emit('restored', data.id)
  } catch (error) {
    console.error('Failed to restore version:', error)
    toast.error(extractErrorMessage(error, 'Failed to restore version'))
  }
}

const revokeUrls = (): void => {
  if (originalPdfUrl.value) window.URL.revokeObjectURL(originalPdfUrl.value)
  if (originalImageUrl.value) window.URL.revokeObjectURL(originalImageUrl.value)
  originalPdfUrl.value = ''
  originalImageUrl.value = ''
}

// Load the full document (text + original-file preview + versions). Called on
// each open by the host, and on document swaps via the watcher below.
async function load(): Promise<void> {
  revokeUrls()

  try {
    await fetchFullText(props.document.id)

    if (props.document.original_file?.id) {
      const response = await filesApi.getContent(props.projectId, props.document.original_file.id, {
        preview: true,
      })
      if (originalFileType.value === 'image') {
        originalImageUrl.value = URL.createObjectURL(response.data)
      } else if (originalFileType.value === 'pdf') {
        originalPdfUrl.value = URL.createObjectURL(response.data)
      }
    }
    setDefaultView()
    await fetchVersions()
  } catch (error) {
    toast.error('Failed to load document preview.')
    console.error(error)
  }
}

defineExpose({ load, downloadDocument, onSegmentedChange })

// Load on open; revoke URLs on close.
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      selectedVersion.value = null
      load()
    } else {
      revokeUrls()
    }
  },
  { immediate: true },
)

// Watch for document changes while open (prev/next nav). The modal stays
// mounted, so the `open` watcher above won't fire — we must reload the full
// document (text + original-file preview + default view + versions), not just
// the text, otherwise the split-screen / original-file URL goes stale.
watch(
  () => props.document?.id,
  async () => {
    if (!props.open) return
    await load()
  },
)

onUnmounted(() => {
  revokeUrls()
})
</script>
