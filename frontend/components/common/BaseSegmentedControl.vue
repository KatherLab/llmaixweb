<script setup>
/**
 * Shared pill-style segmented control (mutually-exclusive single-select).
 *
 * Replaces the copy-pasted Simple/Advanced toggle in SchemaFormModal,
 * PromptFormModal, and CreateTrialModal — one visual idiom for "pick one of
 * a few modes". For 3+ options or label-driven nav, prefer BaseTabGroup
 * (underline style) instead.
 *
 * v-model holds the active option's `value`.
 *
 * Props:
 *  - modelValue : the active option's value (String|Number|Boolean)
 *  - options    : [{ label, value }] (label is shown; value is the v-model key)
 *  - size       : 'sm' | 'md' (default 'md')
 */
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: '' },
  options: { type: Array, required: true },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md'].includes(v),
  },
})

const emit = defineEmits(['update:modelValue'])

const padClass = computed(() =>
  props.size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm',
)
</script>

<template>
  <div class="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
    <button
      v-for="opt in options"
      :key="String(opt.value)"
      type="button"
      :class="[
        padClass,
        'font-medium rounded-md transition-all',
        modelValue === opt.value
          ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
          : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white',
      ]"
      @click="emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>
