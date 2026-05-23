<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md"
        @click.self="$emit('close')"
      >
        <div
          class="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6 flex flex-col max-h-[80vh] overflow-auto border border-gray-200"
        >
          <h3 class="text-lg font-semibold text-gray-900 mb-2">Rename Trial</h3>
          <label class="block text-xs font-semibold text-gray-700 mb-1">Name</label>
          <input
            v-model="name"
            maxlength="100"
            class="w-full border border-gray-300 rounded px-2 py-1 mb-3"
          />
          <label class="block text-xs font-semibold text-gray-700 mb-1">Description</label>
          <textarea
            v-model="description"
            maxlength="512"
            class="w-full border border-gray-300 rounded px-2 py-1 mb-3"
            rows="2"
          />
          <div class="flex gap-2 justify-end mt-2">
            <button
              class="px-3 py-1 rounded text-gray-600 bg-gray-100 hover:bg-gray-200"
              @click="$emit('close')"
            >
              Cancel
            </button>
            <button
              :disabled="!name.trim()"
              class="px-3 py-1 rounded text-white bg-blue-600 hover:bg-blue-700"
              @click="submit"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  open: Boolean,
  trial: Object,
})
const emit = defineEmits(['close', 'rename'])

const name = ref('')
const description = ref('')

watch(
  () => props.trial,
  (t) => {
    name.value = t?.name || `Trial #${t?.id}` || ''
    description.value = t?.description || ''
  },
  { immediate: true },
)

function submit() {
  emit('rename', {
    id: props.trial.id,
    name: name.value.trim(),
    description: description.value.trim(),
  })
}

useScrollLock({ watch: () => props.open })
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
