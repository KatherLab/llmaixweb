<script setup>
import { ref, computed, watch } from 'vue'
import { Info } from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { useFileDownload } from '@/composables/useFileDownload'
import { selectClass, labelClass } from '@/utils/formStyles'
import { getBannerClass } from '@/utils/statusStyles'

const { downloadFromApi } = useFileDownload()

const props = defineProps({
  open: Boolean,
  trial: { type: Object, default: () => ({}) },
  projectId: { type: [String, Number], default: undefined },
})
const emit = defineEmits(['close'])

const format = ref('json')
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

async function download() {
  if (isDownloading.value) return
  isDownloading.value = true
  try {
    await downloadFromApi(
      () =>
        trialsApi.download(props.projectId, props.trial.id, {
          format: format.value,
          include_content: includeContent.value,
        }),
      `trial_${props.trial.id}_results.${fileExt.value}`,
    )
    toast.success('Downloaded!')
    emit('close')
  } catch (e) {
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
    <div
      class="mb-4 flex items-start gap-2 text-xs rounded px-3 py-2"
      :class="getBannerClass('gray')"
    >
      <Info class="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
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
    </div>

    <div class="mb-4">
      <label :class="labelClass">Format</label>
      <select v-model="format" :class="selectClass">
        <option value="json">JSON (per-document, ZIP)</option>
        <option value="csv">CSV (table, with optional files)</option>
      </select>
    </div>

    <div class="mb-4">
      <label :class="labelClass">Options</label>
      <label class="flex items-center text-sm text-slate-700 dark:text-slate-300">
        <input
          v-model="includeContent"
          type="checkbox"
          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-600 dark:bg-slate-700 rounded"
        />
        <span class="ml-2"
          >Include document content
          <span
            class="text-slate-400 dark:text-slate-500"
            title="If checked: you will also receive the original document text and files inside the ZIP."
          >
            (adds document text and source files)
          </span>
        </span>
      </label>
    </div>

    <div v-if="format === 'csv'" class="mb-3 text-xs text-slate-500 dark:text-slate-400">
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
