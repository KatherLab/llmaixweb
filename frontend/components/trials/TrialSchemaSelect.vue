<template>
  <div class="mb-4">
    <label :class="labelClass">Schema <span class="text-red-500">*</span></label>
    <select v-model="model" :class="selectClass" @change="emit('change')">
      <option disabled value="">Select a schema</option>
      <option v-for="schema in schemas" :key="schema.id" :value="schema.id.toString()">
        {{ schema.schema_name }}
      </option>
    </select>
    <div v-if="selectedSchema" class="mt-1 text-xs">
      <p class="text-content-muted">
        {{ summarizeSchema(selectedSchema.schema_definition) }}
      </p>
      <details>
        <summary class="text-primary cursor-pointer hover:underline">Preview fields</summary>
        <div
          class="bg-surface-muted border border-default rounded-card p-2 mt-1 max-h-48 overflow-auto"
        >
          <SchemaFieldList :schema-definition="selectedSchema.schema_definition" />
        </div>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { summarizeSchema } from '@/utils/schemaFieldList'
import SchemaFieldList from '@/components/schemas/SchemaFieldList.vue'
import { selectClass, labelClass } from '@/utils/formStyles'
import type { Schema } from '@/types'

const props = defineProps({
  schemas: {
    type: Array as PropType<Schema[]>,
    default: () => [],
  },
})

const emit = defineEmits<{ change: [] }>()

const model = defineModel<string>({ default: '' })

const selectedSchema = computed(() => {
  if (!model.value) return null
  return props.schemas.find((schema) => schema.id.toString() === model.value) ?? null
})
</script>
