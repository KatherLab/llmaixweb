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
          'bg-gray-50 border-gray-200': status.type === 'none',
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
          <svg
            v-else-if="status.type === 'warning'"
            class="w-5 h-5 text-yellow-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 3 1.732 3z"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
            />
          </svg>
          <svg
            v-else-if="status.type === 'error'"
            class="w-5 h-5 text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
            />
          </svg>
          <svg
            v-else-if="status.type === 'success'"
            class="w-5 h-5 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
            />
          </svg>
          <svg
            v-else
            class="w-5 h-5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
            />
          </svg>
          <div>
            <h4 class="font-medium text-gray-900">Model & Schema Compatibility Test</h4>
            <p
              :class="[
                'text-sm',
                {
                  'text-blue-700': status.type === 'loading',
                  'text-yellow-700': status.type === 'warning',
                  'text-red-700': status.type === 'error',
                  'text-green-700': status.type === 'success',
                  'text-gray-600': status.type === 'none',
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
