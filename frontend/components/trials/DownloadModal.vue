<script setup lang="ts">
import { ref, computed, watch, type PropType } from 'vue'
import { useI18n } from 'vue-i18n'
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
const includeReasoning = ref(false)
const includeUsage = ref(false)

const isDownloading = ref(false)
const toast = useToast()
const { t } = useI18n({ useScope: 'global' })

const isPartial = computed(
  () => props.trial?.status === 'failed' || props.trial?.status === 'cancelled',
)

const isJsonZip = computed(() => format.value === 'json')
const isCsvZip = computed(() => format.value === 'csv' && includeContent.value)
const isCsvOnly = computed(() => format.value === 'csv' && !includeContent.value)
const fileExt = computed(() => (isCsvOnly.value ? 'csv' : 'zip'))

// Prefer the user-set trial name (slugified) for the filename; fall back to the
// project-wise "trial_N" number so it still matches the UI when unnamed.
const downloadBasename = computed(() => {
  const name = props.trial?.name?.trim()
  if (name) {
    const slug = name
      .replace(/[^\w.-]+/g, '_')
      .replace(/^[_.]+|[_.]+$/g, '')
      .slice(0, 80)
    if (slug) return slug
  }
  return `trial_${props.trial?.project_trial_number ?? props.trial?.id}`
})

watch(
  () => props.open,
  (open) => {
    if (open) {
      format.value = 'json'
      includeContent.value = true
      includeReasoning.value = false
      includeUsage.value = false
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
          include_reasoning: includeReasoning.value,
          include_usage: includeUsage.value,
        }),
      `${downloadBasename.value}_results.${fileExt.value}`,
    )
    toast.success(t('trials.download.toast.downloaded'))
    emit('close')
  } catch {
    toast.error(t('trials.download.toast.failed'))
  } finally {
    isDownloading.value = false
  }
}
</script>

<template>
  <BaseModal
    :open="open"
    :title="$t('trials.download.title')"
    size="md"
    body-class="p-6"
    @close="$emit('close')"
  >
    <Callout v-if="isPartial" variant="warning" class="mb-4 text-xs">
      {{ $t('trials.download.partial_note', { count: trial?.results_count }) }}
    </Callout>

    <Callout variant="gray" class="mb-4 text-xs">
      <span v-if="isJsonZip" v-html="$t('trials.download.format_json_zip')"></span>
      <span v-else-if="isCsvZip" v-html="$t('trials.download.format_csv_zip')"></span>
      <span v-else v-html="$t('trials.download.format_csv_flat')"></span>
    </Callout>

    <div class="mb-4">
      <label :class="labelClass" for="download-format">{{
        $t('trials.download.format_label')
      }}</label>
      <select id="download-format" v-model="format" :class="selectClass">
        <option value="json">{{ $t('trials.download.format_json_option') }}</option>
        <option value="csv">{{ $t('trials.download.format_csv_option') }}</option>
      </select>
    </div>

    <div class="mb-4">
      <label :class="labelClass">{{ $t('trials.download.options_label') }}</label>
      <label class="flex items-center text-sm text-content-muted">
        <input v-model="includeContent" type="checkbox" :class="checkboxClass" />
        <span class="ml-2"
          >{{ $t('trials.download.include_content') }}
          <span class="text-content-subtle" :title="$t('trials.download.include_content_title')">
            {{ $t('trials.download.include_content_hint') }}
          </span>
        </span>
      </label>
      <label class="mt-2 flex items-center text-sm text-content-muted">
        <input v-model="includeReasoning" type="checkbox" :class="checkboxClass" />
        <span class="ml-2"
          >{{ $t('trials.download.include_reasoning') }}
          <span class="text-content-subtle" :title="$t('trials.download.include_reasoning_title')">
            {{ $t('trials.download.include_reasoning_hint') }}
          </span>
        </span>
      </label>
      <label class="mt-2 flex items-center text-sm text-content-muted">
        <input v-model="includeUsage" type="checkbox" :class="checkboxClass" />
        <span class="ml-2"
          >{{ $t('trials.download.include_usage') }}
          <span class="text-content-subtle" :title="$t('trials.download.include_usage_title')">
            {{ $t('trials.download.include_usage_hint') }}
          </span>
        </span>
      </label>
    </div>

    <div class="mb-3 text-xs text-content-muted">
      <template v-if="format === 'csv'">
        <span v-if="includeContent" v-html="$t('trials.download.note_csv_content')"></span>
        <span v-else>{{ $t('trials.download.note_csv_only') }}</span>
      </template>
      <template v-else>
        <span v-if="includeContent" v-html="$t('trials.download.note_json_content')"></span>
        <span v-else>{{ $t('trials.download.note_json_only') }}</span>
      </template>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">{{
        $t('trials.download.cancel')
      }}</BaseButton>
      <BaseButton variant="primary" :loading="isDownloading" @click="download">{{
        isDownloading ? $t('trials.download.downloading') : $t('trials.download.download')
      }}</BaseButton>
    </template>
  </BaseModal>
</template>
