<template>
  <div class="bg-surface border-b border-default px-4 py-3 flex items-center justify-between">
    <div class="flex items-center space-x-4">
      <!-- Navigation Breadcrumb -->
      <nav class="flex items-center space-x-2 text-sm">
        <button
          type="button"
          class="text-content-muted hover:text-content font-medium"
          @click="$emit('navigate-to-root')"
        >
          {{ $t('schemaEditor.tree.root') }}
        </button>
        <template v-for="(segment, index) in navigationPath" :key="index">
          <ChevronRight class="h-4 w-4 text-content-subtle" />
          <button
            type="button"
            class="text-content-muted hover:text-content font-medium"
            @click="$emit('navigate-to-path', index)"
          >
            {{ segment }}
          </button>
        </template>
      </nav>
    </div>

    <!-- Quick Actions -->
    <div class="flex items-center space-x-2">
      <button
        type="button"
        class="p-2 text-content-muted hover:text-content hover:bg-surface-muted rounded-card"
        :title="$t('schemaEditor.toolbar.help')"
        @click="$emit('show-help')"
      >
        <CircleHelp class="h-5 w-5" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight, CircleHelp } from '@lucide/vue'

interface Props {
  navigationPath?: string[]
}

withDefaults(defineProps<Props>(), {
  navigationPath: () => [],
})

defineEmits<{
  'navigate-to-root': []
  'navigate-to-path': [index: number]
  'show-help': []
}>()
</script>
