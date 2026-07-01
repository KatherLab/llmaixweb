<template>
  <div class="absolute inset-0 z-0">
    <!-- Gradient orbs with medical theme colors -->
    <div
      class="absolute top-0 left-0 h-96 w-96 rounded-full bg-blue-500 opacity-10 blur-3xl animate-pulse dark:opacity-10"
    ></div>
    <div
      class="absolute bottom-0 right-0 h-96 w-96 rounded-full bg-blue-500 opacity-10 blur-3xl animate-pulse dark:opacity-10"
      style="animation-delay: 2s"
    ></div>
    <div
      class="absolute top-1/3 left-1/2 h-64 w-64 rounded-full bg-emerald-500 opacity-5 blur-3xl animate-pulse dark:opacity-5"
      style="animation-delay: 1s"
    ></div>

    <!-- Grid pattern -->
    <div
      class="absolute inset-0 opacity-5 dark:opacity-5"
      style="
        background-image:
          linear-gradient(to right, rgba(15, 23, 42, 0.4) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(15, 23, 42, 0.4) 1px, transparent 1px);
        background-size: 24px 24px;
      "
    ></div>
    <!-- Grid pattern override for dark mode (light lines on dark) -->
    <div
      class="absolute inset-0 opacity-5 hidden dark:block"
      style="
        background-image:
          linear-gradient(to right, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
        background-size: 24px 24px;
      "
    ></div>

    <!-- Floating elements -->
    <div
      ref="floatingRoot"
      class="floating-element absolute top-20 left-10 font-mono text-xs text-blue-600 opacity-20 dark:text-blue-300 dark:opacity-20"
    >
      {"patient_id": "MED-2023-11"}
    </div>
    <div
      class="floating-element absolute top-60 right-20 font-mono text-xs text-emerald-600 opacity-20 dark:text-emerald-300 dark:opacity-20"
    >
      [extraction_complete]
    </div>
    <div
      class="floating-element absolute bottom-40 left-40 font-mono text-xs text-blue-600 opacity-20 dark:text-blue-300 dark:opacity-20"
    >
      schema.json
    </div>
    <div
      class="floating-element absolute bottom-20 right-60 font-mono text-xs text-purple-600 opacity-20 dark:text-purple-300 dark:opacity-20"
    >
      {"accuracy": 0.92}
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

onMounted(() => {
  // Animate floating elements
  const floatingElements = document.querySelectorAll<HTMLElement>('.floating-element')
  floatingElements.forEach((el, index) => {
    el.style.animation = `float ${15 + index * 2}s ease-in-out infinite`
    el.style.animationDelay = `${index * 0.5}s`
  })
})
</script>

<style scoped>
/* Floating animation */
@keyframes float {
  0%,
  100% {
    transform: translateY(0) translateX(0) rotate(0deg);
    opacity: 0.2;
  }
  25% {
    transform: translateY(-20px) translateX(10px) rotate(1deg);
    opacity: 0.3;
  }
  50% {
    transform: translateY(10px) translateX(-10px) rotate(-1deg);
    opacity: 0.2;
  }
  75% {
    transform: translateY(-15px) translateX(5px) rotate(0.5deg);
    opacity: 0.25;
  }
}

/* Pulse animation for orbs */
@keyframes pulse {
  0%,
  100% {
    opacity: 0.1;
    transform: scale(1);
  }
  50% {
    opacity: 0.15;
    transform: scale(1.1);
  }
}

.animate-pulse {
  animation: pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .floating-element {
    display: none;
  }
}
</style>
