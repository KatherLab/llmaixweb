<template>
  <div class="mb-20 text-center">
    <div
      class="mb-6 inline-block rounded-lg border border-blue-200 bg-blue-50 p-3 backdrop-blur-sm dark:border-blue-500/30 dark:bg-blue-600/20"
    >
      <span
        class="text-sm font-semibold tracking-wider uppercase text-blue-700 dark:bg-gradient-to-r dark:from-blue-400 dark:to-blue-400 dark:bg-clip-text dark:text-transparent"
      >
        Document-to-JSON Extraction Platform
      </span>
    </div>
    <h1 class="mb-6 text-5xl font-extrabold text-slate-900 sm:text-7xl dark:text-white">
      <span
        class="bg-gradient-to-r from-blue-600 to-blue-700 bg-clip-text text-transparent dark:from-blue-400 dark:via-blue-400 dark:to-purple-400"
      >
        LLMAIx-v2
      </span>
    </h1>
    <p class="mx-auto max-w-3xl text-xl leading-relaxed text-slate-600 dark:text-slate-300">
      Turn unstructured medical and lab documents into validated structured JSON. Define your
      schema, run LLM extraction trials, and measure accuracy against ground-truth data — with any
      OpenAI-compatible model, local or hosted.
    </p>
  </div>
</template>

<script setup lang="ts">
// Static hero section — no script logic needed
</script>

<style scoped>
/* Gradient text animation */
@keyframes gradient-shift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

h1 .bg-gradient-to-r {
  background-size: 200% 200%;
  animation: gradient-shift 6s ease infinite;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  h1 {
    font-size: 3rem;
  }
}
</style>
