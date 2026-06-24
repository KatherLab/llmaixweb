<!--
  Shared underline tab group (mutually-exclusive single-select).

  Replaces the copy-pasted `border-b-2` tab clusters scattered across views.
  Dark-mode is always included (normalizes the instances that lacked it).

  Two ways to render tab content:
    1. Declarative: pass `tabs` array of { label, value, icon?, badge? }.
    2. Custom: omit `tabs` and use the `#tab="{ tab }"` scoped slot for full
       control (icons, badges, custom markup). The slot is rendered inside
       each button; the active/inactive styling is handled for you.

  v-model holds the active tab's `value`.
-->
<template>
  <div class="border-b border-gray-200 dark:border-gray-700">
    <nav class="-mb-px flex space-x-8" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        role="tab"
        :aria-selected="modelValue === tab.value"
        :class="[
          'py-2 px-1 border-b-2 font-medium text-sm transition-colors',
          modelValue === tab.value ? activeClass : inactiveClass,
        ]"
        @click="emit('update:modelValue', tab.value)"
      >
        <slot name="tab" :tab="tab">
          <span class="flex items-center gap-2">
            <span v-if="tab.icon" class="text-lg">{{ tab.icon }}</span>
            {{ tab.label }}
            <span
              v-if="tab.badge !== undefined && tab.badge !== null"
              class="bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded-full text-xs ml-1"
            >
              {{ tab.badge }}
            </span>
          </span>
        </slot>
      </button>
    </nav>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    required: true,
  },
  tabs: {
    type: Array,
    required: true,
    // each: { label?: String, value: String|Number, icon?: String, badge?: String|Number }
  },
  tone: {
    type: String,
    default: 'blue',
    // 'blue' | 'indigo'
  },
})

const emit = defineEmits(['update:modelValue'])

const activeClass = computed(() =>
  props.tone === 'indigo'
    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
    : 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400',
)

const inactiveClass =
  'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
</script>
