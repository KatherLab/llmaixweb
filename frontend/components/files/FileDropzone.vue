<template>
  <div
    class="border-2 border-dashed rounded-xl text-center hover:border-blue-400 transition-colors"
    :class="[
      compact
        ? 'border-slate-300 p-10 bg-slate-50'
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

<script setup>
import { ref } from 'vue'
import { UploadCloud } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'

defineProps({
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['drop', 'select'])

// Synced with the parent so empty-state visibility guards keep working.
const dragging = defineModel('dragging', { type: Boolean, default: false })

const inputRef = ref(null)

const onDrop = (e) => {
  dragging.value = false
  emit('drop', Array.from(e.dataTransfer.files))
}

const onSelect = (e) => {
  emit('select', Array.from(e.target.files))
  e.target.value = null
}
</script>
