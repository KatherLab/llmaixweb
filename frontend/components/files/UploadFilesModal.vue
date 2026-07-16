<template>
  <BaseModal :open="open" title="Upload Files" size="md" @close="emit('close')">
    <!-- Idle: drop zone -->
    <FileDropzone v-if="!progress" compact :dragging="dragging" @drop="onDrop" @select="onSelect" />

    <!-- Uploading / summary -->
    <div v-else class="space-y-4">
      <!-- Overall progress -->
      <div>
        <div class="flex items-center justify-between gap-2">
          <p class="text-sm font-medium text-content">
            <template v-if="!progress.done">
              Uploading file {{ progress.currentIndex }} of {{ progress.total }}
            </template>
            <template v-else> Upload complete </template>
          </p>
          <span class="text-xs text-content-subtle tabular-nums">{{ overallPercent }}%</span>
        </div>
        <div class="mt-2 h-2 w-full bg-surface-sunken rounded-full overflow-hidden">
          <div
            class="h-full transition-all duration-200"
            :class="progress.failures.length > 0 && progress.done ? 'bg-amber-500' : 'bg-primary'"
            :style="{ width: overallPercent + '%' }"
          ></div>
        </div>
        <p class="mt-2 text-xs text-content-muted">
          {{ progress.succeeded }} succeeded<span v-if="progress.failures.length > 0">
            ·
            <span class="text-red-600 dark:text-red-400"
              >{{ progress.failures.length }} failed</span
            ></span
          >
        </p>
      </div>

      <!-- Current file (during upload) -->
      <div v-if="!progress.done" class="rounded-card border border-default bg-surface-muted p-3">
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs font-medium text-content truncate" :title="progress.currentName">
            {{ progress.currentName }}
          </p>
          <span class="text-xs text-content-subtle tabular-nums shrink-0"
            >{{ progress.currentPercent }}%</span
          >
        </div>
        <div class="mt-1.5 h-1 w-full bg-surface-sunken rounded-full overflow-hidden">
          <div
            class="h-full bg-primary transition-all duration-200"
            :style="{ width: progress.currentPercent + '%' }"
          ></div>
        </div>
      </div>

      <!-- Failure list (summary screen) -->
      <div
        v-if="progress.done && progress.failures.length > 0"
        class="rounded-card border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30 p-3 max-h-48 overflow-y-auto"
      >
        <p class="text-xs font-medium text-red-700 dark:text-red-300 mb-1.5">Failed uploads</p>
        <ul class="space-y-1">
          <li
            v-for="f in progress.failures"
            :key="f.name"
            class="text-xs text-red-600 dark:text-red-400"
          >
            <span class="font-medium">{{ f.name }}</span> — {{ f.message }}
          </li>
        </ul>
      </div>
    </div>

    <template v-if="progress && progress.done" #footer>
      <BaseButton @click="emit('close')">Close</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import FileDropzone from '@/components/files/FileDropzone.vue'

export interface UploadProgressState {
  total: number
  completed: number
  succeeded: number
  currentIndex: number
  currentName: string
  currentPercent: number
  failures: { name: string; message: string }[]
  done: boolean
}

interface Props {
  open: boolean
  progress?: UploadProgressState | null
}

const props = withDefaults(defineProps<Props>(), {
  progress: null,
})

const emit = defineEmits<{
  close: []
  files: [files: File[]]
}>()

// Shared dragging state (kept local — the modal is the only dropzone when open).
const dragging = defineModel<boolean>('dragging', { default: false })

// Overall percent blends fully-completed files with the in-flight file's own
// progress, so the bar advances smoothly across a large batch.
const overallPercent = computed(() => {
  const p = props.progress
  if (!p || p.total === 0) return 0
  if (p.done) return 100
  const doneFraction = p.completed + p.currentPercent / 100
  return Math.min(100, Math.round((doneFraction / p.total) * 100))
})

const onDrop = (files: File[]) => {
  emit('files', files)
}

const onSelect = (files: File[]) => {
  emit('files', files)
}
</script>
