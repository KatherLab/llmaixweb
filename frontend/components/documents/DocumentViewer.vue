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
          </div>
          <div class="flex items-center space-x-2">
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
        <div class="flex-1 flex overflow-hidden">
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

          <!-- Sidebar -->
          <div class="w-80 border-l bg-gray-50 overflow-auto">
            <div class="p-4 space-y-4">
              <!-- Document Info -->
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Document Information</h4>
                <dl class="space-y-2 text-sm">
                  <div>
                    <dt class="text-gray-500">Created</dt>
                    <dd class="text-gray-900">{{ formatDateTime(document.created_at) }}</dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">File Size</dt>
                    <dd class="text-gray-900">
                      {{ formatFileSize(document.original_file?.file_size) }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">Text Length</dt>
                    <dd class="text-gray-900">{{ document.text?.length || 0 }} characters</dd>
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
                      {{ document.preprocessing_config?.name || 'Custom' }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-gray-500">OCR Engine</dt>
                    <dd class="text-gray-900">
                      {{
                        getEngineLabelWithKey(
                          document.preprocessing_config?.additional_settings?.ocr_engine,
                        )
                      }}
                    </dd>
                  </div>
                </dl>
              </div>
              <!-- Metadata -->
              <div v-if="document.meta_data && Object.keys(document.meta_data).length > 0">
                <h4 class="font-medium text-gray-900 mb-2">Metadata</h4>
                <div class="bg-white rounded-lg p-3 text-xs">
                  <pre class="overflow-x-auto">{{
                    JSON.stringify(document.meta_data, null, 2)
                  }}</pre>
                </div>
              </div>
              <!-- Actions -->
              <div class="pt-4 border-t">
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/services/api.js'
import { useToast } from 'vue-toastification'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { getEngineLabelWithKey } from '@/utils/ocrLabels'

const props = defineProps({
  document: { type: Object, required: true },
  projectId: { type: [String, Number], required: true },
})

const emit = defineEmits(['close', 'reprocess'])
const toast = useToast()
const viewMode = ref('text')
const originalPdfUrl = ref('')
const originalImageUrl = ref('')

const hasOriginalFile = computed(() => !!props.document.original_file?.id)
const hasText = computed(() => !!props.document.text)

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
  if (!props.document.text) return '<em>No text content available</em>'
  return DOMPurify.sanitize(marked.parse(props.document.text))
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
  } catch (error) {
    toast.error('Failed to load document preview.')
    console.error(error)
  }
})

onUnmounted(() => {
  document.body.style.overflow = ''
  if (originalPdfUrl.value) window.URL.revokeObjectURL(originalPdfUrl.value)
  if (originalImageUrl.value) window.URL.revokeObjectURL(originalImageUrl.value)
})
</script>
