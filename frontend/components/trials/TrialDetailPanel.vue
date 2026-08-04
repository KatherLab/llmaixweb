<template>
  <div class="p-4 space-y-3">
    <!-- Description -->
    <div v-if="trial.description" class="text-sm text-content-muted">
      {{ trial.description }}
    </div>

    <!-- Metadata -->
    <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-content-muted">
      <span class="inline-flex items-center gap-1">
        <strong class="text-content-muted">{{ $t('trials.detail.schema_label') }}</strong>
        <button
          type="button"
          class="text-primary hover:underline cursor-pointer"
          :title="$t('trials.detail.view_schema_title')"
          @click.stop="emit('view-schema', trial)"
        >
          {{ schemaName }}
        </button>
      </span>
      <span v-if="promptName" class="inline-flex items-center gap-1">
        <strong class="text-content-muted">{{ $t('trials.detail.prompt_label') }}</strong>
        <button
          type="button"
          class="text-primary hover:underline cursor-pointer"
          :title="$t('trials.detail.view_prompt_title')"
          @click.stop="emit('view-prompt', trial)"
        >
          {{ promptName }}
        </button>
      </span>
      <span
        ><strong class="text-content-muted">{{ $t('trials.detail.llm_label') }}</strong>
        {{ trial.llm_model }}</span
      >
      <span
        ><strong class="text-content-muted">{{ $t('trials.detail.started_label') }}</strong>
        {{ formatDateFull(trial.created_at) }}</span
      >
      <span v-if="trial.last_result_at"
        ><strong class="text-content-muted">{{ $t('trials.detail.last_result_label') }}</strong>
        {{ formatDateFull(trial.last_result_at) }}</span
      >
      <span v-if="trial.documents_count != null"
        ><strong class="text-content-muted">{{ $t('trials.detail.docs_label') }}</strong>
        {{ trial.documents_count }}</span
      >
    </div>

    <!-- Progress (active) -->
    <div v-if="isActive" class="flex flex-col gap-1">
      <div class="flex items-center gap-2 text-xs" aria-live="polite">
        <span class="font-medium text-primary">{{
          $t('trials.detail.docs_progress', { done: docsDone, total: totalDocs })
        }}</span>
        <span class="text-content-muted">{{
          $t('trials.detail.elapsed', { duration: formatDuration(elapsedSeconds) })
        }}</span>
        <span v-if="etaSeconds && etaSeconds > 0" class="text-content-muted">{{
          $t('trials.detail.eta', { duration: formatDuration(etaSeconds) })
        }}</span>
      </div>
      <div
        class="w-full h-1 bg-surface-sunken rounded-full overflow-hidden"
        role="progressbar"
        :aria-label="$t('trials.detail.progress_aria')"
        :aria-valuenow="progressPercent"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <div
          class="h-full bg-primary transition-all duration-500"
          :style="{ width: progressPercent + '%' }"
        ></div>
      </div>
    </div>

    <!-- End states -->
    <div
      v-else-if="trial.status === 'completed'"
      class="flex items-center gap-2 text-green-600 dark:text-green-400 font-medium text-xs"
    >
      <CircleCheckBig class="w-4 h-4" />
      {{ $t('trials.detail.results_ready') }}
    </div>
    <div
      v-else-if="trial.status === 'failed'"
      class="flex items-center gap-2 text-red-600 dark:text-red-400 text-xs font-medium"
    >
      <AlertCircle class="w-4 h-4" />
      {{ $t('trials.detail.failed_details') }}
    </div>

    <!-- Actions -->
    <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-default">
      <div class="flex gap-2 flex-wrap">
        <BaseButton
          v-if="isActive && trial.status !== 'cancelled'"
          variant="warning"
          size="sm"
          @click.stop="emit('cancel', trial)"
        >
          {{ $t('trials.detail.cancel') }}
        </BaseButton>
        <BaseButton variant="primary" size="sm" @click.stop="emit('view-results', trial)">
          {{ $t('trials.detail.results') }}
        </BaseButton>
        <BaseButton
          v-if="canDownload"
          variant="secondary"
          size="sm"
          :title="
            trial.status === 'completed' ? undefined : $t('trials.detail.download_partial_title')
          "
          @click.stop="emit('download', trial)"
        >
          <Download class="w-4 h-4" />
          {{
            trial.status === 'completed'
              ? $t('trials.detail.download')
              : $t('trials.detail.download_partial')
          }}
        </BaseButton>
      </div>
      <!-- Secondary actions collapsed into an overflow menu -->
      <div ref="menuContainer" class="relative" @keydown.escape="menuOpen = false">
        <BaseButton
          variant="ghost"
          size="sm"
          :aria-label="$t('trials.detail.more_actions')"
          :aria-expanded="menuOpen"
          aria-haspopup="true"
          @click.stop="menuOpen = !menuOpen"
        >
          <EllipsisVertical class="w-4 h-4" />
        </BaseButton>
        <transition name="fade-slide">
          <div
            v-if="menuOpen"
            class="absolute right-0 mt-2 w-40 rounded-modal shadow-xl bg-surface ring-1 ring-default-border z-50 py-1"
            role="menu"
          >
            <button
              type="button"
              role="menuitem"
              class="w-full text-left px-4 py-2 text-sm font-medium text-content-muted hover:bg-primary-soft hover:text-primary transition-colors"
              @click.stop="menuAction('retry')"
            >
              {{ $t('trials.detail.retry') }}
            </button>
            <button
              type="button"
              role="menuitem"
              class="w-full text-left px-4 py-2 text-sm font-medium text-content-muted hover:bg-primary-soft hover:text-primary transition-colors"
              @click.stop="menuAction('rename')"
            >
              {{ $t('trials.detail.rename') }}
            </button>
            <button
              type="button"
              role="menuitem"
              class="w-full text-left px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              @click.stop="menuAction('delete')"
            >
              {{ $t('trials.detail.delete') }}
            </button>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, type PropType } from 'vue'
