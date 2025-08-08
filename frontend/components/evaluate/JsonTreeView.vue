<template>
  <div class="json-tree">
    <div v-for="(value, key) in data" :key="key" class="ml-4">
      <div v-if="isObject(value) && currentDepth < maxDepth" class="my-1">
        <button @click="toggleExpanded(key)" class="text-gray-700 hover:text-blue-600 flex items-center">
          <span class="mr-1">{{ expanded[key] ? '▼' : '▶' }}</span>
          <span class="font-medium">{{ key }}:</span>
          <span class="text-gray-500 ml-1 text-xs">{Object}</span>
        </button>
        <div v-if="expanded[key]" class="ml-2">
          <JsonTreeView :data="value" :max-depth="maxDepth" :current-depth="currentDepth + 1" />
        </div>
      </div>
      <div v-else class="my-1 flex items-start">
        <span class="font-medium text-gray-700 mr-2">{{ key }}:</span>
        <span class="text-gray-600">{{ formatValue(value) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  data: {
    type: Object,
    required: true
  },
  maxDepth: {
    type: Number,
    default: 3
  },
  currentDepth: {
    type: Number,
    default: 0
  }
});

const expanded = ref({});

const isObject = (val) => val && typeof val === 'object' && !Array.isArray(val);

const formatValue = (val) => {
  if (val === null) return 'null';
  if (val === undefined) return 'undefined';
  if (Array.isArray(val)) return `[Array: ${val.length} items]`;
  if (isObject(val)) return '{...}';
  if (typeof val === 'string' && val.length > 50) {
    return `"${val.substring(0, 50)}..."`;
  }
  if (typeof val === 'string') return `"${val}"`;
  return String(val);
};

const toggleExpanded = (key) => {
  expanded.value[key] = !expanded.value[key];
};
</script>

<style scoped>
.json-tree {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
}
</style>
