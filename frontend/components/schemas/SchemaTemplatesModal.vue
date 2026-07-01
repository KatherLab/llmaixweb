<template>
  <BaseModal :open="open" size="xl" body-class="p-6" @close="emit('close')">
    <template #header>
      <div>
        <h3 class="text-lg font-medium text-slate-900 dark:text-white">Schema Templates</h3>
        <p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Select a template for common medical document structures
        </p>
      </div>
    </template>

    <div class="grid grid-cols-2 gap-4">
      <button
        v-for="template in templates"
        :key="template.name"
        class="p-4 border rounded-lg hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-left transition-colors"
        @click="emit('apply', template)"
      >
        <h4 class="font-medium text-slate-900 dark:text-white">{{ template.name }}</h4>
        <p class="text-sm text-slate-600 dark:text-slate-400 mt-1">{{ template.description }}</p>
      </button>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="emit('close')">Cancel</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import type { SchemaTemplate } from '@/utils/schemaTemplates'

interface Props {
  open: boolean
  templates: SchemaTemplate[]
}

defineProps<Props>()

const emit = defineEmits<{
  close: []
  apply: [template: SchemaTemplate]
}>()
</script>
