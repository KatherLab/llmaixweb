<template>
  <BaseModal
    :open="open"
    size="xl"
    panel-class="dark:bg-slate-900 dark:border-slate-700 rounded-lg"
    body-class="p-6"
    @close="emit('close')"
  >
    <template #header>
      <div>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Schema Templates</h3>
        <p class="text-sm text-gray-600 dark:text-slate-400 mt-1">
          Select a template for common medical document structures
        </p>
      </div>
    </template>

    <div class="grid grid-cols-2 gap-4">
      <button
        v-for="template in templates"
        :key="template.name"
        class="p-4 border rounded-lg hover:border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-left transition-colors"
        @click="emit('apply', template)"
      >
        <h4 class="font-medium text-gray-900 dark:text-white">{{ template.name }}</h4>
        <p class="text-sm text-gray-600 dark:text-slate-400 mt-1">{{ template.description }}</p>
      </button>
    </div>

    <template #footer>
      <button
        class="px-4 py-2 border border-gray-300 dark:border-slate-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-gray-50 dark:hover:bg-slate-600"
        @click="emit('close')"
      >
        Cancel
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
  templates: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['close', 'apply'])
</script>
