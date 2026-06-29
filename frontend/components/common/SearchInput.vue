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

<script setup>
import { Search } from '@lucide/vue'
import { inputClass } from '@/utils/formStyles'

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
