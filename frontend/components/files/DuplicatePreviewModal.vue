<template>
  <BaseModal :open="open" size="lg" :close-on-backdrop="false" @close="emit('cancel')">
    <!-- Header -->
    <template #header>
      <div class="flex items-center gap-3">
        <!-- Dynamic icon based on situation -->
        <svg
          v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates"
          class="w-6 h-6 text-blue-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <svg
          v-else
          class="w-6 h-6 text-amber-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <h3 class="text-lg font-semibold text-gray-900">
          <template v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates">
            PDF Embedded Text Detected
          </template>
          <template v-else-if="hasSameConfigDuplicates">
            Existing Documents Will Be Archived
          </template>
          <template v-else> Existing Documents Found </template>
        </h3>
      </div>
    </template>

    <!-- Body -->
    <div class="space-y-4">
      <!-- Different messages based on situation -->
      <template v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates">
        <p class="text-sm text-gray-600">
          The following PDF file(s) have embedded text. Since "Force OCR" is not enabled, the
          embedded text will be extracted directly regardless of the selected OCR engine. The result
          will be identical to previous extractions.
        </p>
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div class="flex items-start gap-2">
            <svg
              class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p class="text-xs text-blue-800">
              <strong>Tip:</strong> Enable
              <code class="bg-blue-100 px-1 rounded">Force OCR for PDFs</code>
              in Advanced Options to force OCR on all pages, ignoring embedded text.
            </p>
          </div>
        </div>
      </template>

      <template v-else-if="hasSameConfigDuplicates">
        <p class="text-sm text-gray-600">
          The following files have existing documents with the
          <strong>same OCR configuration</strong>. Running preprocessing will create new versions
          and archive the old ones. Archived documents are hidden by default but can be viewed in
          the document history.
        </p>

        <!-- Option to skip existing -->
        <label
          class="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors"
        >
          <input v-model="skipExisting" type="checkbox" class="mt-0.5 text-blue-600 rounded" />
          <div class="flex-1">
            <p class="text-sm font-medium text-blue-900">
              Only process files without existing documents
            </p>
            <p class="text-xs text-blue-700 mt-1">
              Skip files that already have documents for this OCR configuration. Useful if you want
              to process only new files or re-process files where OCR quality was poor.
            </p>
          </div>
        </label>
      </template>

      <template v-else>
        <p class="text-sm text-gray-600">
          The following files have existing documents with a different OCR configuration. Running
          preprocessing will create additional documents (not replace existing ones). Both versions
          will be preserved.
        </p>
      </template>

      <!-- Files with duplicates list -->
      <div class="max-h-80 overflow-y-auto border border-gray-200 rounded-lg">
        <!-- Show same-config duplicates first (if any) -->
        <template v-if="hasSameConfigDuplicates">
          <div
            v-for="item in duplicatePreview?.same_config_duplicates"
            :key="item.file_id"
            class="px-4 py-3 border-b border-gray-100 hover:bg-amber-50"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">
                  {{ item.file_name }}
                </p>
                <p class="text-xs text-amber-700 mt-1">
                  <svg
                    class="w-3 h-3 inline mr-1"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  {{ item.existing_document_count }} existing document{{
                    item.existing_document_count !== 1 ? 's' : ''
                  }}
                  with same config will be archived
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-amber-100 text-amber-700 flex-shrink-0 ml-3"
              >
                Same config
              </span>
            </div>
          </div>
        </template>

        <!-- Show PDFs with embedded text -->
        <template v-if="hasPdfsWithEmbeddedText">
          <div
            v-for="pdf in duplicatePreview?.pdfs_with_embedded_text"
            :key="pdf.file_id"
            class="px-4 py-3 border-b border-gray-100 hover:bg-blue-50"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">
                  {{ pdf.file_name }}
                </p>
                <p class="text-xs text-blue-700 mt-1">
                  <svg
                    class="w-3 h-3 inline mr-1"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 16h-1v-4h-1m1-4h.01"
                    />
                  </svg>
                  Has embedded text
                  <span v-if="pdf.existing_document_ocr_method" class="text-gray-500">
                    • Previously extracted with: {{ pdf.existing_document_ocr_method }}
                  </span>
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-700 flex-shrink-0 ml-3"
              >
                Embedded text
              </span>
            </div>
          </div>
        </template>

        <!-- Show different-config duplicates (if any, and no same-config) -->
        <template v-if="!hasSameConfigDuplicates && !hasPdfsWithEmbeddedText">
          <div
            v-for="item in duplicatePreview?.files_with_duplicates"
            :key="item.file_id"
            class="px-4 py-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">
                  {{ item.file_name }}
                </p>
                <p class="text-xs text-gray-500 mt-1">
                  {{ item.existing_document_count }} existing document{{
                    item.existing_document_count !== 1 ? 's' : ''
                  }}
                  with different config
                  <span v-if="item.config_name" class="text-gray-400">
                    • Config: {{ item.config_name }}
                  </span>
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700 flex-shrink-0 ml-3"
              >
                Different config
              </span>
            </div>
          </div>
        </template>
      </div>

      <!-- Summary -->
      <div class="bg-gray-50 rounded-lg p-3 flex items-center justify-between text-sm">
        <span class="text-gray-600">
          <span class="font-semibold text-gray-900">{{
            duplicatePreview?.files_with_duplicates?.length || 0
          }}</span>
          file{{ (duplicatePreview?.files_with_duplicates?.length || 0) !== 1 ? 's' : '' }}
          with existing documents
        </span>
        <span class="text-gray-600">
          <span class="font-semibold text-gray-900">{{
            duplicatePreview?.files_without_duplicates
          }}</span>
          new file{{ duplicatePreview?.files_without_duplicates !== 1 ? 's' : '' }}
        </span>
      </div>

      <!-- Info note about document versioning (only for same-config duplicates) -->
      <div v-if="hasSameConfigDuplicates" class="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div class="flex items-start gap-2">
          <svg
            class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p class="text-xs text-blue-800">
            <strong>Document versioning:</strong> Previous versions are preserved with
            <code class="bg-blue-100 px-1 rounded">is_latest=false</code> and can be restored if
            needed. Only the latest version is shown in the document list by default.
          </p>
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <template #footer>
      <BaseButton variant="secondary" @click="emit('cancel')">Cancel</BaseButton>
      <BaseButton
        class="flex items-center gap-2"
        @click="emit('confirm', { skipExisting: skipExisting })"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M5 13l4 4L19 7"
          />
        </svg>
        <template v-if="skipExisting">Process New Files Only</template>
        <template v-else-if="hasSameConfigDuplicates">Archive & Continue</template>
        <template v-else>Continue</template>
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

const props = defineProps({
  open: { type: Boolean, required: true },
  duplicatePreview: { type: Object, default: null },
})

const emit = defineEmits(['confirm', 'cancel'])

// Owned UI state — reset to unchecked each time the modal opens.
const skipExisting = ref(false)
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) skipExisting.value = false
  },
)

const hasSameConfigDuplicates = computed(() => {
  return (
    props.duplicatePreview?.same_config_duplicates &&
    props.duplicatePreview.same_config_duplicates.length > 0
  )
})

const hasPdfsWithEmbeddedText = computed(() => {
  return (
    props.duplicatePreview?.pdfs_with_embedded_text &&
    props.duplicatePreview.pdfs_with_embedded_text.length > 0
  )
})
</script>
