<template>
  <div
    role="button"
    tabindex="0"
    aria-label="Upload files — drop files here or activate to browse"
    class="border-2 border-dashed rounded-modal text-center hover:border-primary transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    :class="[
      compact ? 'border-strong p-10 bg-surface-muted' : 'border-strong p-12 bg-surface-muted',
      { 'border-primary bg-primary-soft': dragging },
    ]"
    @click="openPicker"
    @keydown.enter.prevent="openPicker"
    @keydown.space.prevent="openPicker"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
  >
    <UploadCloud class="mx-auto h-12 w-12 text-content-subtle" aria-hidden="true" />
    <p :class="['mt-4 font-medium text-content', compact ? 'text-sm' : 'text-lg']">
      Drop files here or click to upload
    </p>
    <p class="mt-2 text-sm text-content-muted">PDF, PNG, JPG, DOC, DOCX, CSV, XLSX, TXT</p>
    <BaseButton
      :class="['mt-6', compact ? 'px-6 py-2.5 text-sm' : 'px-6 py-2']"
      @click.stop="openPicker"
    >
      Browse Files
    </BaseButton>
    <!-- @click.stop: the programmatic input.click() bubbles back to the
         container's click handler and would re-open the picker in a loop. -->
    <input
      ref="inputRef"
      type="file"
      multiple
      accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.csv,.xlsx,.txt"
      class="hidden"
      aria-hidden="true"
      tabindex="-1"
      @click.stop
      @change="onSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadCloud } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface Props {
  compact?: boolean
}

withDefaults(defineProps<Props>(), {
  compact: false,
})

const emit = defineEmits<{
  drop: [files: File[]]
  select: [files: File[]]
}>()

// Synced with the parent so empty-state visibility guards keep working.
const dragging = defineModel<boolean>('dragging', { default: false })

const inputRef = ref<HTMLInputElement | null>(null)

const openPicker = () => {
  inputRef.value?.click()
}

const onDrop = (e: DragEvent) => {
  dragging.value = false
  emit('drop', Array.from(e.dataTransfer?.files ?? []))
}

const onSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  emit('select', Array.from(target.files ?? []))
  target.value = ''
}
</script>
