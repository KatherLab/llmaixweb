<template>
  <BaseModal
    :open="open"
    size="sm"
    panel-class="dark:bg-slate-900 dark:border-slate-700 rounded-xl"
    header-class="dark:border-slate-700"
    body-class="p-6"
    footer-class="dark:border-slate-700 dark:bg-slate-800"
    @close="emit('cancel')"
  >
    <div class="flex justify-between items-center mb-2">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{{ title }}</h3>
    </div>
    <p class="text-gray-600 dark:text-slate-400 mb-6">{{ message }}</p>
    <template #footer>
      <button
        class="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="loading"
        @click="emit('cancel')"
      >
        {{ cancelText }}
      </button>
      <button
        :class="[
          'px-4 py-2 rounded-lg inline-flex items-center disabled:opacity-50 disabled:cursor-not-allowed',
          confirmButtonClass,
        ]"
        :disabled="loading"
        @click="emit('confirm')"
      >
        <svg
          v-if="loading"
          class="animate-spin -ml-1 mr-2 h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        {{ confirmText }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    default: 'Confirm Action',
  },
  message: {
    type: String,
    default: 'Are you sure you want to perform this action?',
  },
  confirmText: {
    type: String,
    default: 'Confirm',
  },
  cancelText: {
    type: String,
    default: 'Cancel',
  },
  confirmVariant: {
    type: String,
    default: 'danger', // 'danger', 'warning', 'primary'
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['confirm', 'cancel'])

const confirmButtonClass = computed(() => {
  const variants = {
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    warning: 'bg-yellow-600 hover:bg-yellow-700 text-white',
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
  }
  return variants[props.confirmVariant] || variants.primary
})
</script>
