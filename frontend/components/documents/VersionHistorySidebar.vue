<template>
  <div
    class="absolute right-80 top-0 bottom-0 w-64 bg-white dark:bg-slate-900 border-l dark:border-slate-700 shadow-lg z-10 overflow-auto"
  >
    <div class="p-4">
      <div class="flex items-center justify-between mb-4">
        <h4 class="font-semibold text-slate-900 dark:text-white">Version History</h4>
        <button
          class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          @click="$emit('close')"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loadingVersions" class="text-center py-8">
        <LoadingSpinner size="small" />
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">Loading versions...</p>
      </div>

      <!-- Versions List -->
      <div v-else-if="versions.length > 0" class="space-y-2">
        <div
          v-for="version in versions"
          :key="version.id"
          :class="[
            'p-3 rounded-lg border cursor-pointer transition-all',
            selectedVersion?.id === version.id
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:border-slate-600 dark:hover:bg-slate-800',
          ]"
          @click="$emit('select-version', version)"
        >
          <div class="flex items-center justify-between mb-1">
            <span
              :class="[
                'text-xs font-medium px-1.5 py-0.5 rounded',
                version.is_latest
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
              ]"
            >
              {{ version.is_latest ? 'Current' : 'Archived' }}
            </span>
            <span class="text-xs text-slate-500 dark:text-slate-400"
              >v{{ versionCount - versions.indexOf(version) }}</span
            >
          </div>
          <p class="text-xs text-slate-600 dark:text-slate-400">
            {{ formatRelativeTime(version.created_at) }}
          </p>
          <p
            v-if="version.meta_data?.extraction_method"
            class="text-xs text-slate-400 dark:text-slate-400 truncate mt-1"
          >
            {{ getShortExtractionMethod(version.meta_data.extraction_method) }}
          </p>
        </div>
      </div>

      <!-- No Versions -->
      <div v-else class="text-center py-8">
        <FileText class="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto" />
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">Only one version exists</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FileText, X } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatRelativeTime as sharedFormatRelativeTime } from '@/utils/formatters'
import type { DocumentListItem } from '@/types'

interface Props {
  loadingVersions?: boolean
  versions?: DocumentListItem[]
  selectedVersion?: DocumentListItem | null
  versionCount?: number
}

withDefaults(defineProps<Props>(), {
  loadingVersions: false,
  versions: () => [],
  selectedVersion: null,
  versionCount: 0,
})

defineEmits<{
  close: []
  'select-version': [version: DocumentListItem]
}>()

// Format relative time (e.g., "2 hours ago"). Delegates the just-now/m/h/d
// tiers to the shared formatter; versions older than a week fall back to a
// locale date (preserves the original 7-day cutoff vs the shared 30-day one).
const formatRelativeTime = (dateString: string | null | undefined): string => {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return ''
  if (Date.now() - date.getTime() >= 604800000) return date.toLocaleDateString()
  return sharedFormatRelativeTime(dateString)
}

// Get short extraction method label
const getShortExtractionMethod = (method: string | null | undefined): string => {
  if (!method) return ''
  if (method.includes('no_ocr')) return 'Text Extraction'
  if (method.includes('tesseract')) return 'Local OCR'
  if (method.includes('mistral')) return 'Mistral OCR'
  if (method.includes('llm_vision')) return 'Vision LLM'
  if (method.includes('force_ocr')) return 'Force OCR'
  return method.replace(/_/g, ' ').replace('docling serve', 'Docling')
}
</script>
