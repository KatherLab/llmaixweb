<!-- src/components/ProjectEditModal.vue -->
<template>
  <transition name="fade">
    <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur">
      <div class="bg-white/80 rounded-2xl shadow-2xl w-full max-w-lg p-8 relative" style="backdrop-filter: blur(16px);">
        <h2 class="text-xl font-bold mb-4 text-gray-900">Edit Project</h2>
        <input
          v-model="name"
          class="w-full px-4 py-2 text-lg font-semibold rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-400 mb-3"
          placeholder="Project Name"
          autofocus
        />
        <textarea
          v-model="description"
          class="w-full px-4 py-2 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-400"
          rows="3"
          placeholder="Description (optional)"
        ></textarea>
        <div class="flex justify-end mt-6 space-x-2">
          <button @click="$emit('close')" class="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700">Cancel</button>
          <button @click="onSave" :disabled="isSaving" class="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-semibold flex items-center">
            <svg v-if="isSaving" class="w-4 h-4 animate-spin mr-2" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg>
            Save
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>
<script setup>
import { ref, watch, onMounted } from 'vue';
const props = defineProps({
  open: Boolean,
  initialName: String,
  initialDescription: String,
  isSaving: Boolean
});
const emit = defineEmits(['save', 'close']);

const name = ref(props.initialName || '');
const description = ref(props.initialDescription || '');

watch(() => [props.initialName, props.initialDescription], ([newName, newDesc]) => {
  name.value = newName;
  description.value = newDesc;
});
function onSave() {
  emit('save', { name: name.value, description: description.value });
}
onMounted(() => {
  if (props.open) setTimeout(() => document.querySelector('input[autofocus]')?.focus(), 10);
});
</script>
<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
