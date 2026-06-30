<script setup>
/**
 * Shared password input with a show/hide toggle and a strength meter.
 *
 * Unifies the password UX across all auth/admin flows (register, first-admin,
 * reset-password, account change-password, admin set-password) so the minimum
 * length and strength feedback are consistent everywhere. The strength score is
 * client-side guidance only — the backend enforces the real policy.
 *
 * v-model: binds the password string.
 */
import { computed, ref } from 'vue'
import { Eye, EyeOff } from '@lucide/vue'
import { inputClass, labelClass } from '@/utils/formStyles'
import { useId } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Password' },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'new-password' },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  minlength: { type: [String, Number], default: 8 },
  maxlength: { type: [String, Number], default: 128 },
  // Hide the strength meter (e.g. admin set-password, where guidance is noise).
  showStrength: { type: Boolean, default: true },
  // Render with an error border.
  invalid: { type: Boolean, default: false },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const inputId = useId()
const show = ref(false)

const inputClasses = computed(() => [
  inputClass,
  'pr-10',
  props.invalid || props.error
    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-800'
    : '',
])

// Simple, deterministic strength score (length + character-class diversity).
// Mirrors the backend policy intent (min length + upper/lower/digit) without
// duplicating the rules — it's guidance, not enforcement.
const strength = computed(() => {
  const pw = props.modelValue || ''
  if (!pw) return { score: 0, label: '', color: 'bg-slate-200 dark:bg-slate-700' }
  let classes = 0
  if (/[a-z]/.test(pw)) classes++
  if (/[A-Z]/.test(pw)) classes++
  if (/[0-9]/.test(pw)) classes++
  if (/[^A-Za-z0-9]/.test(pw)) classes++
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  score += Math.max(0, classes - 1) // 0..3 from diversity
  // Clamp to 0..4
  score = Math.min(4, score)
  const labels = ['Very weak', 'Weak', 'Okay', 'Good', 'Strong']
  const colors = ['bg-red-500', 'bg-red-400', 'bg-amber-400', 'bg-green-500', 'bg-green-600']
  return {
    score,
    label: pw.length < 8 ? 'Minimum 8 characters' : labels[score],
    color: colors[score],
  }
})

const segments = computed(() => {
  const s = strength.value.score
  return [1, 2, 3, 4].map((i) => (i <= s ? strength.value.color : 'bg-slate-200 dark:bg-slate-700'))
})
</script>

<template>
  <div>
    <label v-if="label" :for="inputId" :class="labelClass">{{ label }}</label>
    <div class="relative">
      <input
        :id="inputId"
        :type="show ? 'text' : 'password'"
        :value="modelValue"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :required="required"
        :disabled="disabled"
        :minlength="minlength"
        :maxlength="maxlength"
        :class="inputClasses"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <button
        type="button"
        class="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
        :aria-label="show ? 'Hide password' : 'Show password'"
        :aria-pressed="show"
        tabindex="-1"
        @click="show = !show"
      >
        <EyeOff v-if="show" class="h-4 w-4" aria-hidden="true" />
        <Eye v-else class="h-4 w-4" aria-hidden="true" />
      </button>
    </div>

    <div v-if="showStrength" class="mt-2">
      <div class="flex gap-1">
        <div
          v-for="(seg, i) in segments"
          :key="i"
          class="h-1.5 flex-1 rounded-full transition-colors"
          :class="seg"
        />
      </div>
      <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ strength.label }}</p>
    </div>

    <p v-if="hint" class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ hint }}</p>
    <p v-if="error" class="mt-1 text-xs text-red-500 dark:text-red-400">{{ error }}</p>
  </div>
</template>
