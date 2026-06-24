<template>
  <div
    ref="stepEl"
    class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
    @click="$emit('toggle')"
  >
    <div class="relative z-10 flex flex-col items-center text-center">
      <div
        class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl shadow-lg transition-all duration-300"
        :class="[step.gradient, step.shadow, active ? 'scale-110 shadow-xl' : '']"
      >
        <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            :d="step.icon"
          ></path>
        </svg>
      </div>
      <h3 class="font-bold text-white mb-2">{{ step.title }}</h3>
      <p class="text-sm text-slate-400">{{ step.subtitle }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

defineProps({
  step: {
    type: Object,
    required: true,
  },
  active: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['toggle'])

const stepEl = ref(null)

onMounted(() => {
  if (!stepEl.value) return
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-fade-in-up')
        }
      })
    },
    { threshold: 0.1 },
  )
  observer.observe(stepEl.value)
})
</script>

<style scoped>
/* Fade in up animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
}

/* Pipeline step animation */
.pipeline-step {
  opacity: 0;
  transform: translateY(20px);
}

.pipeline-step.animate-fade-in-up {
  opacity: 1;
  transform: translateY(0);
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .pipeline-step {
    margin-bottom: 2rem;
  }
}
</style>
