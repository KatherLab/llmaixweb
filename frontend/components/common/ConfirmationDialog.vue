<template>
  <BaseModal
    :open="open"
    size="sm"
    role="alertdialog"
    :title="title || $t('common.confirm_dialog.title')"
    body-class="p-6"
    @close="emit('cancel')"
  >
    <p class="text-content-muted mb-6">{{ message || $t('common.confirm_dialog.message') }}</p>
    <slot />
    <template #footer>
      <BaseButton variant="secondary" :disabled="loading" @click="emit('cancel')">
        {{ cancelText || $t('common.confirm_dialog.cancel') }}
      </BaseButton>
      <BaseButton :variant="confirmVariant" :loading="loading" @click="emit('confirm')">
        {{ confirmText || $t('common.confirm_dialog.confirm') }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface Props {
  open: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  confirmVariant?: 'danger' | 'warning' | 'primary'
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  confirmVariant: 'danger',
  loading: false,
})

const emit = defineEmits<{ (e: 'confirm'): void; (e: 'cancel'): void }>()
</script>
