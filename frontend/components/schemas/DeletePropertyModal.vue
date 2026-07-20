<template>
  <ConfirmationDialog
    :open="open"
    :title="
      advancedMode
        ? $t('schemaEditor.delete_modal.title_property')
        : $t('schemaEditor.delete_modal.title_field')
    "
    :message="$t('schemaEditor.delete_modal.message', { name: propertyKey })"
    :confirm-text="$t('schemaEditor.delete_modal.confirm')"
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
