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
            <h3 class="text-lg font-semibold text-gray-900">Trial Schema</h3>
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
          <div class="flex items-center gap-2 mb-2">
            <h4 class="font-semibold">{{ schema?.schema_name }}</h4>
            <span
              v-if="isSnapshot"
              class="text-[10px] uppercase tracking-wide bg-blue-100 text-blue-700 px-2 py-0.5 rounded"
              title="Frozen copy of the schema as it was when the trial ran"
              >Snapshot</span
            >
          </div>
          <pre class="bg-gray-50 border rounded-md p-4 overflow-x-auto text-xs font-mono max-h-96"
            >{{ JSON.stringify(schema?.schema_definition, null, 2) }}
        </pre
          >
          <div class="flex justify-end mt-4">
            <button
              class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              @click="copyToClipboard"
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
  schema: Object,
  isSnapshot: { type: Boolean, default: false },
})
const toast = useToast()

useScrollLock({ watch: () => props.open })

function copyToClipboard() {
  if (!props.schema) return
  navigator.clipboard.writeText(JSON.stringify(props.schema.schema_definition, null, 2))
  toast.success('Schema copied!')
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
