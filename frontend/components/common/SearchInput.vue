<template>
  <div class="relative flex-1 max-w-sm min-w-[200px]">
    <input
      :value="inputValue"
      type="text"
      :placeholder="placeholder"
      :aria-label="placeholder"
      :class="[inputClass, 'pl-10 pr-4']"
      @input="onInput"
    />
    <Search class="absolute left-3 top-2.5 h-4 w-4 text-content-subtle" aria-hidden="true" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@lucide/vue'
import { inputClass } from '@/utils/formStyles'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'

interface Props {
  modelValue?: string
  placeholder?: string
  /** Debounce window (ms) for emitted `input` / `update:modelValue` events. */
  debounceMs?: number
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: 'Search...',
  debounceMs: 250,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'input', value: string): void
}>()

// Local mirror of the input value so the field updates immediately on each
// keystroke — only the emitted events are debounced.
const inputValue = ref(props.modelValue)

// Keep the local mirror in sync when the parent changes modelValue externally
// (e.g. clearing the search via a filter chip).
watch(
  () => props.modelValue,
  (v) => {
    if (v !== inputValue.value) inputValue.value = v
  },
)

const emitEvents = (value: string): void => {
  emit('update:modelValue', value)
  emit('input', value)
}

const { schedule } = useDebouncedSearch(emitEvents, props.debounceMs)

function onInput(event: Event): void {
  const value = (event.target as HTMLInputElement).value
  // Update the visible value immediately — no input lag.
  inputValue.value = value
  // Debounce only the emitted events.
  schedule(value)
}
</script>
