<template>
  <div class="mb-4">
    <label class="block text-sm font-semibold text-gray-700 mb-1"
      >Schema <span class="text-red-500">*</span></label
    >
    <select
      v-model="model"
      class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
      @change="emit('change')"
    >
      <option disabled value="">Select a schema</option>
      <option v-for="schema in schemas" :key="schema.id" :value="schema.id.toString()">
        {{ schema.schema_name }}
      </option>
    </select>
    <details class="mt-1 text-xs">
      <summary class="text-blue-700 cursor-pointer">Preview Schema</summary>
      <pre
        v-if="selectedSchema"
        class="bg-gray-50 border rounded p-2 mt-1 max-h-32 overflow-auto font-mono text-xs"
        >{{ JSON.stringify(selectedSchema.schema_definition, null, 2) }}</pre
      >
    </details>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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
