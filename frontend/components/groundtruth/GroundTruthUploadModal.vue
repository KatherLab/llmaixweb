<template>
  <BaseModal :open="open" title="Upload Ground Truth" size="md" @close="$emit('close')">
    <form @submit.prevent="uploadGroundTruth">
      <div class="space-y-4">
        <div>
          <label for="ground-truth-name" :class="labelClass">Name (optional)</label>
          <input
            id="ground-truth-name"
            v-model="groundTruthName"
            type="text"
            :class="inputClass"
            maxlength="100"
            placeholder="Ground truth file name"
          />
        </div>
        <div>
          <label for="ground-truth-format" :class="labelClass">Format</label>
          <select id="ground-truth-format" v-model="groundTruthFormat" :class="selectClass">
            <option value="csv">CSV (flattened fields with dots)</option>
            <option value="json">JSON (single file with document map or multiple files)</option>
            <option value="zip">ZIP (multiple JSON files)</option>
            <option value="xlsx">Excel (.xlsx, dot-paths build nesting)</option>
          </select>
        </div>

        <!-- Format-specific guidance -->
        <Callout
          v-if="groundTruthFormat === 'json' || groundTruthFormat === 'zip'"
          variant="info"
          class="mt-2"
        >
          <p class="text-sm">
            <strong>Important:</strong> Each document must have an 'id' field that matches your
            document identifiers.
          </p>
        </Callout>
        <Callout
          v-else-if="groundTruthFormat === 'csv' || groundTruthFormat === 'xlsx'"
          variant="info"
          class="mt-2"
        >
          <p class="text-sm">
            You'll choose the ID column (matching your document identifiers) on the next step.
          </p>
        </Callout>

        <div>
          <label for="file-upload" :class="labelClass">File(s)</label>
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
                  <span>Upload file(s)</span>
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
                <p class="pl-1">or drag and drop</p>
              </div>
              <p class="text-xs text-content-muted">
                <template v-if="groundTruthFormat === 'csv'"
                  >CSV file with flattened fields (dots for nesting)</template
                >
                <template v-else-if="groundTruthFormat === 'json'"
                  >JSON file(s) - single file or multiple files</template
                >
                <template v-else-if="groundTruthFormat === 'zip'"
                  >ZIP file containing JSON files</template
                >
              </p>
            </div>
          </div>
          <div v-if="selectedFiles.length > 0" class="mt-2">
            <p class="text-sm font-medium text-content-muted mb-1">Selected files:</p>
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
                  aria-label="Remove file"
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
        <BaseButton type="button" variant="secondary" @click="$emit('close')"> Cancel </BaseButton>
        <BaseButton
          type="submit"
          :disabled="isUploading || selectedFiles.length === 0"
          :loading="isUploading"
        >
          <span v-if="isUploading">Uploading...</span>
          <span v-else>Upload</span>
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
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

const handleFileDrop = (event: DragEvent) => {
  const files = Array.from(event.dataTransfer?.files ?? [])
  if (groundTruthFormat.value === 'json') {
    const jsonFiles = files.filter((f) => f.name.toLowerCase().endsWith('.json'))
    selectedFiles.value = jsonFiles
    if (jsonFiles.length === 0 && files.length > 0) {
      toast.warning('Only .json files are accepted for the JSON format.')
    }
  } else {
    // CSV / ZIP / XLSX are single-file
    const allowed = ['.csv', '.zip', '.xlsx', '.xls']
    const picked = files.find((f) => allowed.some((ext) => f.name.toLowerCase().endsWith(ext)))
    selectedFiles.value = picked ? [picked] : []
    if (!picked && files.length > 0) {
      toast.warning(
        `No file matching the ${groundTruthFormat.value.toUpperCase()} format was found in the drop.`,
      )
    }
  }
}

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}

const uploadGroundTruth = async () => {
  if (selectedFiles.value.length === 0) {
    toast.warning('Please select at least one file to upload')
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
      formData.append('name', groundTruthName.value || 'JSON Ground Truth')
      formData.append('format', 'zip')

      response = await groundtruthApi.upload(props.projectId, formData)
    } else {
      const firstFile = selectedFiles.value[0]
      if (!firstFile) {
        toast.error('No file selected')
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
    toast.error(`Failed to upload ground truth: ${errorMessage}`)
    console.error(err)
  } finally {
    isUploading.value = false
  }
}
</script>