import { AlertCircle, CircleCheckBig, Download, EllipsisVertical } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { useClickOutside } from '@/composables/useClickOutside'
import { formatDuration, formatDateFull } from '@/utils/formatters'
import type { TrialSummary, Schema, Prompt } from '@/types'

const props = defineProps({
  trial: { type: Object as PropType<TrialSummary>, required: true },
  schemas: { type: Array as PropType<Schema[]>, required: true },
  prompts: { type: Array as PropType<Prompt[]>, required: true },
})

const emit = defineEmits<{
  rename: [trial: TrialSummary]
  delete: [trial: TrialSummary]
  retry: [trial: TrialSummary]
  download: [trial: TrialSummary]
  'view-results': [trial: TrialSummary]
  'view-schema': [trial: TrialSummary]
  'view-prompt': [trial: TrialSummary]
  cancel: [trial: TrialSummary]
}>()

const schema = computed(() => props.schemas.find((s) => s.id === props.trial.schema_id))
const prompt = computed(() => props.prompts.find((p) => p.id === props.trial.prompt_id))
// Prefer the name frozen in the trial snapshot (matches what actually ran);
// fall back to the live schema/prompt name for legacy trials without snapshots.
const schemaName = computed(
  () => props.trial.schema_snapshot?.schema_name || schema.value?.schema_name || '-',
)
const promptName = computed(() => props.trial.prompt_snapshot?.name || prompt.value?.name)

const isActive = computed(() => !['completed', 'failed', 'cancelled'].includes(props.trial.status))

// Overflow ("⋯") menu for the secondary actions (Retry / Rename / Delete).
const menuOpen = ref(false)
const menuContainer = ref<HTMLElement | null>(null)
useClickOutside(menuContainer, () => {
  menuOpen.value = false
})
function menuAction(action: 'retry' | 'rename' | 'delete'): void {
  menuOpen.value = false
  if (action === 'retry') emit('retry', props.trial)
  else if (action === 'rename') emit('rename', props.trial)
  else emit('delete', props.trial)
}

// Completed trials are always downloadable. Failed/cancelled trials are downloadable
// too when some documents finished — the archive contains only the successful results.
const canDownload = computed(
  () =>
    props.trial.status === 'completed' ||
    (['failed', 'cancelled'].includes(props.trial.status) && (props.trial.results_count ?? 0) > 0),
)

// document_ids is null/empty for set-based trials — fall back to the
// server-computed documents_count so the progress label isn't "0/0".
const totalDocs = computed(
  () => props.trial.document_ids?.length || props.trial.documents_count || 0,
)
const docsDone = computed(() => {
  if (props.trial.docs_done != null) return props.trial.docs_done
  if (props.trial.progress != null) {
    return Math.round((props.trial.progress || 0) * totalDocs.value)
  }
  return 0
})
const progressPercent = computed(() =>
  props.trial.progress != null ? Math.round((props.trial.progress || 0) * 100) : 0,
)

const elapsedSeconds = computed(() =>
  props.trial.started_at ? (Date.now() - Date.parse(props.trial.started_at)) / 1000 : 0,
)
const etaSeconds = computed(() => props.trial.meta?.eta_seconds ?? 0)
</script>

<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity 0.15s,
    transform 0.15s;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}
</style>
