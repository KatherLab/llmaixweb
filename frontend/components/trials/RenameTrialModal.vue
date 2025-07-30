<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center"
      style="backdrop-filter: blur(8px); background: rgba(30,30,40,0.27);"
      @click.self="$emit('close')"
    >
      <div
        class="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6 flex flex-col max-h-[80vh] overflow-auto"
      >
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Rename Trial</h3>
        <label class="block text-xs font-semibold text-gray-700 mb-1">Name</label>
        <input v-model="name" maxlength="100" class="w-full border border-gray-300 rounded px-2 py-1 mb-3" />
        <label class="block text-xs font-semibold text-gray-700 mb-1">Description</label>
        <textarea v-model="description" maxlength="512" class="w-full border border-gray-300 rounded px-2 py-1 mb-3" rows="2"/>
        <div class="flex gap-2 justify-end mt-2">
          <button @click="$emit('close')" class="px-3 py-1 rounded text-gray-600 bg-gray-100 hover:bg-gray-200">Cancel</button>
          <button @click="submit" :disabled="!name.trim()" class="px-3 py-1 rounded text-white bg-blue-600 hover:bg-blue-700">Save</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
  open: Boolean,
  trial: Object,
});
const emit = defineEmits(['close', 'rename']);

const name = ref('');
const description = ref('');

watch(() => props.trial, (t) => {
  name.value = t?.name || `Trial #${t?.id}` || '';
  description.value = t?.description || '';
}, { immediate: true });

function submit() {
  emit('rename', { id: props.trial.id, name: name.value.trim(), description: description.value.trim() });
}

// --- BODY SCROLL LOCK ---
function lockBodyScroll() {
  document.body.style.overflow = 'hidden';
}
function unlockBodyScroll() {
  document.body.style.overflow = '';
}
watch(() => props.open, (open) => {
  if (open) lockBodyScroll();
  else unlockBodyScroll();
});
// In case of component unmount while modal is open
onBeforeUnmount(unlockBodyScroll);
onMounted(() => {
  if (props.open) lockBodyScroll();
});
</script>
