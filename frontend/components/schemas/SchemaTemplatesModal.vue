<template>
  <BaseModal :open="open" size="xl" body-class="p-6" @close="emit('close')">
    <template #header>
      <div>
        <h3 class="text-lg font-medium text-content">Schema Templates</h3>
        <p class="text-sm text-content-muted mt-1">
          Select a template for common medical document structures
        </p>
      </div>
    </template>

    <div class="grid grid-cols-2 gap-4">
      <button
        v-for="template in templates"
        :key="template.name"
        class="p-4 border rounded-card hover:border-primary hover:bg-primary-soft text-left transition-colors"
        @click="emit('apply', template)"
      >
        <h4 class="font-medium text-content">{{ template.name }}</h4>
        <p class="text-sm text-content-muted mt-1">{{ template.description }}</p>
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
