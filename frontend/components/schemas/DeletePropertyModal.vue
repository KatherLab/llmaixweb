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

<script setup lang="ts">
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'

interface Props {
  open: boolean
  propertyKey?: string
  advancedMode?: boolean
}

withDefaults(defineProps<Props>(), {
  propertyKey: '',
  advancedMode: false,
})

defineEmits<{
  confirm: []
  cancel: []
}>()
</script>
