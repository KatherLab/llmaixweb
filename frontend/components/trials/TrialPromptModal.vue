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
          <h3 class="text-lg font-semibold text-gray-900">Trial Prompt</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="mb-2">
          <h4 class="font-semibold">{{ prompt?.name }}</h4>
          <p class="text-sm text-gray-600" v-if="prompt?.description">{{ prompt.description }}</p>
        </div>
        <div class="mb-3">
          <label class="block font-medium text-gray-700 mb-1">System Prompt</label>
          <pre class="bg-gray-50 border rounded-md p-3 overflow-x-auto text-xs font-mono max-h-32">
{{ prompt?.system_prompt || '-' }}
          </pre>
        </div>
        <div class="mb-3">
          <label class="block font-medium text-gray-700 mb-1">User Prompt</label>
          <pre class="bg-gray-50 border rounded-md p-3 overflow-x-auto text-xs font-mono max-h-32">
{{ prompt?.user_prompt || '-' }}
          </pre>
        </div>
        <div class="flex justify-end mt-4">
          <button @click="copyPrompt" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
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
  prompt: Object
});
const toast = useToast();
function copyPrompt() {
  if (!props.prompt) return;
  const text = `System Prompt:\n${props.prompt.system_prompt || '-'}\n\nUser Prompt:\n${props.prompt.user_prompt || '-'}`;
  navigator.clipboard.writeText(text);
  toast.success('Prompt copied!');
}
</script>
