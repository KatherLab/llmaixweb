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
        <LoadingSpinner size="small" />
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
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatRelativeTime as sharedFormatRelativeTime } from '@/utils/formatters'

defineProps({
  loadingVersions: { type: Boolean, default: false },
  versions: { type: Array, default: () => [] },
  selectedVersion: { type: Object, default: null },
  versionCount: { type: Number, default: 0 },
})

defineEmits(['close', 'select-version'])

// Format relative time (e.g., "2 hours ago"). Delegates the just-now/m/h/d
// tiers to the shared formatter; versions older than a week fall back to a
// locale date (preserves the original 7-day cutoff vs the shared 30-day one).
const formatRelativeTime = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (isNaN(date)) return ''
  if (Date.now() - date.getTime() >= 604800000) return date.toLocaleDateString()
  return sharedFormatRelativeTime(dateString)
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
