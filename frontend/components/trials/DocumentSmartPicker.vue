<template>
  <div class="mt-4 flex-1 flex flex-col gap-4">
    <div>
      <h4 class="text-sm font-medium text-content-muted mb-2">
        {{ $t('trials.smart.load_from_trial') }}
      </h4>
      <select
        v-model="selectedTrialId"
        :class="selectClass"
        @change="emit('load-from-trial', selectedTrialId)"
      >
        <option value="">{{ $t('trials.smart.select_trial') }}</option>
        <option v-for="trial in previousTrials" :key="trial.id" :value="trial.id">
          {{
            $t('trials.smart.trial_option', {
              name: trialLabel(trial, trial.id),
              date: formatDate(trial.created_at),
              count: trial.document_ids.length,
            })
          }}
        </option>
      </select>
    </div>

    <div>
      <h4 class="text-sm font-medium text-content-muted mb-2">
        {{ $t('trials.smart.filter_by_date') }}
      </h4>
      <div class="grid grid-cols-2 gap-2">
        <input v-model="dateRange.start" :class="inputClass" type="date" />
        <input v-model="dateRange.end" :class="inputClass" type="date" />
      </div>
    </div>

    <div class="flex flex-wrap gap-2 pt-2">
      <BaseButton variant="secondary" size="sm" @click="emit('select-recent', 7)">{{
        $t('trials.smart.last_7_days')
      }}</BaseButton>
      <BaseButton variant="secondary" size="sm" @click="emit('select-recent', 30)">{{
        $t('trials.smart.last_30_days')
      }}</BaseButton>
      <BaseButton
        variant="primary"
        size="sm"
        :disabled="!dateRange.start && !dateRange.end"
        :title="$t('trials.smart.apply_title')"
        @click="emit('apply-date-range', { start: dateRange.start, end: dateRange.end })"
        >{{ $t('trials.smart.apply_range') }}</BaseButton
      >
    </div>

    <div v-if="selectedIds.length > 0" class="mt-4 p-3 bg-primary-soft rounded-card">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-primary">
          {{ $t('trials.smart.n_selected', { count: selectedIds.length }, selectedIds.length) }}
        </span>
        <div class="flex items-center gap-2">
          <BaseButton
            variant="link"
            tone="blue"
            class="text-sm flex items-center gap-1"
            @click="showSelectedDocs = !showSelectedDocs"
          >
            <span v-if="!showSelectedDocs">{{ $t('trials.smart.show') }}</span>
            <span v-else>{{ $t('trials.smart.hide') }}</span>
            <ChevronDown
              :class="{ 'rotate-180': showSelectedDocs }"
              class="w-4 h-4 transition-transform"
              aria-hidden="true"
            />
          </BaseButton>
          <BaseButton variant="link" tone="blue" class="text-sm" @click="emit('clear')">
            {{ $t('trials.smart.clear') }}
          </BaseButton>
        </div>
      </div>
      <transition name="fade">
        <div
          v-show="showSelectedDocs"
          class="mt-2 bg-surface rounded shadow p-2 max-h-40 overflow-y-auto border border-default"
        >
          <ul class="text-xs text-content space-y-1">
            <li v-for="docId in selectedIds" :key="docId">
              {{ getDocLabel(docId) }}
            </li>
          </ul>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, type PropType } from 'vue'
import { ChevronDown } from '@lucide/vue'
import { formatDate } from '@/utils/formatters'
import { trialLabel } from '@/utils/trialLabel'
import BaseButton from '@/components/common/BaseButton.vue'
import { inputClass, selectClass } from '@/utils/formStyles'
import type { TrialSummary } from '@/types'

/** A previous trial with a guaranteed non-null document_ids list (the parent
 *  only forwards completed trials that have documents). */
interface PreviousTrial extends TrialSummary {
  document_ids: number[]
}

interface DateRangePayload {
  start: string
  end: string
}

defineProps({
  previousTrials: {
    type: Array as PropType<PreviousTrial[]>,
    default: () => [],
  },
  selectedIds: {
    type: Array as PropType<number[]>,
    default: () => [],
  },
  getDocLabel: {
    type: Function as PropType<(docId: number) => string>,
    required: true,
  },
})

const emit = defineEmits<{
  'load-from-trial': [trialId: string | number]
  'select-recent': [days: number]
  'apply-date-range': [range: DateRangePayload]
  clear: []
}>()

// Local UI state (not reset by initializeForm in the original, so safe to localise)
const selectedTrialId = ref<string>('')
const dateRange = ref<DateRangePayload>({ start: '', end: '' })
const showSelectedDocs = ref(false)
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
