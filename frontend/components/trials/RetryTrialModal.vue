<template>
  <BaseModal :open="open" size="sm" body-class="p-6" @close="$emit('close')">
    <template #header>
      <h3 class="text-lg font-semibold text-content">{{ $t('trials.retry_modal.title') }}</h3>
    </template>

    <p class="text-sm text-content-muted">
      {{ $t('trials.retry_modal.message') }}
    </p>

    <div class="mt-4 space-y-3">
      <label class="flex items-start gap-2 text-sm cursor-pointer">
        <input v-model="scope" type="radio" value="failed" :class="[radioClass, 'mt-0.5']" />
        <span>
          <span class="font-medium text-content">
            {{ $t('trials.retry_modal.failed_only') }}{{ failedCount ? ` (${failedCount})` : '' }}
          </span>
          <span class="block text-xs text-content-muted mt-0.5">
            {{ $t('trials.retry_modal.failed_only_desc') }}
          </span>
        </span>
      </label>
      <label class="flex items-start gap-2 text-sm cursor-pointer">
        <input v-model="scope" type="radio" value="all" :class="[radioClass, 'mt-0.5']" />
        <span>
          <span class="font-medium text-content">{{ $t('trials.retry_modal.all') }}</span>
          <span class="block text-xs text-content-muted mt-0.5">
            {{ $t('trials.retry_modal.all_desc') }}
          </span>
        </span>
      </label>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">{{
        $t('trials.retry_modal.cancel')
      }}</BaseButton>
      <BaseButton variant="primary" @click="$emit('confirm', scope === 'failed')">
        {{ $t('trials.retry_modal.confirm') }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { radioClass } from '@/utils/formStyles'

interface Props {
  open: boolean
  /** Number of failed documents in the source trial (shown in the option label). */
  failedCount?: number
}

const props = withDefaults(defineProps<Props>(), { failedCount: 0 })

defineEmits<{
  close: []
  /** Confirmed retry; payload is whether to retry only the failed documents. */
  confirm: [onlyFailed: boolean]
}>()

// Failed-only is the safe default — re-running successes costs real LLM credits.
const scope = ref<'failed' | 'all'>('failed')

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) scope.value = 'failed'
  },
)
</script>
