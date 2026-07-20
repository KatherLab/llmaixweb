<template>
  <BaseModal :open="open" :title="$t('groundtruth.upload.title')" size="md" @close="$emit('close')">
    <form @submit.prevent="uploadGroundTruth">
      <div class="space-y-4">
        <div>
          <label for="ground-truth-name" :class="labelClass">{{
            $t('groundtruth.upload.name_label')
          }}</label>
          <input
            id="ground-truth-name"
            v-model="groundTruthName"
            type="text"
            :class="inputClass"
            maxlength="100"
            :placeholder="$t('groundtruth.upload.name_placeholder')"
          />
        </div>
        <div>
          <label for="ground-truth-format" :class="labelClass">{{
            $t('groundtruth.upload.format_label')
          }}</label>
          <select id="ground-truth-format" v-model="groundTruthFormat" :class="selectClass">
            <option value="csv">{{ $t('groundtruth.upload.format_csv') }}</option>
            <option value="json">{{ $t('groundtruth.upload.format_json') }}</option>
            <option value="zip">{{ $t('groundtruth.upload.format_zip') }}</option>
            <option value="xlsx">{{ $t('groundtruth.upload.format_xlsx') }}</option>
          </select>
        </div>

        <!-- Format-specific guidance -->
        <Callout
          v-if="groundTruthFormat === 'json' || groundTruthFormat === 'zip'"
          variant="info"
          class="mt-2"
        >
          <p class="text-sm">
            <strong>{{ $t('groundtruth.upload.important') }}</strong>
            {{ $t('groundtruth.upload.json_id_note') }}
          </p>
        </Callout>
        <Callout
          v-else-if="groundTruthFormat === 'csv' || groundTruthFormat === 'xlsx'"
          variant="info"
          class="mt-2"
        >
          <p class="text-sm">
            {{ $t('groundtruth.upload.tabular_id_note') }}
          </p>
        </Callout>

        <div>
          <label for="file-upload" :class="labelClass">{{
            $t('groundtruth.upload.files_label')
          }}</label>
          <div
            class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-strong border-dashed rounded-card"
            @dragover.prevent
            @drop.prevent="handleFileDrop"
          >
            <div class="space-y-1 text-center">
              <ImageIcon class="mx-auto h-12 w-12 text-content-subtle" />
              <div class="flex text-sm text-content-muted justify-center">
                <label
                  for="file-upload"
                  class="relative cursor-pointer bg-surface rounded-card font-medium text-primary hover:text-primary focus-within:outline-none"
                >
                  <span>{{ $t('groundtruth.upload.upload_files') }}</span>
                  <input
                    id="file-upload"
                    name="file-upload"
                    type="file"
                    class="sr-only"
                    :accept="acceptedFileTypes"
                    :multiple="groundTruthFormat === 'json'"
                    @change="handleFileSelect"
                  />
                </label>
                <p class="pl-1">{{ $t('groundtruth.upload.or_drag_and_drop') }}</p>
              </div>
              <p class="text-xs text-content-muted">
                <template v-if="groundTruthFormat === 'csv'">{{
                  $t('groundtruth.upload.hint_csv')
                }}</template>
                <template v-else-if="groundTruthFormat === 'json'">{{
                  $t('groundtruth.upload.hint_json')
                }}</template>
                <template v-else-if="groundTruthFormat === 'zip'">{{
                  $t('groundtruth.upload.hint_zip')
                }}</template>
                <template v-else-if="groundTruthFormat === 'xlsx'">{{
                  $t('groundtruth.upload.hint_xlsx')
                }}</template>
              </p>
            </div>
          </div>
          <div v-if="selectedFiles.length > 0" class="mt-2">
            <p class="text-sm font-medium text-content-muted mb-1">
              {{ $t('groundtruth.upload.selected_files') }}
            </p>
            <ul class="text-sm text-content-muted space-y-1">
              <li
                v-for="(file, index) in selectedFiles"
                :key="index"
                class="flex items-center justify-between"
              >
                <span>{{ file.name }}</span>
                <BaseButton
                  v-if="groundTruthFormat === 'json' && selectedFiles.length > 1"
                  variant="link"
                  tone="red"
                  :aria-label="$t('groundtruth.upload.remove_file')"
                  @click="removeFile(index)"
                >
                  <X class="h-4 w-4" aria-hidden="true" />
                </BaseButton>
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div class="mt-6 flex justify-end space-x-3">
        <BaseButton type="button" variant="secondary" @click="$emit('close')">
          {{ $t('groundtruth.upload.cancel') }}
        </BaseButton>
        <BaseButton
          type="submit"
          :disabled="isUploading || selectedFiles.length === 0"
          :loading="isUploading"
        >
          <span v-if="isUploading">{{ $t('groundtruth.upload.uploading') }}</span>
          <span v-else>{{ $t('groundtruth.upload.upload') }}</span>
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ImageIcon, X } from '@lucide/vue'
import { groundtruthApi } from '@/services/groundtruthApi'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'
import { extractErrorMessage } from '@/utils/errors'
import type { GroundTruth } from '@/types'

