<script setup lang="ts">
/**
 * Shared form field: label + input + hint/error.
 *
 * Replaces the copy-pasted `label + input + error` blocks across the auth
 * pages and AppLayout's change-password modal. Adds dark-mode variants the
 * inline copies lacked.
 *
 * v-model: binds the input value (string).
 * Slots:
 *  - hint  : helper text below the input (overrides `hint` prop)
 *  - error : error text below the input (overrides `error` prop; renders red)
 *  - trailing : inline content after the input (e.g. a "forgot password" link)
 */
import { computed, useId } from 'vue'
import { inputClass, labelClass } from '@/utils/formStyles'

interface Props {
  modelValue?: string | number
  label?: string
  type?: string
  placeholder?: string
  autocomplete?: string
  required?: boolean
  disabled?: boolean
  spellcheck?: boolean
  minlength?: string | number
  maxlength?: string | number
  // Numeric / pattern constraints (passed through to the <input>).
  min?: string | number
  max?: string | number
  step?: string | number
  pattern?: string
  // When true, renders the input with an error border (e.g. mismatch).
  invalid?: boolean
  hint?: string
  error?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  label: '',
  type: 'text',
  placeholder: '',
  autocomplete: 'off',
  required: false,
  disabled: false,
  spellcheck: true,
  minlength: undefined,
  maxlength: undefined,
  min: undefined,
  max: undefined,
  step: undefined,
  pattern: undefined,
  invalid: false,
  hint: '',
  error: '',
})

const emit = defineEmits<{ (e: 'update:modelValue', value: string | number): void }>()

const inputId = useId()

const inputClasses = computed(() => [
  inputClass,
  props.invalid || props.error
    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800'
    : '',
])
</script>

<template>
  <div>
    <label v-if="label" :for="inputId" :class="labelClass">
      {{ label }}
    </label>
    <div class="relative">
      <input
        :id="inputId"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :required="required"
        :disabled="disabled"
        :spellcheck="spellcheck"
        :minlength="minlength"
        :maxlength="maxlength"
        :min="min"
        :max="max"
        :step="step"
        :pattern="pattern"
        :class="inputClasses"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <div v-if="$slots.trailing" class="mt-1 text-right">
        <slot name="trailing" />
      </div>
    </div>
    <p v-if="$slots.hint" class="mt-1 text-xs text-slate-500 dark:text-slate-400">
      <slot name="hint" />
    </p>
    <p v-else-if="hint" class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ hint }}</p>
    <p v-if="$slots.error" class="mt-1 text-xs text-red-500 dark:text-red-400">
      <slot name="error" />
    </p>
    <p v-else-if="error" class="mt-1 text-xs text-red-500 dark:text-red-400">{{ error }}</p>
  </div>
</template>
