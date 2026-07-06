<template>
  <BaseModal
    :open="open"
    placement="fullscreen"
    body-class="!p-0 flex flex-col h-full"
    @close="$emit('close')"
  >
    <!-- Header -->
    <DocumentViewerHeader
      :document="document"
      :has-version-history="hasVersionHistory"
      :show-version-history="showVersionHistory"
      :version-count="versionCount"
      :has-displayable-original-file="hasDisplayableOriginalFile"
      :has-text="hasText"
      :view-mode="viewMode"
      @close="$emit('close')"
      @toggle-version-history="showVersionHistory = !showVersionHistory"
      @change-view="changeView"
      @download="downloadDocument"
    />

    <!-- Main Content -->
    <div class="flex-1 flex overflow-hidden relative">
      <div class="flex-1 overflow-auto">
        <!-- Text View -->
        <DocumentTextView
          v-if="viewMode === 'text'"
          :text-loading="textLoading"
          :safe-markdown="safeMarkdown"
        />
        <!-- PDF / Image View -->
        <DocumentFilePreview
          v-else-if="
            (viewMode === 'pdf' && originalPdfUrl) || (viewMode === 'image' && originalImageUrl)
          "
          :view-mode="viewMode"
          :original-pdf-url="originalPdfUrl"
          :original-image-url="originalImageUrl"
        />
        <!-- Side-by-side Compare View -->
        <DocumentCompareView
          v-else-if="viewMode === 'compare'"
          :has-displayable-original-file="hasDisplayableOriginalFile"
          :original-pdf-url="originalPdfUrl"
          :original-image-url="originalImageUrl"
          :original-file-type="originalFileType ?? ''"
          :safe-markdown="safeMarkdown"
        />
      </div>

      <!-- Version History Sidebar (overlays on top of Document Info when shown) -->
      <VersionHistorySidebar
        v-if="showVersionHistory"
        :loading-versions="loadingVersions"
        :versions="versions"
        :selected-version="selectedVersion"
        :version-count="versionCount"
        @close="showVersionHistory = false"
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
    </div>

    <!-- Restore archived version confirmation -->
    <ConfirmationDialog
      :open="showRestoreConfirm"
      title="Restore archived version?"
      message="This will create a new latest version with the same content as the selected archived version."
      confirm-text="Restore"
      cancel-text="Cancel"
      confirm-variant="primary"
      @confirm="confirmRestore"
      @cancel="showRestoreConfirm = false"
    />
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useFileDownload } from '@/composables/useFileDownload'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import DocumentViewerHeader from './DocumentViewerHeader.vue'
import DocumentTextView from './DocumentTextView.vue'
import DocumentFilePreview from './DocumentFilePreview.vue'
import DocumentCompareView from './DocumentCompareView.vue'
import VersionHistorySidebar from './VersionHistorySidebar.vue'
import DocumentInfoSidebar from './DocumentInfoSidebar.vue'
import type { DocumentListItem, DocumentFilter } from '@/types'

interface Props {
  open: boolean
  document: DocumentListItem
  projectId: string | number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  reprocess: [payload: Partial<DocumentListItem>]
  'update-document': [version: DocumentListItem]
}>()
const toast = useToast()
const { downloadBlob } = useFileDownload()
type ViewMode = 'text' | 'pdf' | 'image' | 'compare'
const viewMode = ref<ViewMode>('text')
const originalPdfUrl = ref<string>('')
const originalImageUrl = ref<string>('')

// Version history state
const showVersionHistory = ref<boolean>(false)
const versions = ref<DocumentListItem[]>([])
const loadingVersions = ref<boolean>(false)
const selectedVersion = ref<DocumentListItem | null>(null)

// Full text is fetched on demand (GET /document/{id}); list items no longer
// carry the (potentially large) `text` column, so we can't read it from the
// passed-in document object.
const fullText = ref<string | null>(null)
const textLoading = ref<boolean>(false)

// Check if document has an original file that can be displayed
// For TXT files and row-by-row CSV/XLSX, the "original file" exists but shouldn't show split-screen
// because the extracted text IS the original content (TXT) or represents partial data (CSV row)
const hasDisplayableOriginalFile = computed<boolean>(() => {
  if (!props.document.original_file?.id) return false
  if (!props.document.original_file?.file_type) return false

  const fileType = props.document.original_file.file_type
  // TXT files: extracted text is the original content - no split view needed
  const isPlainText = fileType === 'text/plain'
  // CSV/XLSX row-by-row: each doc is one row, not the full spreadsheet - no split view needed
  const isCsvXlsxRowByRow = props.document.meta_data?.preprocessing_strategy === 'row_by_row'

  if (isPlainText || isCsvXlsxRowByRow) return false

  return true
})

const hasText = computed<boolean>(() => !!fullText.value)

// Check if document has version history (either has version_of or is part of a version chain)
const hasVersionHistory = computed<boolean>(() => {
  return (
    !!props.document.version_of ||
    !!props.document.meta_data?.version_of ||
    !!props.document.meta_data?.replaced_document_id ||
    versions.value.length > 1
  )
})

// Total version count (estimated based on version_of chain)
const versionCount = computed<number>(() => {
  // This is a placeholder - actual count comes from fetched versions
  return versions.value.length || 1
})

