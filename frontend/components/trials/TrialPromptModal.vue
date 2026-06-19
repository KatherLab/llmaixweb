<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/30 backdrop-blur-md"
        @click.self="$emit('close')"
      >
        <div
          class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-6 flex flex-col max-h-[80vh] overflow-auto border border-gray-200"
        >
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-lg font-semibold text-gray-900">Trial Prompt</h3>
            <button class="text-gray-400 hover:text-gray-600" @click="$emit('close')">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          <div class="mb-2">
            <div class="flex items-center gap-2">
              <h4 class="font-semibold">{{ prompt?.name }}</h4>
              <span
                v-if="isSnapshot"
                class="text-[10px] uppercase tracking-wide bg-blue-100 text-blue-700 px-2 py-0.5 rounded"
                title="Frozen copy of the prompt as it was when the trial ran"
                >Snapshot</span
              >
            </div>
            <p v-if="prompt?.description" class="text-sm text-gray-600">{{ prompt.description }}</p>
          </div>
          <div class="mb-3">
            <label class="block font-medium text-gray-700 mb-1">System Prompt</label>
            <pre class="bg-gray-50 border rounded-md p-3 overflow-x-auto text-xs font-mono max-h-32"
              >{{ prompt?.system_prompt || '-' }}
          </pre
            >
          </div>
          <div class="mb-3">
            <label class="block font-medium text-gray-700 mb-1">User Prompt</label>
            <pre class="bg-gray-50 border rounded-md p-3 overflow-x-auto text-xs font-mono max-h-32"
              >{{ prompt?.user_prompt || '-' }}
          </pre
            >
          </div>
          <div class="flex justify-end mt-4">
            <button
              class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              @click="copyPrompt"
            >
              Copy
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>
<script setup>
import { watch } from 'vue'
import { useToast } from 'vue-toastification'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  open: Boolean,
  prompt: Object,
  isSnapshot: { type: Boolean, default: false },
})
const toast = useToast()

useScrollLock({ watch: () => props.open })

function copyPrompt() {
  if (!props.prompt) return
  const text = `System Prompt:\n${props.prompt.system_prompt || '-'}\n\nUser Prompt:\n${props.prompt.user_prompt || '-'}`
  navigator.clipboard.writeText(text)
  toast.success('Prompt copied!')
}
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
