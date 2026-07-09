<script setup lang="ts">
import { ref, computed, watch, type PropType } from 'vue'
import { trialsApi } from '@/services/trialsApi'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { useFileDownload } from '@/composables/useFileDownload'
import { selectClass, labelClass, checkboxClass } from '@/utils/formStyles'
import type { TrialSummary } from '@/types'

const { downloadFromApi } = useFileDownload()

const props = defineProps({
  open: { type: Boolean, default: false },
  trial: { type: Object as PropType<Partial<TrialSummary> | null>, default: () => ({}) },
  projectId: { type: [String, Number] as PropType<string | number>, default: undefined },
})
const emit = defineEmits<{ close: [] }>()

const format = ref<'json' | 'csv'>('json')
const includeContent = ref(true)

const isDownloading = ref(false)
const toast = useToast()

const isJsonZip = computed(() => format.value === 'json')
const isCsvZip = computed(() => format.value === 'csv' && includeContent.value)
const isCsvOnly = computed(() => format.value === 'csv' && !includeContent.value)
const fileExt = computed(() => (isCsvOnly.value ? 'csv' : 'zip'))

watch(
  () => props.open,
  (open) => {
    if (open) {
      format.value = 'json'
      includeContent.value = true
    }
  },
)

async function download(): Promise<void> {
  if (isDownloading.value) return
  isDownloading.value = true
  try {
    await downloadFromApi(
      () =>
        trialsApi.download(props.projectId!, props.trial!.id!, {
          format: format.value,
          include_content: includeContent.value,
        }),
      `trial_${props.trial!.id}_results.${fileExt.value}`,
    )
    toast.success('Downloaded')
    emit('close')
  } catch {
    toast.error('Download failed')
  } finally {
    isDownloading.value = false
  }
}
</script>

<template>
  <BaseModal
    :open="open"
    title="Download Trial Results"
    size="md"
    body-class="p-6"
    @close="$emit('close')"
  >
    <Callout variant="gray" class="mb-4 text-xs">
      <span v-if="isJsonZip">
        <strong>JSON (per-document):</strong> Downloads a <b>ZIP archive</b> with one JSON file per
        document.
        <span class="block">
          Each file includes all extracted results, full document metadata, preprocessing
          configuration, and trial configuration.
        </span>
      </span>
      <span v-else-if="isCsvZip">
        <strong>CSV (with files):</strong> Downloads a <b>ZIP archive</b> with the CSV and attached
        files.
        <span class="block">
          The CSV includes all extracted results, full document metadata, preprocessing
          configuration, and trial configuration.
        </span>
      </span>
      <span v-else>
        <strong>CSV (flat):</strong> Downloads a single CSV file, one row per document.<br />
        Includes all extracted results, document metadata, preprocessing configuration, and trial
        configuration.
      </span>
    </Callout>

    <div class="mb-4">
      <label :class="labelClass">Format</label>
      <select v-model="format" :class="selectClass">
        <option value="json">JSON (per-document, ZIP)</option>
        <option value="csv">CSV (table, with optional files)</option>
      </select>
    </div>

    <div class="mb-4">
      <label :class="labelClass">Options</label>
      <label class="flex items-center text-sm text-content-muted">
        <input v-model="includeContent" type="checkbox" :class="checkboxClass" />
        <span class="ml-2"
          >Include document content
          <span
            class="text-content-subtle"
            title="If checked: you will also receive the original document text and files inside the ZIP."
          >
            (adds document text and source files)
          </span>
        </span>
      </label>
    </div>

    <div v-if="format === 'csv'" class="mb-3 text-xs text-content-muted">
      <span v-if="includeContent">
        Will include original files and full document text inside a ZIP.<br />
        <b>Note:</b> Download may be large if your trial contains many files.
      </span>
      <span v-else> Only a single CSV will be downloaded (no files/text included). </span>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">Cancel</BaseButton>
      <BaseButton variant="primary" :loading="isDownloading" @click="download">{{
        isDownloading ? 'Downloading...' : 'Download'
      }}</BaseButton>
    </template>
  </BaseModal>
</template>
