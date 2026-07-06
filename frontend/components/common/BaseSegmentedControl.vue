<script setup lang="ts">
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

export interface SegmentedOption {
  label: string
  value: string | number | boolean
}

interface Props {
  modelValue?: string | number | boolean
  options: SegmentedOption[]
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  size: 'md',
})

const emit = defineEmits<{ (e: 'update:modelValue', value: string | number | boolean): void }>()

const padClass = computed(() =>
  props.size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm',
)
</script>

<template>
  <div class="inline-flex items-center gap-1 bg-surface-sunken rounded-card p-1">
    <button
      v-for="opt in options"
      :key="String(opt.value)"
      type="button"
      :class="[
        padClass,
        'font-medium rounded-card transition-all',
        modelValue === opt.value
          ? 'bg-surface text-content shadow-sm'
          : 'text-content-muted hover:text-content',
      ]"
      @click="emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>
