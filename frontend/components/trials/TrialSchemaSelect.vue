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
      <p class="text-slate-500 dark:text-slate-400">
        {{ summarizeSchema(selectedSchema.schema_definition) }}
      </p>
      <details>
        <summary class="text-blue-700 dark:text-blue-400 cursor-pointer hover:underline">
          Preview fields
        </summary>
        <div class="bg-slate-50 dark:bg-slate-800 border rounded p-2 mt-1 max-h-48 overflow-auto">
          <SchemaFieldList :schema-definition="selectedSchema.schema_definition" />
        </div>
      </details>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { summarizeSchema } from '@/utils/schemaFieldList'
import SchemaFieldList from '@/components/schemas/SchemaFieldList.vue'
import { selectClass, labelClass } from '@/utils/formStyles'

const props = defineProps({
  schemas: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['change'])

const model = defineModel({ type: String, default: '' })

const selectedSchema = computed(() => {
  if (!model.value) return null
  return props.schemas.find((schema) => schema.id.toString() === model.value)
})
</script>
