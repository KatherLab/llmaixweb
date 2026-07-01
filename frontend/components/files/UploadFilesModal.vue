<template>
  <BaseModal :open="open" title="Upload Files" size="md" @close="emit('close')">
    <FileDropzone compact :dragging="dragging" @drop="onDrop" @select="onSelect" />
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/common/BaseModal.vue'
import FileDropzone from '@/components/files/FileDropzone.vue'

interface Props {
  open: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  close: []
  files: [files: File[]]
}>()

// Shared dragging state (kept local — the modal is the only dropzone when open).
const dragging = defineModel<boolean>('dragging', { default: false })

const onDrop = (files: File[]) => {
  emit('files', files)
}

const onSelect = (files: File[]) => {
  emit('files', files)
}
</script>
