<template>
  <div
    ref="stepEl"
    class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
    @click="$emit('toggle')"
  >
    <div class="relative z-10 flex flex-col items-center text-center">
      <div
        class="mb-4 flex h-20 w-20 items-center justify-center rounded-modal shadow-lg transition-all duration-300"
        :class="[step.gradient, step.shadow, active ? 'scale-110 shadow-xl' : '']"
      >
        <component :is="step.icon" class="h-10 w-10 text-white" />
      </div>
      <h3 class="font-bold text-content mb-2">{{ step.title }}</h3>
      <p class="text-sm text-content-muted">{{ step.subtitle }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, type Component } from 'vue'

interface Step {
  id: number
  title: string
  subtitle: string
  gradient: string
  shadow: string
  icon: Component
}

interface Props {
  step: Step
  active?: boolean
}

withDefaults(defineProps<Props>(), {
  active: false,
})

defineEmits<{ toggle: [] }>()

const stepEl = ref<HTMLElement | null>(null)

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
