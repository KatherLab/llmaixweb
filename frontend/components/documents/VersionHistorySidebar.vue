<template>
  <div class="absolute right-80 top-0 bottom-0 w-64 bg-white border-l shadow-lg z-10 overflow-auto">
    <div class="p-4">
      <div class="flex items-center justify-between mb-4">
        <h4 class="font-semibold text-gray-900">Version History</h4>
        <button class="text-gray-400 hover:text-gray-600" @click="$emit('close')">
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
          ></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
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
          @click="$emit('select-version', version)"
        >
          <div class="flex items-center justify-between mb-1">
            <span
              :class="[
                'text-xs font-medium px-1.5 py-0.5 rounded',
                version.is_latest ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600',
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
</template>

<script setup>
defineProps({
  loadingVersions: { type: Boolean, default: false },
  versions: { type: Array, default: () => [] },
  selectedVersion: { type: Object, default: null },
  versionCount: { type: Number, default: 0 },
})

defineEmits(['close', 'select-version'])

// Format relative time (e.g., "2 hours ago")
// NOTE: local copy preserved verbatim from the original DocumentViewer to avoid
// behavior drift vs utils/formatters.formatRelativeTime (different day cutoff +
// locale). Consolidation is a Phase 3 concern.
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
</script>
