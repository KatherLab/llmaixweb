<template>
  <BaseModal :open="open" title="Upload Files" size="md" @close="emit('close')">
    <FileDropzone compact :dragging="dragging" @drop="onDrop" @select="onSelect" />
  </BaseModal>
</template>

<script setup>
import BaseModal from '@/components/common/BaseModal.vue'
import FileDropzone from '@/components/files/FileDropzone.vue'

defineProps({
  open: { type: Boolean, required: true },
})

const emit = defineEmits(['close', 'files'])

// Shared dragging state (kept local — the modal is the only dropzone when open).
const dragging = defineModel('dragging', { type: Boolean, default: false })

const onDrop = (files) => {
  emit('files', files)
}

const onSelect = (files) => {
  emit('files', files)
}
</script>
