<template>
  <div class="mb-20 text-center">
    <div
      class="mb-6 inline-block rounded-lg bg-gradient-to-r from-blue-600/20 to-blue-600/20 border border-blue-500/30 p-3 backdrop-blur-sm"
    >
      <span
        class="text-sm font-semibold tracking-wider uppercase bg-gradient-to-r from-blue-400 to-blue-400 bg-clip-text text-transparent"
      >
        Medical Document Intelligence Platform
      </span>
    </div>
    <h1 class="mb-6 text-5xl font-extrabold sm:text-7xl">
      <span
        class="bg-gradient-to-r from-blue-400 via-blue-400 to-purple-400 bg-clip-text text-transparent"
      >
        LLMAIx-v2
      </span>
    </h1>
    <p class="mx-auto max-w-3xl text-xl text-slate-300 leading-relaxed">
      Transform unstructured medical documents into structured data using state-of-the-art Large
      Language Models with complete privacy and control over your extraction pipeline
    </p>
  </div>
</template>

<script setup>
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

.bg-gradient-to-r {
  background-size: 200% 200%;
}

h1 .bg-gradient-to-r {
  animation: gradient-shift 6s ease infinite;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  h1 {
    font-size: 3rem;
  }
}
</style>
