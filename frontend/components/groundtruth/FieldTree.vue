<template>
  <ul class="pl-4">
    <li v-for="(child, key) in fields" :key="path(key)">
      <div
        class="flex items-center gap-2 py-0.5 rounded-lg group cursor-pointer select-none transition"
        :class="{
          // selected states (win over dimming)
          'bg-gradient-to-r from-blue-100/70 to-blue-50/80 shadow border border-blue-300':
            selected === path(key) && isLeaf(key) && nodeColor === 'text-blue-700',
          'bg-gradient-to-r from-purple-100/80 to-blue-50/60 border border-purple-300':
            selected === path(key) && isLeaf(key) && nodeColor === 'text-purple-700',

          // normal hover (only when not dimmed)
          'hover:bg-blue-50/60': !disabled && isLeaf(key) && !(dimMapped && isMapped(path(key))),

          // dim mapped leaves unless selected
          'opacity-50': dimMapped && isLeaf(key) && isMapped(path(key)) && selected !== path(key),

          // disabled whole tree
          'pointer-events-none': disabled,
        }"
        :title="isLeaf(key) && isMapped(path(key)) ? 'Already mapped' : ''"
        @click="!disabled && isLeaf(key) && $emit('select', path(key))"
      >
        <!-- Expand/collapse indicator for objects -->
        <span v-if="isObject(child)" class="inline-flex items-center mr-0.5">
          <Folder class="w-3 h-3 text-slate-300" />
        </span>

        <!-- Key label -->
        <span
          class="font-mono font-medium text-slate-900"
          :class="[
            nodeColor === 'text-purple-700' ? 'text-purple-700' : 'text-blue-700',
            dimMapped && isLeaf(key) && isMapped(path(key)) && selected !== path(key)
              ? 'text-slate-400'
              : '',
          ]"
        >
          {{ key }}
        </span>

        <!-- Modern type badge (only if leaf) -->
        <span
          v-if="isLeaf(key)"
          class="ml-1 px-2 py-0.5 rounded-full text-xs font-semibold font-mono"
          :class="typeBadgeClass(types[path(key)])"
        >
          {{ badgeLabel(types[path(key)]) }}
        </span>

        <!-- mapped badge -->
        <span
          v-if="isLeaf(key) && isMapped(path(key))"
          class="ml-1 inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold border border-green-200 bg-green-50 text-green-700"
        >
          <Check class="w-2.5 h-2.5" />
          <span class="sr-only">Mapped</span>
        </span>

        <!-- required-but-unmapped marker -->
        <span
          v-if="highlight && highlight(path(key))"
          class="ml-1 text-pink-700 font-bold"
          title="Required and not mapped"
          >*</span
        >
      </div>

      <!-- Recurse: show children only for object nodes -->
      <FieldTree
        v-if="isObject(child)"
        :fields="child"
        :types="types"
        :selected="selected"
        :highlight="highlight"
        :node-color="nodeColor"
        :disabled="disabled"
        :prefix="path(key)"
        :mapped="mapped"
        :dim-mapped="dimMapped"
        @select="$emit('select', $event)"
      />
    </li>
  </ul>
</template>

<script setup>
import { Check, Folder } from '@lucide/vue'
import { getTypePillClass } from '@/utils/schemaTypeIcons'
import { getPillClass } from '@/utils/statusStyles'

const props = defineProps({
  fields: { type: Object, default: () => ({}) },
  types: { type: Object, default: () => ({}) },
  required: { type: Array, default: () => [] },
  selected: { type: String, default: '' },
  highlight: { type: Function, default: undefined },
  nodeColor: { type: String, default: 'text-blue-700' },
  disabled: Boolean,
  prefix: { type: String, default: '' },
  mapped: { type: Array, default: () => [] }, // paths already mapped
  dimMapped: { type: Boolean, default: true }, // allow parent to toggle (optional)
})
const emit = defineEmits(['select'])

const path = (key) => (props.prefix ? `${props.prefix}.${key}` : key)

function isObject(val) {
  return val && typeof val === 'object' && Object.keys(val).length > 0
}
function isLeaf(key) {
  return !!props.types?.[path(key)]
}
function isMapped(p) {
  return props.mapped?.includes?.(p)
}

function badgeLabel(type) {
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
function typeBadgeClass(type) {
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
