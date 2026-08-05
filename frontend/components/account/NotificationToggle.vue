<template>
  <div class="flex items-start justify-between gap-4 py-3">
    <div class="min-w-0">
      <label :for="id" class="block text-sm font-medium text-content cursor-pointer">
        {{ label }}
      </label>
      <p v-if="description" class="mt-0.5 text-xs text-content-subtle">
        {{ description }}
      </p>
    </div>
    <!--
      A <button role="switch"> rather than a styled checkbox: it carries the
      on/off semantics screen readers announce, keeps Space/Enter working without
      extra handlers, and lets the label point at it via `for`/`id`.
    -->
    <button
      :id="id"
      type="button"
      role="switch"
      :aria-checked="modelValue"
      :disabled="disabled"
      class="relative shrink-0 mt-0.5 inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-50 disabled:cursor-not-allowed"
      :class="modelValue ? 'bg-primary' : 'bg-surface-sunken ring-1 ring-default-border'"
      @click="toggle"
    >
      <span
        class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
        :class="modelValue ? 'translate-x-6' : 'translate-x-1'"
      />
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  label: string
  description?: string
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  description: undefined,
  disabled: false,
})

const modelValue = defineModel<boolean>({ required: true })

// Unique per instance so the <label for> association survives several toggles
// rendered in the same card.
const id = `notif-toggle-${Math.random().toString(36).slice(2, 9)}`

function toggle(): void {
  modelValue.value = !modelValue.value
}
</script>
