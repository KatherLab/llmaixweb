<template>
  <div
    class="border-2 border-dashed rounded-xl text-center hover:border-blue-400 transition-colors"
    :class="[
      compact
        ? 'border-slate-300 dark:border-slate-600 p-10 bg-slate-50 dark:bg-slate-800/50'
        : 'border-slate-300 dark:border-slate-600 p-12 bg-slate-50 dark:bg-slate-800/50',
      { 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-slate-800': dragging },
    ]"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
  >
    <UploadCloud class="mx-auto h-12 w-12 text-slate-400 dark:text-slate-500" />
    <p
      :class="['mt-4 font-medium text-slate-900 dark:text-white', compact ? 'text-sm' : 'text-lg']"
    >
      Drop files here or click to upload
    </p>
    <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
      PDF, PNG, JPG, DOCX, CSV, XLSX, TXT
    </p>
    <BaseButton
      :class="['mt-6', compact ? 'px-6 py-2.5 text-sm' : 'px-6 py-2']"
      @click="inputRef?.click()"
    >
      Browse Files
    </BaseButton>
    <input
      ref="inputRef"
      type="file"
      multiple
      accept=".pdf,.png,.jpg,.jpeg,.docx,.csv,.xlsx,.txt"
      class="hidden"
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
