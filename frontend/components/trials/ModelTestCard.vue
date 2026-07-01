<template>
  <div class="my-6">
    <div
      :class="[
        'p-4 rounded-md border',
        {
          'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800':
            status.type === 'loading',
          'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800':
            status.type === 'warning',
          'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800':
            status.type === 'error',
          'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800':
            status.type === 'success',
          'bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700':
            status.type === 'none',
        },
      ]"
    >
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-2">
          <LoadingSpinner
            v-if="status.type === 'loading'"
            size="small"
            color="blue"
            inline
            label=""
          />
          <AlertTriangle v-else-if="status.type === 'warning'" class="w-5 h-5 text-yellow-500" />
          <AlertCircle v-else-if="status.type === 'error'" class="w-5 h-5 text-red-500" />
          <CircleCheckBig v-else-if="status.type === 'success'" class="w-5 h-5 text-green-500" />
          <Info v-else class="w-5 h-5 text-slate-500 dark:text-slate-400" />
          <div>
            <h4 class="font-medium text-slate-900 dark:text-white">
              Model &amp; Schema Compatibility
            </h4>
            <p
              :class="[
                'text-sm',
                {
                  'text-blue-700 dark:text-blue-300': status.type === 'loading',
                  'text-yellow-700 dark:text-yellow-300': status.type === 'warning',
                  'text-red-700 dark:text-red-300': status.type === 'error',
                  'text-green-700 dark:text-green-300': status.type === 'success',
                  'text-slate-600 dark:text-slate-400': status.type === 'none',
                },
              ]"
            >
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
        class="mt-3 p-3 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-md"
      >
        <p class="text-yellow-800 dark:text-yellow-300 text-sm">
          The model is checked automatically when you start the trial — or test it now to confirm
          compatibility beforehand.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertCircle, AlertTriangle, CircleCheckBig, Info } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface StatusDescriptor {
  type: 'loading' | 'warning' | 'error' | 'success' | 'none'
  message: string
}

defineProps<{
  status: StatusDescriptor
  isTesting?: boolean
  llmModel?: string
  schemaId?: string | number
}>()

const emit = defineEmits<{ test: [] }>()
</script>
