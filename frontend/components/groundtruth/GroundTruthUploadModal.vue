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
            placeholder="Ground truth file name"
          />
        </div>
        <div>
          <label for="ground-truth-format" :class="labelClass">Format</label>
          <select id="ground-truth-format" v-model="groundTruthFormat" :class="selectClass">
            <option value="csv">CSV (flattened fields with dots)</option>
            <option value="json">JSON (single file with document map or multiple files)</option>
            <option value="zip">ZIP (multiple JSON files)</option>
            +
            <option value="xlsx">Excel (.xlsx, dot-paths build nesting)</option>
          </select>
        </div>

        <!-- Add info box for JSON -->
        <div
          v-if="groundTruthFormat === 'json' || groundTruthFormat === 'zip'"
          class="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md"
        >
          <p class="text-sm text-blue-700">
            <strong>Important:</strong> Each document must have an 'id' field that matches your
            document identifiers.
          </p>
        </div>

        <div>
          <label for="file-upload" :class="labelClass">File(s)</label>
          <div
            class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-slate-300 border-dashed rounded-md"
            @dragover.prevent
            @drop.prevent="handleFileDrop"
          >
            <div class="space-y-1 text-center">
              <ImageIcon class="mx-auto h-12 w-12 text-slate-400" />
              <div class="flex text-sm text-slate-600 justify-center">
                <label
                  for="file-upload"
                  class="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none"
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
              <p class="text-xs text-slate-500">
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
            <p class="text-sm font-medium text-slate-700 mb-1">Selected files:</p>
            <ul class="text-sm text-slate-600 space-y-1">
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

<script setup>
import { ref, computed, watch } from 'vue'
import { ImageIcon, X } from '@lucide/vue'
import { groundtruthApi } from '@/services/groundtruthApi'
import { useToast } from 'vue-toastification'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: [String, Number],
    required: true,
  },
})

const emit = defineEmits(['close', 'uploaded'])
const toast = useToast()

const groundTruthName = ref('')
const groundTruthFormat = ref('csv')
const selectedFiles = ref([])
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

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  if (groundTruthFormat.value === 'json') {
    // For JSON, allow multiple files
    selectedFiles.value = files
  } else {
    // For CSV and ZIP, only allow single file
    selectedFiles.value = files.slice(0, 1)
  }
}

const handleFileDrop = (event) => {
  const files = Array.from(event.dataTransfer.files)
  if (groundTruthFormat.value === 'json') {
    selectedFiles.value = files.filter((f) => f.name.endsWith('.json'))
  } else {
    // CSV / ZIP / XLSX are single-file
    const allowed = ['.csv', '.zip', '.xlsx', '.xls']
    const picked = files.find((f) => allowed.some((ext) => f.name.toLowerCase().endsWith(ext)))
    selectedFiles.value = picked ? [picked] : []
  }
}

const removeFile = (index) => {
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
      const formData = new FormData()
      formData.append('file', selectedFiles.value[0])
      formData.append('name', groundTruthName.value || selectedFiles.value[0].name)
      formData.append('format', groundTruthFormat.value)

      response = await groundtruthApi.upload(props.projectId, formData)
    }

    emit('uploaded', response.data)
    toast.success('Ground truth uploaded successfully')
  } catch (err) {
    const errorMessage = extractErrorMessage(err)
    toast.error(`Failed to upload ground truth: ${errorMessage}`)
    console.error(err)
  } finally {
    isUploading.value = false
  }
}
</script>
