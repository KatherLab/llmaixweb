<template>
  <BaseModal
    :open="open"
    size="xl"
    panel-class="dark:bg-slate-900 dark:border-slate-700 rounded-xl"
    header-class="dark:border-slate-700"
    body-class="p-6"
    @close="emit('close')"
  >
    <template #header>
      <div>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">
          {{ prompt?.name }}
        </h3>
        <p v-if="prompt?.description" class="mt-1 text-sm text-gray-500 dark:text-slate-400">
          {{ prompt.description }}
        </p>
      </div>
    </template>

    <div class="space-y-4">
      <div v-if="prompt?.system_prompt" class="bg-gray-50 dark:bg-slate-800 rounded-lg p-4">
        <h4 class="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">System Prompt</h4>
        <pre class="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">{{
          prompt.system_prompt
        }}</pre>
      </div>
      <div v-if="prompt?.user_prompt" class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
        <h4 class="text-sm font-medium text-blue-700 dark:text-blue-300 mb-2">User Prompt</h4>
        <pre class="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">{{
          prompt.user_prompt
        }}</pre>
      </div>
    </div>

    <template #footer>
      <button
        class="inline-flex justify-center px-4 py-2 border border-gray-300 dark:border-slate-600 shadow-sm text-sm font-medium rounded-lg text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-gray-50 dark:hover:bg-slate-600"
        @click="emit('close')"
      >
        Close
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import BaseModal from '@/components/common/BaseModal.vue'

defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prompt: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close'])
</script>
