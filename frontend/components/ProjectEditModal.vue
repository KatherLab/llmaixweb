<!-- src/components/ProjectEditModal.vue -->
<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-[1px] p-4"
        @click="emitClose"
      >
        <div
          class="bg-white/80 rounded-2xl shadow-2xl w-full max-w-lg p-8 relative overflow-y-auto max-h-[90vh]"
          style="backdrop-filter: blur(16px);"
          @click.stop
        >
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
            <button
              @click="emitClose"
              class="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700"
            >
              Cancel
            </button>
            <button
              @click="onSave"
              :disabled="isSaving"
              class="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-semibold flex items-center"
            >
              <svg
                v-if="isSaving"
                class="w-4 h-4 animate-spin mr-2"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Save
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, onUnmounted, onMounted } from 'vue';

const props = defineProps({
  open: Boolean,
  initialName: String,
  initialDescription: String,
  isSaving: Boolean
});
const emit = defineEmits(['save', 'close']);

const name = ref(props.initialName || '');
const description = ref(props.initialDescription || '');

// Sync props changes
watch(
  () => [props.initialName, props.initialDescription],
  ([newName, newDesc]) => {
    name.value = newName || '';
    description.value = newDesc || '';
  }
);

// Disable background scroll while modal is open
watch(
  () => props.open,
  (open) => {
    document.body.classList.toggle('overflow-hidden', open);
  }
);

onUnmounted(() => {
  document.body.classList.remove('overflow-hidden');
});

// Emit save event with form data
function onSave() {
  emit('save', { name: name.value, description: description.value });
}

// Emit close event
function emitClose() {
  if (!props.isSaving) {
    emit('close');
  }
}

onMounted(() => {
  if (props.open) {
    setTimeout(() => document.querySelector('input[autofocus]')?.focus(), 10);
  }
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
