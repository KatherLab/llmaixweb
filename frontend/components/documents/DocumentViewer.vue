<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 overflow-hidden">
      <div
        class="absolute inset-0 bg-black/30 backdrop-blur-md transition-all"
        @click="$emit('close')"
      ></div>

      <div
        class="absolute inset-4 md:inset-8 bg-white rounded-lg shadow-2xl flex flex-col overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b bg-gray-50 rounded-t-lg">
          <div class="flex items-center space-x-4">
            <h3 class="text-lg font-semibold text-gray-900">
              {{
                document.document_name ||
                document.original_file?.file_name ||
                `Document #${document.id}`
              }}
            </h3>

            <p
              v-if="
                document.document_name &&
                document.original_file?.file_name &&
                document.document_name !== document.original_file.file_name
              "
              class="text-sm text-gray-500 mt-1"
            >
              Original File: {{ document.original_file.file_name }}
            </p>

            <!-- Extraction Method Badge -->
            <span
              v-if="extractionMethodInfo"
              :class="[
                'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                extractionMethodInfo.bgClass,
                extractionMethodInfo.textClass,
              ]"
              :title="extractionMethodInfo.description"
            >
              <svg
                v-if="extractionMethodInfo.icon"
                class="w-3.5 h-3.5 mr-1.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  :d="extractionMethodInfo.iconPath"
                />
              </svg>
              {{ extractionMethodInfo.label }}
            </span>
          </div>
          <div class="flex items-center space-x-2">
            <!-- Version History Button -->
            <button
              v-if="hasVersionHistory"
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              :title="showVersionHistory ? 'Hide version history' : 'Show version history'"
              @click="showVersionHistory = !showVersionHistory"
            >
              <svg
                class="h-4 w-4 mr-1.5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span
                v-if="versionCount > 0"
                class="bg-blue-100 text-blue-800 text-xs font-semibold mr-1 px-2 py-0.5 rounded-full"
              >
                {{ versionCount }}
              </span>
              History
            </button>
            <button
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="toggleView"
            >
              <svg
                class="h-4 w-4 mr-1.5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                />
              </svg>
              {{ viewModeLabel }}
            </button>
            <button
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="downloadDocument"
            >
              <svg
                class="h-4 w-4 mr-1.5"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                />
              </svg>
              Download
            </button>
            <button class="text-gray-400 hover:text-gray-500" @click="$emit('close')">
              <svg
                class="h-6 w-6"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
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

        <!-- Main Content -->
        <div class="flex-1 flex overflow-hidden relative">
          <div class="flex-1 overflow-auto">
            <!-- Text View -->
            <div v-if="viewMode === 'text'" class="p-6">
              <div class="prose max-w-none bg-gray-50 p-4 rounded-lg" v-html="safeMarkdown" />
            </div>
            <!-- PDF View -->
            <div v-else-if="viewMode === 'pdf' && originalPdfUrl" class="h-full">
              <iframe
                :src="originalPdfUrl"
                class="w-full h-full"
                frameborder="0"
                title="Original PDF"
              ></iframe>
            </div>
            <!-- Image View (for original image files) -->
            <div
              v-else-if="viewMode === 'image' && originalImageUrl"
              class="h-full p-4 bg-gray-100"
            >
              <div class="flex items-center justify-center h-full">
                <img
                  :src="originalImageUrl"
                  alt="Original document"
                  class="max-w-full max-h-full object-contain shadow-lg rounded-lg"
                />
              </div>
            </div>
            <!-- Side-by-side Compare View -->
            <div v-else-if="viewMode === 'compare'" class="flex h-full">
              <!-- Left: Original File (PDF or Image) -->
              <div class="w-1/2 border-r overflow-auto p-4 flex flex-col">
                <h4 class="font-medium text-gray-700 mb-2">Original File</h4>
                <!-- PDF Viewer -->
                <iframe
                  v-if="originalPdfUrl && originalFileType === 'pdf'"
                  :src="originalPdfUrl"
                  class="w-full flex-1"
                  frameborder="0"
                  title="Original PDF"
                ></iframe>
                <!-- Image Viewer -->
                <div
                  v-else-if="originalImageUrl && ['image'].includes(originalFileType)"
                  class="flex-1 flex items-center justify-center bg-gray-100 rounded-lg p-4"
                >
                  <img
                    :src="originalImageUrl"
                    alt="Original document"
                    class="max-w-full max-h-full object-contain"
                  />
                </div>
                <div v-else class="text-gray-400 flex items-center justify-center flex-1">
                  No original file available
                </div>
              </div>
              <!-- Right: Extracted Text -->
              <div class="w-1/2 overflow-auto p-4 flex flex-col">
                <h4 class="font-medium text-gray-700 mb-2">Extracted Text</h4>
                <div
                  class="prose max-w-none bg-gray-50 p-2 rounded-lg flex-1"
                  v-html="safeMarkdown"
                />
              </div>
            </div>
          </div>

          <!-- Version History Sidebar (overlays on top of Document Info when shown) -->
          <div
            v-if="showVersionHistory"
            class="absolute right-80 top-0 bottom-0 w-64 bg-white border-l shadow-lg z-10 overflow-auto"
          >
            <div class="p-4">
              <div class="flex items-center justify-between mb-4">
                <h4 class="font-semibold text-gray-900">Version History</h4>
                <button
                  class="text-gray-400 hover:text-gray-600"
                  @click="showVersionHistory = false"
                >
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <!-- Loading State -->
              <div v-if="loadingVersions" class="text-center py-8">
                <svg
                  class="animate-spin h-6 w-6 text-blue-600 mx-auto"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
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
                <p class="text-xs text-gray-500 mt-2">Loading versions...</p>
              </div>

              <!-- Versions List -->
              <div v-else-if="versions.length > 0" class="space-y-2">
                <div
                  v-for="version in versions"
                  :key="version.id"
                  :class="[
                    'p-3 rounded-lg border cursor-pointer transition-all',
                    selectedVersion?.id === version.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50',
                  ]"
                  @click="selectVersion(version)"
                >
                  <div class="flex items-center justify-between mb-1">
                    <span
                      :class="[
                        'text-xs font-medium px-1.5 py-0.5 rounded',
                        version.is_latest
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600',
                      ]"
                    >
                      {{ version.is_latest ? 'Current' : 'Archived' }}
                    </span>
                    <span class="text-xs text-gray-500"
                      >v{{ versionCount - versions.indexOf(version) }}</span
                    >
                  </div>
                  <p class="text-xs text-gray-600">
                    {{ formatRelativeTime(version.created_at) }}
                  </p>
                  <p
                    v-if="version.meta_data?.extraction_method"
                    class="text-xs text-gray-400 truncate mt-1"
                  >
                    {{ getShortExtractionMethod(version.meta_data.extraction_method) }}
                  </p>
                </div>
              </div>

              <!-- No Versions -->
              <div v-else class="text-center py-8">
                <svg
                  class="w-10 h-10 text-gray-300 mx-auto"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p class="text-sm text-gray-500 mt-2">Only one version exists</p>
              </div>
            </div>
          </div>

          <!-- Sidebar -->
          <div class="w-80 border-l bg-gray-50 overflow-auto">
            <div class="p-4 space-y-4">
              <!-- Version Badge -->
              <div
                v-if="selectedVersion"
                class="flex items-center justify-between p-3 bg-white rounded-lg border"
              >
                <span class="text-sm font-medium text-gray-700">Version Status</span>
                <span
                  :class="[
                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                    selectedVersion.is_latest
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-600',
                  ]"
                >
                  {{ selectedVersion.is_latest ? 'Current Version' : 'Archived Version' }}
                </span>
              </div>

              <!-- Document Info -->
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Document Information</h4>
                <dl class="space-y-2 text-sm">
                  <div>
                    <dt class="text-gray-500">Created</dt>
                    <dd class="text-gray-900">
                      {{ formatDateTime(selectedVersion?.created_at || document.created_at) }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">File Size</dt>
                    <dd class="text-gray-900">
                      {{ formatFileSize(document.original_file?.file_size) }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">Text Length</dt>
                    <dd class="text-gray-900">
                      {{ (selectedVersion?.text || document.text)?.length || 0 }} characters
                    </dd>
                  </div>
                  <div v-if="selectedVersion && !selectedVersion.is_latest">
                    <dt class="text-gray-500">Archived</dt>
                    <dd class="text-gray-900">{{ formatDateTime(selectedVersion.updated_at) }}</dd>
                  </div>
                </dl>
              </div>
              <!-- Preprocessing Info -->
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Preprocessing Configuration</h4>
                <dl class="space-y-2 text-sm">
                  <div>
                    <dt class="text-gray-500">Configuration</dt>
                    <dd class="text-gray-900">
                      {{
                        (selectedVersion?.preprocessing_config || document.preprocessing_config)
                          ?.name || 'Custom'
                      }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">OCR Engine</dt>
                    <dd class="text-gray-900">
                      {{
                        getEngineLabelWithKey(
                          (selectedVersion?.preprocessing_config || document.preprocessing_config)
                            ?.additional_settings?.ocr_engine,
                        )
                      }}
                    </dd>
                  </div>
                </dl>
              </div>
              <!-- Metadata -->
              <div
                v-if="
                  (selectedVersion?.meta_data || document.meta_data) &&
                  Object.keys(selectedVersion?.meta_data || document.meta_data).length > 0
                "
              >
                <h4 class="font-medium text-gray-900 mb-2">Metadata</h4>
                <div class="bg-white rounded-lg p-3 text-xs">
                  <pre class="overflow-x-auto">{{
                    JSON.stringify(selectedVersion?.meta_data || document.meta_data, null, 2)
                  }}</pre>
                </div>
              </div>
              <!-- Actions -->
              <div class="pt-4 border-t space-y-2">
                <!-- Restore button for archived versions -->
                <button
                  v-if="selectedVersion && !selectedVersion.is_latest"
                  class="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                  @click="restoreVersion(selectedVersion)"
                >
                  <svg
                    class="h-4 w-4 mr-2"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Restore This Version
                </button>
                <button
                  class="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                  @click="() => emit('reprocess', document)"
                >
                  <svg
                    class="h-4 w-4 mr-2"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Reprocess Document
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '@/services/api.js'
import { useToast } from 'vue-toastification'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { getEngineLabelWithKey } from '@/utils/ocrLabels'

const props = defineProps({
  document: { type: Object, required: true },
  projectId: { type: [String, Number], required: true },
})

const emit = defineEmits(['close', 'reprocess', 'update-document'])
const toast = useToast()
const viewMode = ref('text')
const originalPdfUrl = ref('')
const originalImageUrl = ref('')

// Version history state
const showVersionHistory = ref(false)
const versions = ref([])
const loadingVersions = ref(false)
const selectedVersion = ref(null)

const hasOriginalFile = computed(() => !!props.document.original_file?.id)
const hasText = computed(() => !!props.document.text)

// Get the current document (selected version or main document)
const currentDocument = computed(() => {
  return selectedVersion.value || props.document
})

// Check if document has version history (either has version_of or is part of a version chain)
const hasVersionHistory = computed(() => {
  return (
    props.document.version_of ||
    props.document.meta_data?.version_of ||
    props.document.meta_data?.replaced_document_id ||
    versions.value.length > 1
  )
})

// Total version count (estimated based on version_of chain)
const versionCount = computed(() => {
  // This is a placeholder - actual count comes from fetched versions
  return versions.value.length || 1
})

const originalFileType = computed(() => {
  const fileType = props.document.original_file?.file_type
  if (!fileType) return null
  if (fileType.includes('pdf')) return 'pdf'
  if (fileType.includes('image')) return 'image'
  return 'other'
})

const viewModeLabel = computed(() => {
  // Label describes what clicking will show, not current view
  if (viewMode.value === 'compare') return 'Show File' // clicking shows single file
  if (viewMode.value === 'pdf' || viewMode.value === 'image') return 'Show Text' // clicking shows text
  if (viewMode.value === 'text') return 'Show Both' // clicking shows compare (side-by-side)
  return 'Show Both'
})

// Extraction method info for display badges
const extractionMethodInfo = computed(() => {
  const metaData = props.document.meta_data || {}
  const extractionMethod = metaData.extraction_method
  const ocrEngine = metaData.ocr_engine
  const engineUsed = metaData.engine_used
  const ocrApplied = metaData.ocr_applied
  // embeddedText is available if needed for future logic

  // Icon paths
  const textIconPath =
    'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
  const ocrIconPath = 'M13 10V3L4 14h7v7l9-11h-7z'
  const remoteIconPath =
    'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9'

  // Determine extraction method label and styling
  if (
    extractionMethod === 'docling_serve_no_ocr' ||
    (engineUsed === 'docling_serve' && !ocrApplied)
  ) {
    return {
      label: 'Text Extraction',
      bgClass: 'bg-blue-100',
      textClass: 'text-blue-800',
      description: 'Extracted from embedded PDF text (no OCR)',
      icon: true,
      iconPath: textIconPath,
    }
  }

  if (
    extractionMethod === 'docling_serve_tesseract_ocr' ||
    extractionMethod === 'docling_serve_tesseract_image_ocr'
  ) {
    return {
      label: 'Local OCR',
      bgClass: 'bg-green-100',
      textClass: 'text-green-800',
      description: 'Processed with local Tesseract OCR',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  if (extractionMethod === 'docling_serve_tesseract_force_ocr') {
    return {
      label: 'Force OCR',
      bgClass: 'bg-amber-100',
      textClass: 'text-amber-800',
      description: 'Full-page OCR forced (even if embedded text exists)',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  if (ocrEngine === 'mistral_ocr' || engineUsed === 'mistral_ocr') {
    return {
      label: 'Mistral OCR',
      bgClass: 'bg-purple-100',
      textClass: 'text-purple-800',
      description: 'Processed with Mistral AI OCR API',
      icon: true,
      iconPath: remoteIconPath,
    }
  }

  if (ocrEngine === 'llm_vision' || engineUsed === 'llm_vision') {
    return {
      label: 'Vision LLM',
      bgClass: 'bg-indigo-100',
      textClass: 'text-indigo-800',
      description: 'Processed with Vision LLM API',
      icon: true,
      iconPath: remoteIconPath,
    }
  }

  // Fallback for legacy methods
  if (extractionMethod?.includes('no_ocr')) {
    return {
      label: 'Text Extraction',
      bgClass: 'bg-blue-100',
      textClass: 'text-blue-800',
      description: 'Extracted from embedded PDF text',
      icon: true,
      iconPath: textIconPath,
    }
  }

  if (extractionMethod?.includes('tesseract') || extractionMethod?.includes('ocr')) {
    return {
      label: 'OCR',
      bgClass: 'bg-green-100',
      textClass: 'text-green-800',
      description: 'Processed with OCR',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  return null
})

// Set default view mode: compare (file + text side-by-side) if both available
const setDefaultViewMode = () => {
  if (hasOriginalFile.value && hasText.value) {
    viewMode.value = 'compare'
  } else if (hasOriginalFile.value) {
    viewMode.value = originalFileType.value === 'image' ? 'image' : 'pdf'
  } else {
    viewMode.value = 'text'
  }
}

// Markdown rendering with XSS sanitizing
const safeMarkdown = computed(() => {
  const text = currentDocument.value?.text || props.document.text
  if (!text) return '<em>No text content available</em>'
  return DOMPurify.sanitize(marked.parse(text))
})

const toggleView = () => {
  const isImage = originalFileType.value === 'image'

  // Cycle: Compare → Single File (PDF/Image) → Text → Compare
  if (viewMode.value === 'compare') {
    // From compare: go to single file view
    viewMode.value = hasOriginalFile.value ? (isImage ? 'image' : 'pdf') : 'text'
  } else if (viewMode.value === 'pdf' || viewMode.value === 'image') {
    // From single file: go to text
    viewMode.value = 'text'
  } else if (viewMode.value === 'text') {
    // From text: go to compare if we have file + text
    if (hasOriginalFile.value && hasText.value) {
      viewMode.value = 'compare'
    } else if (hasOriginalFile.value) {
      viewMode.value = isImage ? 'image' : 'pdf'
    }
  }
}

const downloadDocument = async () => {
  try {
    const fileId = props.document.preprocessed_file?.id || props.document.original_file?.id
    if (!fileId) {
      toast.error('No file available for download')
      return
    }
    const response = await api.get(`/project/${props.projectId}/file/${fileId}/content`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute(
      'download',
      props.document.original_file?.file_name || `document_${props.document.id}.pdf`,
    )
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    toast.error('Failed to download document')
    console.error(error)
  }
}

const formatDateTime = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString()
}

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`
}

// Format relative time (e.g., "2 hours ago")
const formatRelativeTime = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

// Get short extraction method label
const getShortExtractionMethod = (method) => {
  if (!method) return ''
  if (method.includes('no_ocr')) return 'Text Extraction'
  if (method.includes('tesseract')) return 'Local OCR'
  if (method.includes('mistral')) return 'Mistral OCR'
  if (method.includes('llm_vision')) return 'Vision LLM'
  if (method.includes('force_ocr')) return 'Force OCR'
  return method.replace(/_/g, ' ').replace('docling serve', 'Docling')
}

// Fetch all versions of this document
const fetchVersions = async () => {
  if (!props.document.original_file_id) return

  loadingVersions.value = true
  try {
    // Fetch documents filtered by original file, preprocessing config, and include archived
    const response = await api.get(`/project/${props.projectId}/document`, {
      params: {
        file_id: props.document.original_file_id,
        config_id: props.document.preprocessing_config_id,
        include_archived: true,
        limit: 100, // Get all versions
      },
    })

    // Filter to only documents with same name (same document chain)
    const docName = props.document.document_name || props.document.original_file?.file_name
    versions.value = (response.data.items || [])
      .filter((d) => d.document_name === docName)
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

    // Set current document as selected
    selectedVersion.value =
      versions.value.find((v) => v.id === props.document.id) || versions.value[0]
  } catch (error) {
    console.error('Failed to fetch document versions:', error)
    versions.value = []
  } finally {
    loadingVersions.value = false
  }
}

// Select a version to view
const selectVersion = (version) => {
  selectedVersion.value = version
  // Emit event to parent to reload document with new version
  emit('update-document', version)
}

// Restore an archived version (creates a new latest version with same content)
const restoreVersion = async (version) => {
  if (
    !confirm(
      'Restore this archived version? This will create a new latest version with the same content.',
    )
  ) {
    return
  }

  try {
    // We need to reprocess the original file with the same config to create a new version
    // For now, emit event to parent to handle restoration
    emit('reprocess', { ...document, ...version })
    toast.success('Version restoration initiated. The document will be reprocessed.')
  } catch (error) {
    console.error('Failed to restore version:', error)
    toast.error('Failed to restore version')
  }
}

onMounted(async () => {
  document.body.style.overflow = 'hidden'
  try {
    if (props.document.original_file?.id) {
      const response = await api.get(
        `/project/${props.projectId}/file/${props.document.original_file.id}/content?preview=true`,
        { responseType: 'blob' },
      )
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
})

// Watch for document changes and refetch versions
watch(
  () => props.document?.id,
  async () => {
    await fetchVersions()
  },
)

onUnmounted(() => {
  document.body.style.overflow = ''
  if (originalPdfUrl.value) window.URL.revokeObjectURL(originalPdfUrl.value)
  if (originalImageUrl.value) window.URL.revokeObjectURL(originalImageUrl.value)
})
</script>
