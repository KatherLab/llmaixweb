<template>
  <BaseModal :open="open" size="sm" body-class="p-6" @close="$emit('close')">
    <template #header>
      <h3 class="text-lg font-semibold text-content">Retry Trial</h3>
    </template>

    <p class="text-sm text-content-muted">
      Start a new trial run with the same configuration? This will consume LLM credits.
    </p>

    <div class="mt-4 space-y-3">
      <label class="flex items-start gap-2 text-sm cursor-pointer">
        <input v-model="scope" type="radio" value="failed" :class="[radioClass, 'mt-0.5']" />
        <span>
          <span class="font-medium text-content">
            Retry failed documents only{{ failedCount ? ` (${failedCount})` : '' }}
          </span>
          <span class="block text-xs text-content-muted mt-0.5">
            Creates a new trial that processes just the documents that failed.
          </span>
        </span>
      </label>
      <label class="flex items-start gap-2 text-sm cursor-pointer">
        <input v-model="scope" type="radio" value="all" :class="[radioClass, 'mt-0.5']" />
        <span>
          <span class="font-medium text-content">Re-run all documents</span>
          <span class="block text-xs text-content-muted mt-0.5">
            Processes every document again, including the ones that already succeeded.
          </span>
        </span>
      </label>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">Cancel</BaseButton>
      <BaseButton variant="primary" @click="$emit('confirm', scope === 'failed')">
        Retry Trial
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
