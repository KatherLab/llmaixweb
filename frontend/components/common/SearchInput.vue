<template>
  <div class="relative flex-1 max-w-sm min-w-[200px]">
    <input
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :aria-label="placeholder"
      class="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
      @input="onInput"
    />
    <svg
      class="absolute left-3 top-2.5 h-4 w-4 text-gray-400 dark:text-gray-500"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  </div>
</template>

<script setup>
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
