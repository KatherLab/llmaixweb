<template>
  <ul class="pl-4">
    <li v-for="(child, key) in fields" :key="path(key)">
      <div
        class="flex items-center gap-2 py-0.5 rounded-lg group cursor-pointer select-none transition"
        :class="{
          'bg-gradient-to-r from-blue-100/70 to-blue-50/80 shadow border border-blue-300': selected === path(key) && isLeaf(key),
          'bg-gradient-to-r from-purple-100/80 to-blue-50/60 border border-purple-300': selected === path(key) && nodeColor==='text-purple-700' && isLeaf(key),
          'hover:bg-blue-50/60': !disabled && isLeaf(key),
          'opacity-50 pointer-events-none': disabled,
        }"
        @click="!disabled && isLeaf(key) && $emit('select', path(key))"
      >
        <!-- Expand/collapse toggler for objects -->
        <span v-if="isObject(child)" class="inline-flex items-center mr-0.5">
          <svg class="w-3 h-3 text-gray-300" fill="none" viewBox="0 0 16 16">
            <rect x="2" y="6" width="12" height="4" rx="1.5" fill="currentColor"/>
          </svg>
        </span>
        <!-- Key label -->
        <span
          class="font-mono font-medium text-gray-900"
          :class="{ 'text-purple-700': nodeColor==='text-purple-700', 'text-blue-700': nodeColor==='text-blue-700' }"
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
        <span v-if="highlight && highlight(path(key))" class="ml-1 text-pink-700 font-bold">*</span>
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
});
const emit = defineEmits(['select']);
const path = (key) => props.prefix ? `${props.prefix}.${key}` : key;
function isObject(val) {
  return val && typeof val === 'object' && Object.keys(val).length > 0;
}
function isLeaf(key) {
  return !!props.types?.[path(key)];
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
