<template>
  <div class="my-6">
    <div
      :class="[
        'p-4 rounded-md border',
        {
          'bg-blue-50 border-blue-200': status.type === 'loading',
          'bg-yellow-50 border-yellow-200': status.type === 'warning',
          'bg-red-50 border-red-200': status.type === 'error',
          'bg-green-50 border-green-200': status.type === 'success',
          'bg-slate-50 border-slate-200': status.type === 'none',
        },
      ]"
    >
      <div class="flex items-center justify-between">
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
          <Info v-else class="w-5 h-5 text-slate-500" />
          <div>
            <h4 class="font-medium text-slate-900">Model & Schema Compatibility Test</h4>
            <p
              :class="[
                'text-sm',
                {
                  'text-blue-700': status.type === 'loading',
                  'text-yellow-700': status.type === 'warning',
                  'text-red-700': status.type === 'error',
                  'text-green-700': status.type === 'success',
                  'text-slate-600': status.type === 'none',
                },
              ]"
            >
              {{ status.message }}
            </p>
          </div>
        </div>
        <BaseButton
          variant="primary"
          :loading="isTesting"
          :disabled="!llmModel || !schemaId"
          @click="emit('test')"
          >{{ isTesting ? 'Testing...' : 'Test Model' }}</BaseButton
        >
      </div>
      <div
        v-if="status.type === 'warning'"
        class="mt-3 p-3 bg-yellow-100 border border-yellow-200 rounded-md"
      >
        <p class="text-yellow-800 text-sm">
          <strong>Required:</strong> You must test the selected model with the schema to ensure
          compatibility before creating a trial.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { AlertCircle, AlertTriangle, CircleCheckBig, Info } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'

defineProps({
  status: {
    type: Object,
    required: true,
    // { type: 'none'|'loading'|'warning'|'error'|'success', message: string }
  },
  isTesting: {
    type: Boolean,
    default: false,
  },
  llmModel: {
    type: String,
    default: '',
  },
  schemaId: {
    type: [String, Number],
    default: '',
  },
})

const emit = defineEmits(['test'])
</script>
