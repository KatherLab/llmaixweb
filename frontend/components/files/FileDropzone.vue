<template>
  <div
    class="border-2 border-dashed rounded-xl text-center hover:border-blue-400 transition-colors"
    :class="[
      compact
        ? 'border-gray-300 p-10 bg-gray-50'
        : 'border-gray-300 dark:border-slate-600 p-12 bg-gray-50 dark:bg-slate-800/50',
      { 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-slate-800': dragging },
    ]"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
  >
    <svg
      class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m0-3v12"
      />
    </svg>
    <p :class="['mt-4 font-medium text-gray-900 dark:text-white', compact ? 'text-sm' : 'text-lg']">
      Drop files here or click to upload
    </p>
    <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">PDF, PNG, JPG, DOCX, CSV, XLSX, TXT</p>
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