interface Props {
  open: boolean
  projectId: string | number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  uploaded: [groundTruth: GroundTruth]
}>()

const { t } = useI18n({ useScope: 'global' })
const toast = useToast()

const groundTruthName = ref('')
const groundTruthFormat = ref('csv')
const selectedFiles = ref<File[]>([])
const isUploading = ref(false)

// Reset transient form state whenever the modal is closed so a reopen starts fresh
// (component stays mounted to enable the close transition).
watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      groundTruthName.value = ''
      groundTruthFormat.value = 'csv'
      selectedFiles.value = []
      isUploading.value = false
    }
  },
)

const acceptedFileTypes = computed(() => {
  switch (groundTruthFormat.value) {
    case 'json':
      return '.json'
    case 'zip':
      return '.zip'
    case 'csv':
      return '.csv'
    case 'xlsx':
      return '.xlsx,.xls'
    default:
      return '.csv,.json,.zip,.xlsx,.xls'
  }
})

const handleFileSelect = (event: Event) => {
  const files = Array.from((event.target as HTMLInputElement).files ?? [])
  if (groundTruthFormat.value === 'json') {
    // For JSON, allow multiple files
    selectedFiles.value = files
  } else {
    // For CSV and ZIP, only allow single file
    selectedFiles.value = files.slice(0, 1)
  }
}

/** Ground-truth format implied by a filename extension (null = unsupported). */
const formatForExtension = (name: string): string | null => {
  const n = name.toLowerCase()
  if (n.endsWith('.csv')) return 'csv'
  if (n.endsWith('.xlsx') || n.endsWith('.xls')) return 'xlsx'
  if (n.endsWith('.zip')) return 'zip'
  if (n.endsWith('.json')) return 'json'
  return null
}

const handleFileDrop = (event: DragEvent) => {
  const files = Array.from(event.dataTransfer?.files ?? [])
  if (files.length === 0) return

  // Multiple JSON files → the JSON format supports multi-file uploads.
  const jsonFiles = files.filter((f) => formatForExtension(f.name) === 'json')
  if (files.length > 1 && jsonFiles.length === files.length) {
    if (groundTruthFormat.value !== 'json') {
      groundTruthFormat.value = 'json'
      toast.info(t('groundtruth.upload.toast_switched_json'))
    }
    selectedFiles.value = jsonFiles
    return
  }

  // Multiple mixed / non-JSON files → ambiguous.
  if (files.length > 1) {
    toast.warning(t('groundtruth.upload.toast_drop_single'))
    return
  }

  const file = files[0]!
  const fmt = formatForExtension(file.name)
  if (!fmt) {
    toast.warning(t('groundtruth.upload.toast_unsupported_type', { name: file.name }))
    return
  }
  // Auto-switch the format so the file isn't uploaded under the wrong one
  // (e.g. a .zip dropped while CSV is selected would fail server-side).
  if (fmt !== groundTruthFormat.value) {
    groundTruthFormat.value = fmt
    toast.info(t('groundtruth.upload.toast_switched_format', { format: fmt.toUpperCase() }))
  }
  selectedFiles.value = [file]
}

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}

const uploadGroundTruth = async () => {
  if (selectedFiles.value.length === 0) {
    toast.warning(t('groundtruth.upload.toast_select_file'))
    return
  }

  isUploading.value = true

  try {
    let response

    if (groundTruthFormat.value === 'json' && selectedFiles.value.length > 1) {
      const { default: JSZip } = await import('jszip')
      const zip = new JSZip()

      for (const file of selectedFiles.value) {
        const content = await file.text()
        zip.file(file.name, content)
      }

      const zipBlob = await zip.generateAsync({ type: 'blob' })
      const zipFile = new File([zipBlob], 'ground_truth.zip', { type: 'application/zip' })

      const formData = new FormData()
      formData.append('file', zipFile)
      formData.append('name', groundTruthName.value || t('groundtruth.upload.default_json_name'))
      formData.append('format', 'zip')

      response = await groundtruthApi.upload(props.projectId, formData)
    } else {
      const firstFile = selectedFiles.value[0]
      if (!firstFile) {
        toast.error(t('groundtruth.upload.toast_no_file'))
        return
      }
      const formData = new FormData()
      formData.append('file', firstFile)
      formData.append('name', groundTruthName.value || firstFile.name)
      formData.append('format', groundTruthFormat.value)

      response = await groundtruthApi.upload(props.projectId, formData)
    }

    emit('uploaded', response.data)
    // Success toast is shown by the parent (onGroundTruthUploaded) — don't
    // double-fire here.
  } catch (err) {
    const errorMessage = extractErrorMessage(err)
    toast.error(t('groundtruth.upload.toast_upload_failed', { error: errorMessage }))
    console.error(err)
  } finally {
    isUploading.value = false
  }
}
</script>
