<template>
  <BaseModal
    :open="open"
    size="sm"
    role="alertdialog"
    :title="title"
    body-class="p-6"
    @close="emit('cancel')"
  >
    <p class="text-content-muted mb-6">{{ message }}</p>
    <slot />
    <template #footer>
      <BaseButton variant="secondary" :disabled="loading" @click="emit('cancel')">
        {{ cancelText }}
      </BaseButton>
      <BaseButton :variant="confirmVariant" :loading="loading" @click="emit('confirm')">
        {{ confirmText }}
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
  title: 'Confirm Action',
  message: 'Are you sure you want to perform this action?',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  confirmVariant: 'danger',
  loading: false,
})

const emit = defineEmits<{ (e: 'confirm'): void; (e: 'cancel'): void }>()
</script>
