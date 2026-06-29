<template>
  <div class="relative flex-1 max-w-sm min-w-[200px]">
    <input
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :aria-label="placeholder"
      class="w-full pl-10 pr-4 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
      @input="onInput"
    />
    <Search
      class="absolute left-3 top-2.5 h-4 w-4 text-slate-400 dark:text-slate-500"
      aria-hidden="true"
    />
  </div>
</template>

<script setup>
import { Search } from '@lucide/vue'

defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: 'Search...',
  },
})

const emit = defineEmits(['update:modelValue', 'input'])

function onInput(event) {
  emit('update:modelValue', event.target.value)
  emit('input', event.target.value)
}
</script>
