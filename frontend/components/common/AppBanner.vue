<template>
  <div
    v-if="visible"
    role="status"
    class="w-full text-center py-1.5 px-4 text-sm font-medium"
    :class="colorClass"
  >
    {{ text }}
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { usePublicSettingsStore } from '@/stores/publicSettings'

const store = usePublicSettingsStore()

onMounted(() => {
  store.fetch()
})

// Literal class strings per color so Tailwind's JIT keeps them in the build.
const COLOR_CLASSES: Record<string, string> = {
  amber: 'bg-amber-500 text-white dark:bg-amber-600',
  red: 'bg-red-600 text-white',
  blue: 'bg-blue-600 text-white',
  green: 'bg-green-600 text-white',
  gray: 'bg-gray-700 text-white',
}

const visible = computed(
  () => !!store.settings?.banner_enabled && !!store.settings?.banner_text?.trim(),
)
const text = computed(() => store.settings?.banner_text ?? '')
const colorClass = computed(
  () => COLOR_CLASSES[store.settings?.banner_color ?? 'amber'] ?? COLOR_CLASSES.amber,
)
</script>
