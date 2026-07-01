<template>
  <div class="relative flex-1 max-w-sm min-w-[200px]">
    <input
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :aria-label="placeholder"
      :class="[inputClass, 'pl-10 pr-4']"
      @input="onInput"
    />
    <Search
      class="absolute left-3 top-2.5 h-4 w-4 text-slate-400 dark:text-slate-500"
      aria-hidden="true"
    />
  </div>
</template>

<script setup lang="ts">
import { Search } from '@lucide/vue'
import { inputClass } from '@/utils/formStyles'

interface Props {
  modelValue?: string
  placeholder?: string
}

withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: 'Search...',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'input', value: string): void
}>()

function onInput(event: Event) {
  const value = (event.target as HTMLInputElement).value
  emit('update:modelValue', value)
  emit('input', value)
}
</script>
