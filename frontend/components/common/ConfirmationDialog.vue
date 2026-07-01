<template>
  <BaseModal
    :open="open"
    size="sm"
    role="alertdialog"
    :title="title"
    body-class="p-6"
    footer-class="dark:bg-slate-800"
    @close="emit('cancel')"
  >
    <p class="text-slate-600 dark:text-slate-400 mb-6">{{ message }}</p>
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

<script setup>
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    default: 'Confirm Action',
  },
  message: {
    type: String,
    default: 'Are you sure you want to perform this action?',
  },
  confirmText: {
    type: String,
    default: 'Confirm',
  },
  cancelText: {
    type: String,
    default: 'Cancel',
  },
  confirmVariant: {
    type: String,
    default: 'danger', // 'danger', 'warning', 'primary'
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['confirm', 'cancel'])
</script>
