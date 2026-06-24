<template>
  <div class="flex items-center justify-between p-4 border-b bg-gray-50 rounded-t-lg">
    <div class="flex items-center space-x-4">
      <h3 class="text-lg font-semibold text-gray-900">
        {{
          document.document_name || document.original_file?.file_name || `Document #${document.id}`
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
      <ExtractionMethodBadge :document="document" />
    </div>
    <div class="flex items-center space-x-2">
      <!-- Version History Button -->
      <button
        v-if="hasVersionHistory"
        class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        :title="showVersionHistory ? 'Hide version history' : 'Show version history'"
        @click="$emit('toggle-version-history')"
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
        v-if="hasDisplayableOriginalFile"
        class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        @click="$emit('toggle-view')"
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
      <span
        v-else-if="!hasDisplayableOriginalFile && hasText"
        class="inline-flex items-center px-3 py-1.5 border border-gray-200 text-sm font-medium rounded-md text-gray-500 bg-gray-50"
        title="Only text view is available"
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
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        Text Only
      </span>
      <button
        class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        @click="$emit('download')"
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
</template>

<script setup>
import ExtractionMethodBadge from './ExtractionMethodBadge.vue'

defineProps({
  document: { type: Object, required: true },
  hasVersionHistory: { type: Boolean, default: false },
  showVersionHistory: { type: Boolean, default: false },
  versionCount: { type: Number, default: 0 },
  hasDisplayableOriginalFile: { type: Boolean, default: false },
  hasText: { type: Boolean, default: false },
  viewModeLabel: { type: String, default: 'Show Both' },
})

defineEmits(['close', 'toggle-version-history', 'toggle-view', 'download'])
</script>
