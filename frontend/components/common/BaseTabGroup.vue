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
  <div class="border-b border-default">
    <nav class="-mb-px flex space-x-8" role="tablist">
      <component
        :is="tab.to ? 'router-link' : 'button'"
        v-for="tab in tabs"
        :key="tab.value"
        :type="tab.to ? undefined : 'button'"
        :to="tab.to"
        role="tab"
        :aria-selected="modelValue === tab.value"
        :class="[
          'py-2 px-1 border-b-2 font-medium text-sm transition-colors',
          modelValue === tab.value ? activeClass : inactiveClass,
        ]"
        @click="!tab.to && emit('update:modelValue', tab.value)"
      >
        <slot name="tab" :tab="tab">
          <span class="flex items-center gap-2">
            <span v-if="tab.icon" class="text-lg">{{ tab.icon }}</span>
            {{ tab.label }}
            <span
              v-if="tab.badge !== undefined && tab.badge !== null"
              class="bg-surface-sunken text-content-muted px-2 py-0.5 rounded-full text-xs ml-1"
            >
              {{ tab.badge }}
            </span>
          </span>
        </slot>
      </component>
    </nav>
  </div>
</template>

<script setup lang="ts">
export interface TabItem {
  label?: string
  value: string | number
  icon?: string
  badge?: string | number | null
  // When `to` is set, the tab renders as a <router-link> (URL-driven tabs).
  to?: string
}

interface Props {
  modelValue: string | number
  tabs?: TabItem[]
}

withDefaults(defineProps<Props>(), {
  tabs: () => [],
})

const emit = defineEmits<{ (e: 'update:modelValue', value: string | number): void }>()

const activeClass = 'border-primary text-primary'

const inactiveClass = 'border-transparent text-content-muted hover:text-content hover:border-strong'
</script>
