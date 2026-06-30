<template>
  <div
    ref="cardEl"
    class="feature-card group relative overflow-hidden rounded-xl border border-slate-200 bg-white p-6 transition-all dark:border-slate-700 dark:bg-gradient-to-br dark:from-slate-900 dark:to-slate-800"
    :class="[feature.borderHover, feature.shadowHover]"
  >
    <div
      class="absolute inset-0 bg-gradient-to-br to-transparent opacity-0 group-hover:opacity-100 transition-opacity"
      :class="feature.gradientFrom"
    ></div>
    <div class="relative z-10">
      <div
        class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg transition-colors"
        :class="[feature.iconBg, feature.iconText, feature.iconHoverBg]"
      >
        <component :is="feature.icon" class="h-6 w-6" />
      </div>
      <h3 class="mb-2 text-lg font-bold text-slate-900 dark:text-white">{{ feature.title }}</h3>
      <p class="text-sm text-slate-600 dark:text-slate-300">{{ feature.description }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  feature: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    default: 0,
  },
})

const cardEl = ref(null)

onMounted(() => {
  if (!cardEl.value) return
  // Preserve staggered fade-in delay from original (index * 0.1s)
  cardEl.value.style.animationDelay = `${props.index * 0.1}s`
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
  observer.observe(cardEl.value)
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

/* Feature card hover effects */
.feature-card {
  opacity: 0;
  transform: translateY(20px);
}

.feature-card.animate-fade-in-up {
  opacity: 1;
  transform: translateY(0);
}

/* Interactive hover states */
.group:hover .group-hover\:scale-110 {
  transform: scale(1.1);
}
</style>
