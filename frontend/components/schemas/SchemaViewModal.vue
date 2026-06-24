<template>
  <BaseModal
    :open="open"
    size="lg"
    panel-class="dark:bg-slate-900 dark:border-slate-700 rounded-lg"
    header-class="dark:border-slate-700"
    body-class="p-6"
    footer-class="dark:border-slate-700 dark:bg-slate-800"
    @close="emit('close')"
  >
    <template #header>
      <h3 class="text-lg font-medium text-gray-900 dark:text-white">
        {{ schema?.schema_name }}
      </h3>
    </template>

    <div class="bg-gray-50 dark:bg-slate-800 p-4 rounded-md overflow-auto max-h-96">
      <pre class="text-sm text-gray-700 dark:text-slate-300">{{
        formatJSON(schema?.schema_definition)
      }}</pre>
    </div>

    <template #footer>
      <button
        class="inline-flex justify-center px-4 py-2 border border-gray-300 dark:border-slate-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-gray-50 dark:hover:bg-slate-600"
        @click="emit('close')"
      >
        Close
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import BaseModal from '@/components/common/BaseModal.vue'
import { formatJSON } from '@/utils/schemaTemplates'

defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  schema: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close'])
</script>
