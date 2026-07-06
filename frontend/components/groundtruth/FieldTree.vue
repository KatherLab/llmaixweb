<template>
  <ul class="pl-3">
    <li v-for="(child, key) in fields" :key="path(key)">
      <div
        class="flex items-center gap-2 py-1 px-2 -mx-2 rounded-card cursor-pointer select-none transition-colors"
        :class="{
          // selected: tinted background, accent left bar, ring — clear in both themes
          'bg-primary-soft ring-1 ring-inset ring-primary': isSelected(key) && variant === 'schema',
          'bg-purple-100/70 dark:bg-purple-500/15 ring-1 ring-inset ring-purple-400 dark:ring-purple-500':
            isSelected(key) && variant === 'groundtruth',

          // hover (only on selectable, unselected leaves)
          'hover:bg-surface-muted':
            !disabled && isLeaf(key) && !isSelected(key) && !(dimMapped && isMapped(path(key))),

          // dim already-mapped leaves unless they're the current selection
          'opacity-50': dimMapped && isLeaf(key) && isMapped(path(key)) && !isSelected(key),

          'pointer-events-none': disabled,
        }"
        :title="isLeaf(key) && isMapped(path(key)) ? 'Already mapped — click to reselect' : ''"
        @click="!disabled && isLeaf(key) && $emit('select', path(key))"
      >
        <!-- Expand/collapse indicator for objects -->
        <span v-if="isObject(child)" class="inline-flex items-center mr-0.5">
          <Folder class="w-3 h-3 text-content-subtle" />
        </span>

        <!-- Key label -->
        <span
          class="font-mono font-medium"
          :class="[
            variant === 'groundtruth'
              ? 'text-purple-700 dark:text-purple-300'
              : 'text-primary dark:text-blue-300',
            dimMapped && isLeaf(key) && isMapped(path(key)) && !isSelected(key)
              ? 'text-content-subtle'
              : '',
          ]"
        >
          {{ key }}
        </span>

        <!-- Modern type badge (only if leaf) -->
        <span
          v-if="isLeaf(key)"
          class="ml-1 px-2 py-0.5 rounded-full text-xs font-semibold font-mono"
          :class="typeBadgeClass((types ?? {})[path(key)])"
        >
          {{ badgeLabel((types ?? {})[path(key)]) }}
        </span>

        <!-- required-but-unmapped marker -->
        <span
          v-if="highlight && highlight(path(key))"
          class="ml-auto text-pink-700 dark:text-pink-300 font-bold"
          title="Required and not mapped"
          >*</span
        >

        <!-- mapped badge -->
        <span
          v-if="isLeaf(key) && isMapped(path(key)) && !isSelected(key)"
          :class="[
            'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold border border-green-200 dark:border-green-700 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300',
            highlight && highlight(path(key)) ? '' : 'ml-auto',
          ]"
        >
          <Check class="w-2.5 h-2.5" />
          <span class="sr-only">Mapped</span>
        </span>
        <!-- selected badge -->
        <span
          v-if="isSelected(key)"
          :class="[
            'inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold',
            highlight && highlight(path(key)) ? '' : 'ml-auto',
            variant === 'groundtruth'
              ? 'text-purple-700 dark:text-purple-300'
              : 'text-primary dark:text-blue-300',
          ]"
        >
          <ArrowRight class="w-3 h-3" />
          <span class="sr-only">Selected</span>
        </span>
      </div>

      <!-- Recurse: show children only for object nodes -->
      <FieldTree
        v-if="isObject(child)"
        :fields="child"
        :types="types"
        :selected="selected"
        :highlight="highlight"
        :variant="variant"
        :disabled="disabled"
        :prefix="path(key)"
        :mapped="mapped"
        :dim-mapped="dimMapped"
        @select="$emit('select', $event)"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import { ArrowRight, Check, Folder } from '@lucide/vue'
import { getTypePillClass } from '@/utils/schemaTypeIcons'
import { getPillClass } from '@/utils/statusStyles'

interface Props {
  fields?: Record<string, unknown>
  types?: Record<string, string>
  required?: string[]
  selected?: string
  highlight?: ((path: string) => boolean) | undefined
  /** Which side of the mapping this tree represents — drives selection colors. */
  variant?: 'schema' | 'groundtruth'
  disabled?: boolean
  prefix?: string
  mapped?: string[]
  dimMapped?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  fields: () => ({}),
  types: () => ({}),
  required: () => [],
  selected: '',
  highlight: undefined,
  variant: 'schema',
  disabled: false,
  prefix: '',
  mapped: () => [],
  dimMapped: true,
})

defineEmits<{ select: [path: string] }>()

const path = (key: string): string => (props.prefix ? `${props.prefix}.${key}` : key)
/** A leaf is selected when its path matches the active selection. */
const isSelected = (key: string): boolean => props.selected === path(key) && isLeaf(key)

function isObject(val: unknown): val is Record<string, unknown> {
  return !!val && typeof val === 'object' && !Array.isArray(val) && Object.keys(val).length > 0
}
function isLeaf(key: string): boolean {
  return !!props.types?.[path(key)]
}
function isMapped(p: string): boolean {
  return props.mapped?.includes?.(p) ?? false
}

function badgeLabel(type: string | undefined): string {
  switch (type) {
    case 'string':
      return 'str'
    case 'boolean':
      return 'bool'
    case 'number':
      return 'num'
    case 'array':
      return 'arr'
    case 'object':
      return 'obj'
    case 'category':
      return 'category'
    default:
      return type || ''
  }
}
function typeBadgeClass(type: string | undefined): string {
  // Schema types use the shared type→pill mapping (consistent with
  // SchemaBlock / TreeNode / VisualSchemaEditor). `category` and unknowns
  // fall back to a gray pill.
  switch (type) {
    case 'string':
    case 'number':
    case 'boolean':
    case 'object':
    case 'array':
      return getTypePillClass(type)
    case 'category':
      return getPillClass('gray')
    default:
      return getPillClass('gray')
  }
}
</script>