const originalFileType = computed<'pdf' | 'image' | 'other' | null>(() => {
  const fileType = props.document.original_file?.file_type
  if (!fileType) return null
  if (fileType.includes('pdf')) return 'pdf'
  if (fileType.includes('image')) return 'image'
  return 'other'
})

// Set default view mode: compare (file + text side-by-side) if both available
const setDefaultViewMode = (): void => {
  if (hasDisplayableOriginalFile.value && hasText.value) {
    viewMode.value = 'compare'
  } else if (hasDisplayableOriginalFile.value) {
    viewMode.value = originalFileType.value === 'image' ? 'image' : 'pdf'
  } else {
    // No displayable original file (TXT, row-by-row CSV, or no file): always show text view
    viewMode.value = 'text'
  }
}

// Handle explicit view-mode changes from the segmented control. "file" is
// resolved to pdf or image based on the original file type.
const changeView = (mode: 'text' | 'pdf' | 'image' | 'compare' | 'file'): void => {
  if (mode === 'file') {
    viewMode.value = originalFileType.value === 'image' ? 'image' : 'pdf'
  } else if (mode === 'compare') {
    // Only enter compare if we actually have both halves; otherwise fall back.
    if (hasDisplayableOriginalFile.value && hasText.value) {
      viewMode.value = 'compare'
    } else if (hasDisplayableOriginalFile.value) {
      viewMode.value = originalFileType.value === 'image' ? 'image' : 'pdf'
    } else {
      viewMode.value = 'text'
    }
  } else {
    viewMode.value = mode
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

// Fetch the full document (with text) for a given document id. List items no
// longer include `text`, so the viewer pulls it on demand.
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
    // Fetch documents filtered by original file, preprocessing config, and include archived
    const response = await documentsApi.list(props.projectId, {
      file_id: props.document.original_file_id,
      config_id: props.document.preprocessing_config_id,
      include_archived: true,
      limit: 100, // Get all versions
    } as DocumentFilter)

    // Filter to only documents with same name (same document chain)
    const docName = props.document.document_name || props.document.original_file?.file_name
    versions.value = (response.data.items || [])
      .filter((d) => d.document_name === docName)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    // Set current document as selected
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
  // Load that version's text (versions list items don't carry `text`).
  fetchFullText(version.id)
  // Emit event to parent to reload document with new version
  emit('update-document', version)
}

// Restore an archived version (creates a new latest version with same content).
// Confirms via the shared ConfirmationDialog instead of a browser confirm().
const showRestoreConfirm = ref<boolean>(false)
const pendingRestoreVersion = ref<DocumentListItem | null>(null)
const restoreVersion = (version: DocumentListItem): void => {
  pendingRestoreVersion.value = version
  showRestoreConfirm.value = true
}
const confirmRestore = (): void => {
  const version = pendingRestoreVersion.value
  showRestoreConfirm.value = false
  pendingRestoreVersion.value = null
  if (!version) return

  try {
    // We need to reprocess the original file with the same config to create a new version
    // For now, emit event to parent to handle restoration
    emit('reprocess', { ...props.document, ...version })
    toast.success('Version restoration initiated. The document will be reprocessed.')
  } catch (error) {
    console.error('Failed to restore version:', error)
    toast.error('Failed to restore version')
  }
}

// Load the full document (text + original-file preview + versions). Called on
// each open since the component stays mounted to enable the close transition.
async function loadDocument(): Promise<void> {
  // Reset preview URLs from any previously viewed document.
  if (originalPdfUrl.value) window.URL.revokeObjectURL(originalPdfUrl.value)
  if (originalImageUrl.value) window.URL.revokeObjectURL(originalImageUrl.value)
  originalPdfUrl.value = ''
  originalImageUrl.value = ''

  try {
    // Fetch the full document text (list items no longer carry `text`).
    await fetchFullText(props.document.id)

    if (props.document.original_file?.id) {
      const response = await filesApi.getContent(props.projectId, props.document.original_file.id, {
        preview: true,
      })
      // Load image URL for image files, otherwise PDF URL
      if (originalFileType.value === 'image') {
        originalImageUrl.value = URL.createObjectURL(response.data)
      } else if (originalFileType.value === 'pdf') {
        originalPdfUrl.value = URL.createObjectURL(response.data)
      }
    }
    // Set default view mode
    setDefaultViewMode()

    // Fetch version history
    await fetchVersions()
  } catch (error) {
    toast.error('Failed to load document preview.')
    console.error(error)
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      showVersionHistory.value = false
      selectedVersion.value = null
      loadDocument()
    } else if (originalPdfUrl.value || originalImageUrl.value) {
      if (originalPdfUrl.value) window.URL.revokeObjectURL(originalPdfUrl.value)
      if (originalImageUrl.value) window.URL.revokeObjectURL(originalImageUrl.value)
      originalPdfUrl.value = ''
      originalImageUrl.value = ''
    }
  },
  { immediate: true },
)

// Watch for document changes while open and refetch versions + text
watch(
  () => props.document?.id,
  async (newId) => {
    if (!props.open) return
    fetchFullText(newId)
    await fetchVersions()
  },
)

onUnmounted(() => {
  if (originalPdfUrl.value) window.URL.revokeObjectURL(originalPdfUrl.value)
  if (originalImageUrl.value) window.URL.revokeObjectURL(originalImageUrl.value)
})
</script>
