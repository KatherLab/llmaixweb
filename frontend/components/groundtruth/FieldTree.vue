<template>
  <ul class="pl-4">
    <li v-for="(child, key) in fields" :key="path(key)">
      <div
        class="flex items-center gap-2 py-0.5 rounded-lg group cursor-pointer select-none transition"
        :class="{
          // selected states (win over dimming)
          'bg-gradient-to-r from-blue-100/70 to-blue-50/80 shadow border border-blue-300':
            selected === path(key) && isLeaf(key) && nodeColor==='text-blue-700',
          'bg-gradient-to-r from-purple-100/80 to-blue-50/60 border border-purple-300':
            selected === path(key) && isLeaf(key) && nodeColor==='text-purple-700',

          // normal hover (only when not dimmed)
          'hover:bg-blue-50/60':
            !disabled && isLeaf(key) && !(dimMapped && isMapped(path(key))),

          // dim mapped leaves unless selected
          'opacity-50':
            dimMapped && isLeaf(key) && isMapped(path(key)) && selected !== path(key),

          // disabled whole tree
          'pointer-events-none': disabled,
        }"
        @click="!disabled && isLeaf(key) && $emit('select', path(key))"
        :title="isLeaf(key) && isMapped(path(key)) ? 'Already mapped' : ''"
      >
        <!-- Expand/collapse indicator for objects -->
        <span v-if="isObject(child)" class="inline-flex items-center mr-0.5">
          <svg class="w-3 h-3 text-gray-300" fill="none" viewBox="0 0 16 16">
            <rect x="2" y="6" width="12" height="4" rx="1.5" fill="currentColor"/>
          </svg>
        </span>

        <!-- Key label -->
        <span
          class="font-mono font-medium text-gray-900"
          :class="[
            nodeColor==='text-purple-700' ? 'text-purple-700' : 'text-blue-700',
            (dimMapped && isLeaf(key) && isMapped(path(key)) && selected !== path(key)) ? 'text-gray-400' : ''
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
          ✓
          <span class="sr-only">Mapped</span>
        </span>

        <!-- required-but-unmapped marker -->
        <span
          v-if="highlight && highlight(path(key))"
          class="ml-1 text-pink-700 font-bold"
          title="Required and not mapped"
        >*</span>
      </div>

      <!-- Recurse: show children only for object nodes -->
      <FieldTree
        v-if="isObject(child)"
        :fields="child"
        :types="types"
        :selected="selected"
        :highlight="highlight"
        :nodeColor="nodeColor"
        :disabled="disabled"
        :prefix="path(key)"
        :mapped="mapped"
        :dimMapped="dimMapped"
        @select="$emit('select', $event)"
      />
    </li>
  </ul>
</template>

<script setup>
const props = defineProps({
  fields: Object,
  types: Object,
  required: Array,
  selected: String,
  highlight: Function,
  nodeColor: { type: String, default: "text-blue-700" },
  disabled: Boolean,
  prefix: { type: String, default: "" },
  mapped: { type: Array, default: () => [] },     // paths already mapped
  dimMapped: { type: Boolean, default: true },    // allow parent to toggle (optional)
});
const emit = defineEmits(['select']);

const path = (key) => props.prefix ? `${props.prefix}.${key}` : key;

function isObject(val) {
  return val && typeof val === 'object' && Object.keys(val).length > 0;
}
function isLeaf(key) {
  return !!props.types?.[path(key)];
}
function isMapped(p) {
  return props.mapped?.includes?.(p);
}

function badgeLabel(type) {
  switch (type) {
    case "string": return "str";
    case "boolean": return "bool";
    case "number": return "num";
    case "array": return "arr";
    case "object": return "obj";
    case "category": return "category";
    default: return type || "";
  }
}
function typeBadgeClass(type) {
  switch (type) {
    case "string": return "bg-blue-100 text-blue-700 border border-blue-200";
    case "boolean": return "bg-purple-100 text-purple-700 border border-purple-200";
    case "number": return "bg-pink-100 text-pink-700 border border-pink-200";
    case "array": return "bg-green-100 text-green-700 border border-green-200";
    case "object": return "bg-orange-100 text-orange-700 border border-orange-200";
    case "category": return "bg-gray-100 text-gray-600 border border-gray-300";
    default: return "bg-gray-100 text-gray-500 border border-gray-200";
  }
}
</script>
