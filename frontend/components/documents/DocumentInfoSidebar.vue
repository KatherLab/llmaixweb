<template>
  <div class="w-80 border-l bg-slate-50 overflow-auto">
    <div class="p-4 space-y-4">
      <!-- Version Badge -->
      <div
        v-if="selectedVersion"
        class="flex items-center justify-between p-3 bg-white rounded-lg border"
      >
        <span class="text-sm font-medium text-slate-700">Version Status</span>
        <span
          :class="[
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
            selectedVersion.is_latest
              ? 'bg-green-100 text-green-800'
              : 'bg-slate-100 text-slate-600',
          ]"
        >
          {{ selectedVersion.is_latest ? 'Current Version' : 'Archived Version' }}
        </span>
      </div>

      <!-- Document Info -->
      <div>
        <h4 class="font-medium text-slate-900 mb-2">Document Information</h4>
        <dl class="space-y-2 text-sm">
          <div>
            <dt class="text-slate-500">Created</dt>
            <dd class="text-slate-900">
              {{ formatDateFull(selectedVersion?.created_at || document.created_at) }}
            </dd>
          </div>
          <div>
            <dt class="text-slate-500">File Size</dt>
            <dd class="text-slate-900">
              {{ formatFileSize(document.original_file?.file_size, 'Unknown') }}
            </dd>
          </div>
          <div>
            <dt class="text-slate-500">Text Length</dt>
            <dd class="text-slate-900">{{ fullText?.length || 0 }} characters</dd>
          </div>
          <div v-if="selectedVersion && !selectedVersion.is_latest">
            <dt class="text-slate-500">Archived</dt>
            <dd class="text-slate-900">{{ formatDateFull(selectedVersion.updated_at) }}</dd>
          </div>
        </dl>
      </div>
      <!-- Preprocessing Info -->
      <div>
        <h4 class="font-medium text-slate-900 mb-2">Preprocessing Configuration</h4>
        <dl class="space-y-2 text-sm">
          <div>
            <dt class="text-slate-500">Configuration</dt>
            <dd class="text-slate-900">
              {{
                (selectedVersion?.preprocessing_config || document.preprocessing_config)?.name ||
                'Custom'
              }}
            </dd>
          </div>
          <div>
            <dt class="text-slate-500">OCR Engine</dt>
            <dd class="text-slate-900">
              {{
                getEngineLabelWithKey(
                  (selectedVersion?.preprocessing_config || document.preprocessing_config)
                    ?.additional_settings?.ocr_engine,
                )
              }}
            </dd>
          </div>
          <div v-if="getModelName(selectedVersion || document)">
            <dt class="text-slate-500">Model</dt>
            <dd class="text-slate-900">
              {{ getModelName(selectedVersion || document) }}
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
        <h4 class="font-medium text-slate-900 mb-2">Metadata</h4>
        <div class="bg-white rounded-lg p-3 text-xs">
          <JsonViewer :data="selectedVersion?.meta_data || document.meta_data" />
        </div>
      </div>
      <!-- Actions -->
      <div class="pt-4 border-t space-y-2">
        <!-- Restore button for archived versions -->
        <BaseButton
          v-if="selectedVersion && !selectedVersion.is_latest"
          variant="success"
          class="w-full"
          @click="$emit('restore-version', selectedVersion)"
        >
          <RefreshCw class="h-4 w-4" />
          Restore This Version
        </BaseButton>
        <BaseButton variant="primary" class="w-full" @click="$emit('reprocess', document)">
          <RefreshCw class="h-4 w-4" />
          Reprocess Document
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { RefreshCw } from '@lucide/vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { getEngineLabelWithKey } from '@/utils/ocrLabels'
import { formatDateFull, formatFileSize } from '@/utils/formatters'

defineProps({
  document: { type: Object, required: true },
  selectedVersion: { type: Object, default: null },
  fullText: { type: String, default: null },
})

defineEmits(['restore-version', 'reprocess'])

const getModelName = (doc) => {
  if (!doc) return ''
  const metaData = doc.meta_data || {}
  // Check for specific model fields first
  if (metaData.mistral_model) return metaData.mistral_model
  if (metaData.vision_model) return metaData.vision_model
  // Fallback to generic model field
  if (metaData.model) return metaData.model
  // No model for local OCR
  return ''
}
</script>
