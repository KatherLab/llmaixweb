<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center"
      style="backdrop-filter: blur(8px); background: rgba(30,30,40,0.27);"
      @click.self="$emit('close')"
    >
      <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border p-6 flex flex-col">
        <div class="flex justify-between items-center mb-3">
          <h3 class="text-lg font-semibold text-gray-900">Trial Schema</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <h4 class="font-semibold mb-2">{{ schema?.schema_name }}</h4>
        <pre class="bg-gray-50 border rounded-md p-4 overflow-x-auto text-xs font-mono max-h-96">
{{ JSON.stringify(schema?.schema_definition, null, 2) }}
        </pre>
        <div class="flex justify-end mt-4">
          <button @click="copyToClipboard" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Copy
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
<script setup>
import { useToast } from 'vue-toastification';
const props = defineProps({
  open: Boolean,
  schema: Object
});
const toast = useToast();
function copyToClipboard() {
  if (!props.schema) return;
  navigator.clipboard.writeText(JSON.stringify(props.schema.schema_definition, null, 2));
  toast.success('Schema copied!');
}
</script>
