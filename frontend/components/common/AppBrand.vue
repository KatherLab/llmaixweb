<!--
  Single source of truth for the LLMAIx wordmark.

  - `asLink` (default true): renders as a <router-link> to `to` (default "/"),
    so the logo always returns to the landing page — from anywhere in the app.
  - `asLink={false}`: renders as a plain heading element (used on auth/setup
    pages where the wordmark is a page heading, not navigation).
  - `variant="hero"`: the gradient text treatment used on the landing hero.
  - `size`: sm (navbar), md (auth pages), lg (hero).
-->
<template>
  <component
    :is="asLink ? 'router-link' : 'span'"
    :to="asLink ? to : undefined"
    :aria-label="asLink ? 'LLMAIx home' : undefined"
    class="font-extrabold tracking-tight inline-block"
    :class="[
      sizeClass,
      variant === 'hero'
        ? 'bg-gradient-to-r from-primary to-primary-hover bg-clip-text text-transparent dark:from-primary dark:to-primary-hover'
        : 'text-content',
    ]"
  >
    LLMAIx-v2
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  asLink?: boolean
  to?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'hero'
}

const props = withDefaults(defineProps<Props>(), {
  asLink: true,
  to: '/',
  size: 'sm',
  variant: 'default',
})

const sizeClass = computed(() => {
  switch (props.size) {
    case 'lg':
      return 'text-5xl sm:text-7xl'
    case 'md':
      return 'text-4xl'
    default:
      return 'text-xl'
  }
})
</script>
