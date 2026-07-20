<template>
  <BaseModal :open="open" size="xl" @close="emitClose">
    <template #header>
      <div>
        <h3 class="text-lg font-semibold text-content">{{ $t('groundtruth.manager.title') }}</h3>
        <p class="mt-1 text-sm text-content-muted">
          {{ $t('groundtruth.manager.subtitle') }}
        </p>
      </div>
    </template>

    <!-- BODY: Files List -->
    <EmptyState
      v-if="groundTruthFiles.length === 0"
      :title="$t('groundtruth.manager.empty_title')"
      :description="$t('groundtruth.manager.empty_description')"
    />

    <div v-else class="space-y-4">
      <div
        v-for="(gt, index) in groundTruthFiles"
        :key="gt.id"
        class="bg-surface border border-default rounded-card p-4 hover:shadow-md transition-shadow"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h4 class="font-medium text-content">
                {{ gt.name || $t('groundtruth.manager.default_name', { number: index + 1 }) }}
              </h4>
              <StatusBadge color="blue" class="px-2 py-1 font-medium">{{
                gt.format?.toUpperCase()
              }}</StatusBadge>
              <StatusBadge
                v-if="gt.field_mappings?.length"
                color="green"
                class="px-2 py-1 font-medium"
                >{{
                  $t(
                    'groundtruth.manager.mappings_count',
                    { count: gt.field_mappings.length },
                    gt.field_mappings.length,
                  )
                }}</StatusBadge
              >
            </div>
            <div class="text-xs text-content-muted flex flex-wrap gap-4">
              <span>{{
                $t('groundtruth.manager.created', { date: formatDate(gt.created_at) })
              }}</span>
              <span v-if="gt.updated_at !== gt.created_at">
                {{ $t('groundtruth.manager.updated', { date: formatDate(gt.updated_at) }) }}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <!-- Configure mappings -->
            <button
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary hover:text-primary hover:bg-primary-soft rounded-card transition-colors"
              :title="$t('groundtruth.manager.configure_mappings')"
              @click="previewGroundTruth(gt)"
            >
              <Settings class="w-4 h-4" />
              {{ $t('groundtruth.manager.configure_mappings') }}
            </button>
            <!-- Rename (pencil) -->
            <button
              class="p-2 text-content-muted hover:text-content hover:bg-surface-muted rounded-card transition-colors"
              :title="$t('groundtruth.manager.rename')"
              :aria-label="
                $t('groundtruth.manager.rename_aria', {
                  name: gt.name || $t('groundtruth.manager.fallback_file'),
                })
              "
              @click="editGroundTruth(gt)"
            >
              <Pencil class="w-5 h-5" aria-hidden="true" />
            </button>
            <!-- Delete (trash) -->
            <button
              class="p-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-card transition-colors"
              :title="$t('groundtruth.manager.delete')"
              :aria-label="
                $t('groundtruth.manager.delete_aria', {
                  name: gt.name || $t('groundtruth.manager.fallback_file'),
                })
              "
              @click="deleteGroundTruth(gt)"
            >
              <Trash2 class="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>
        <!-- Field mappings preview -->
        <div v-if="gt.field_mappings?.length" class="mt-3 pt-3 border-t border-default">
          <h5 class="text-xs font-medium text-content-muted mb-1">
            {{ $t('groundtruth.manager.configured_field_mappings') }}
          </h5>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div
              v-for="mapping in gt.field_mappings.slice(0, 6)"
              :key="mapping.id"
              class="bg-surface-sunken px-2 py-1 rounded-card flex justify-between"
            >
              <span class="font-mono text-primary">{{ mapping.schema_field }}</span>
              <span class="text-content-muted">→ {{ mapping.ground_truth_field }}</span>
            </div>
            <div
              v-if="gt.field_mappings.length > 6"
              class="bg-surface-sunken px-2 py-1 rounded-card text-center text-content-muted"
            >
              {{ $t('groundtruth.manager.more_count', { count: gt.field_mappings.length - 6 }) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <BaseButton @click="emitClose">{{ $t('groundtruth.manager.close') }}</BaseButton>
    </template>
  </BaseModal>

  <!-- Edit Modal -->
  <BaseModal
    :open="!!editingGroundTruth"
    :title="$t('groundtruth.manager.rename_title')"
    size="sm"
    @close="cancelEdit"
  >
    <label for="edit-name" :class="labelClass">{{ $t('groundtruth.manager.name_label') }}</label>
    <input
      id="edit-name"
      v-model="editName"
      type="text"
      :class="inputClass"
      maxlength="100"
      :placeholder="$t('groundtruth.manager.name_placeholder')"
    />
    <template #footer>
      <BaseButton variant="secondary" @click="cancelEdit">{{
        $t('groundtruth.manager.cancel')
      }}</BaseButton>
      <BaseButton :disabled="isSaving" :loading="isSaving" @click="saveEdit">
        <span v-if="isSaving">{{ $t('groundtruth.manager.saving') }}</span>
        <span v-else>{{ $t('groundtruth.manager.save') }}</span>
      </BaseButton>
    </template>
  </BaseModal>

  <!-- Preview Modal (GroundTruthPreviewModal) -->
  <GroundTruthPreviewModal
    :open="showPreview"
    :project-id="projectId"
    :ground-truth="previewingGroundTruth"
    @close="closePreview"
    @configured="onMappingConfigured"
  />

  <!-- Delete ground truth confirmation -->
  <ConfirmationDialog
    :open="showDeleteConfirm"
    :title="$t('groundtruth.manager.delete_confirm_title')"
    :message="
      $t('groundtruth.manager.delete_confirm_message', {
        name: pendingDelete?.name || $t('groundtruth.manager.this_file'),
      })
    "
    :confirm-text="$t('groundtruth.manager.delete')"
    :cancel-text="$t('groundtruth.manager.cancel')"
    confirm-variant="danger"
    @confirm="confirmDelete"
    @cancel="showDeleteConfirm = false"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pencil, Settings, Trash2 } from '@lucide/vue'
import { groundtruthApi } from '@/services/groundtruthApi'
import { formatDate } from '@/utils/formatters'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, labelClass } from '@/utils/formStyles'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import GroundTruthPreviewModal from './GroundTruthPreviewModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { GroundTruth } from '@/types'

