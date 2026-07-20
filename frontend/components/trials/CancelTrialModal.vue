<template>
  <BaseModal :open="open" size="sm" body-class="p-6" @close="$emit('close')">
    <template #header>
      <h3 class="text-lg font-semibold text-content">{{ $t('trials.cancel_modal.title') }}</h3>
    </template>

    <p class="text-sm text-content-muted">
      {{ $t('trials.cancel_modal.message') }}
    </p>

    <label class="mt-4 flex items-start gap-2 text-sm cursor-pointer">
      <input v-model="keepProcessed" type="checkbox" :class="[checkboxClass, 'mt-0.5']" />
      <span>
        <span class="font-medium text-content">{{ $t('trials.cancel_modal.keep_label') }}</span>
        <span class="block text-xs text-content-muted mt-0.5">
          {{
            keepProcessed ? $t('trials.cancel_modal.keep_yes') : $t('trials.cancel_modal.keep_no')
          }}
        </span>
      </span>
    </label>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">{{
        $t('trials.cancel_modal.keep_running')
      }}</BaseButton>
      <BaseButton variant="warning" @click="$emit('confirm', keepProcessed)">{{
        $t('trials.cancel_modal.confirm')
      }}</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { checkboxClass } from '@/utils/formStyles'

interface Props {
  open: boolean
}

const props = defineProps<Props>()

defineEmits<{
  close: []
  /** Confirmed cancellation; payload is the "keep already-processed results" choice. */
  confirm: [keepProcessed: boolean]
}>()

// Keeping finished results is the safe default — discarding is irreversible.
const keepProcessed = ref(true)

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) keepProcessed.value = true
  },
)
</script>
