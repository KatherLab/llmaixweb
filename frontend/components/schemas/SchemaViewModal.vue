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
      <h3 class="text-lg font-medium text-slate-900 dark:text-white">
        {{ schema?.schema_name }}
      </h3>
    </template>

    <div class="bg-slate-50 dark:bg-slate-800 p-4 rounded-md overflow-auto max-h-96">
      <pre class="text-sm text-slate-700 dark:text-slate-300">{{
        formatJSON(schema?.schema_definition)
      }}</pre>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="emit('close')">Close</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
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
