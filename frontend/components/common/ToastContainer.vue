<template>
  <Teleport to="body">
    <TransitionGroup
      tag="div"
      name="toast"
      class="fixed top-4 right-4 z-[10000] flex flex-col gap-2 pointer-events-none"
    >
      <div v-for="t in toasts" :key="t.id" class="pointer-events-auto">
        <ToastItem
          :message="t.message"
          :type="t.type"
          :timeout="t.timeout"
          @dismiss="dismiss(t.id)"
        />
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { onUnmounted } from 'vue'
import ToastItem from '@/components/common/ToastItem.vue'
import { useToastStore } from '@/stores/toast'

const store = useToastStore()
const { toasts, dismiss, clear } = store

// Clear any pending timers when the app unmounts (HMR / tests).
onUnmounted(() => clear())
</script>

<style scoped>
/* Enter: slide + scale up from the right, fading in. */
.toast-enter-active {
  transition:
    transform 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 0.3s ease;
}
.toast-leave-active {
  transition:
    transform 0.2s ease-in,
    opacity 0.2s ease;
  position: absolute;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(1rem) scale(0.96);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(1rem) scale(0.96);
}
/* Smooth repositioning when a toast leaves the stack. */
.toast-move {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
</style>
