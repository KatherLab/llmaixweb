<template>
  <div class="my-6">
    <Callout :variant="calloutVariant">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-2">
          <LoadingSpinner
            v-if="status.type === 'loading'"
            size="small"
            color="blue"
            inline
            label=""
          />
          <div>
            <h4 class="font-medium text-slate-900 dark:text-white">
              Model &amp; Schema Compatibility
            </h4>
            <p class="text-sm text-slate-600 dark:text-slate-400">
              {{ status.message }}
            </p>
          </div>
        </div>
        <!-- Optional pre-verification: hidden once verified or while testing -->
        <BaseButton
          v-if="status.type !== 'success' && status.type !== 'loading'"
          variant="secondary"
          :disabled="!llmModel || !schemaId"
          @click="emit('test')"
          >Test now</BaseButton
        >
      </div>
      <div
        v-if="status.type === 'warning'"
        class="mt-3 p-3 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-card"
      >
        <p class="text-yellow-800 dark:text-yellow-300 text-sm">
          The model is checked automatically when you start the trial — or test it now to confirm
          compatibility beforehand.
        </p>
      </div>
    </Callout>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Callout from '@/components/common/Callout.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface StatusDescriptor {
  type: 'loading' | 'warning' | 'error' | 'success' | 'none'
  message: string
}

const props = defineProps<{
  status: StatusDescriptor
  isTesting?: boolean
  llmModel?: string
  schemaId?: string | number
}>()

const emit = defineEmits<{ test: [] }>()

const calloutVariant = computed<'info' | 'warning' | 'danger' | 'success' | 'gray'>(() => {
  switch (props.status.type) {
    case 'loading':
      return 'info'
    case 'warning':
      return 'warning'
    case 'error':
      return 'danger'
    case 'success':
      return 'success'
    default:
      return 'gray'
  }
})
</script>
