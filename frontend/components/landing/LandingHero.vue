<template>
  <div class="mb-20 text-center">
    <div
      class="mb-6 inline-block rounded-card border border-default bg-primary-soft p-3 backdrop-blur-sm"
    >
      <span class="text-sm font-semibold tracking-wider uppercase text-primary">
        Document-to-JSON Extraction Platform
      </span>
    </div>
    <h1 class="mb-6 text-5xl font-extrabold text-content sm:text-7xl">
      <AppBrand :as-link="false" size="lg" variant="hero" />
    </h1>
    <p class="mx-auto max-w-3xl text-xl leading-relaxed text-content-muted">
      Turn unstructured medical and lab documents into validated structured JSON. Define your
      schema, run LLM extraction trials, and measure accuracy against ground-truth data — with any
      OpenAI-compatible model, local or hosted.
    </p>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
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