interface Props {
  projectId: string | number
  groundTruthFiles: GroundTruth[]
  open: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: []; updated: [] }>()

const { t } = useI18n({ useScope: 'global' })
const toast = useToast()
const editingGroundTruth = ref<GroundTruth | null>(null)
const previewingGroundTruth = ref<GroundTruth | null>(null)
const showPreview = ref(false)
const editName = ref('')
const isSaving = ref(false)

// Modal close handler
function emitClose() {
  emit('close')
}

// Edit ground truth
function editGroundTruth(gt: GroundTruth) {
  editingGroundTruth.value = gt
  editName.value = gt.name || ''
}
function cancelEdit() {
  editingGroundTruth.value = null
  editName.value = ''
}
async function saveEdit() {
  if (!editingGroundTruth.value) return
  isSaving.value = true
  try {
    const formData = new FormData()
    formData.append('name', editName.value)

    await groundtruthApi.update(props.projectId, editingGroundTruth.value.id, formData)
    toast.success(t('groundtruth.manager.toast_updated'))
    emit('updated')
    cancelEdit()
  } catch (err) {
    toast.error(extractErrorMessage(err, t('groundtruth.manager.toast_update_failed')))
    console.error(err)
  } finally {
    isSaving.value = false
  }
}

// Preview ground truth
function previewGroundTruth(gt: GroundTruth) {
  previewingGroundTruth.value = gt
  showPreview.value = true
}
function closePreview() {
  showPreview.value = false
}

// Delete ground truth (confirmed via ConfirmationDialog)
const showDeleteConfirm = ref(false)
const pendingDelete = ref<GroundTruth | null>(null)
function deleteGroundTruth(gt: GroundTruth) {
  pendingDelete.value = gt
  showDeleteConfirm.value = true
}
async function confirmDelete() {
  const gt = pendingDelete.value
  showDeleteConfirm.value = false
  pendingDelete.value = null
  if (!gt) return
  try {
    await groundtruthApi.delete(props.projectId, gt.id)
    toast.success(t('groundtruth.manager.toast_deleted'))
    emit('updated')
  } catch (err) {
    toast.error(extractErrorMessage(err, t('groundtruth.manager.toast_delete_failed')))
    console.error(err)
  }
}

// Handle mapping configuration
function onMappingConfigured() {
  showPreview.value = false
  emit('updated')
  toast.success(t('groundtruth.manager.toast_mappings_configured'))
}
</script>
