<template>
  <ConfirmationDialog
    :open="open"
    :title="`Delete ${advancedMode ? 'Property' : 'Field'}`"
    :message="`Are you sure you want to delete &quot;${propertyKey}&quot;? This action cannot be undone.`"
    confirm-text="Delete"
    confirm-variant="danger"
    @confirm="$emit('confirm')"
    @cancel="$emit('cancel')"
  />
</template>

<script setup>
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'

defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  propertyKey: {
    type: String,
    default: '',
  },
  advancedMode: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['confirm', 'cancel'])
</script>
