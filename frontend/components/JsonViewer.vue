<template>
  <div class="json-viewer">
    <div v-if="!data" class="text-gray-500 italic">null</div>
    <div v-else-if="typeof data !== 'object'" class="json-value">{{ formatValue(data) }}</div>
    <div v-else class="json-object">
      <div v-for="(value, key) in data" :key="key" class="json-item">
        <div class="json-key" @click="toggleExpanded(key)">
          <span class="toggle-icon">
            <svg
              v-if="isExpandable(value)"
              class="w-4 h-4 transition-transform"
              :class="{ 'transform rotate-90': expanded[key] }"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            <span v-else class="w-4 h-4 inline-block"></span>
          </span>
          <span class="key-name">{{ key }}:</span>
          <span v-if="!isExpandable(value) || !expanded[key]" class="json-value">
            {{ formatValue(value, !expanded[key]) }}
          </span>
        </div>
        <div v-if="isExpandable(value) && expanded[key]" class="json-children ml-4">
          <JsonViewer :data="value" :max-depth="maxDepth - 1" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';

const props = defineProps({
  data: {
    type: [Object, Array, String, Number, Boolean],
    default: null
  },
  maxDepth: {
    type: Number,
    default: 3
  }
});

const expanded = reactive({});

const isExpandable = (value) => {
  return value && typeof value === 'object' && props.maxDepth > 0;
};

const toggleExpanded = (key) => {
  if (isExpandable(props.data[key])) {
    expanded[key] = !expanded[key];
  }
};

const formatValue = (value, collapsed = false) => {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'string') return `"${value}"`;
  if (typeof value === 'boolean') return value.toString();
  if (typeof value === 'number') return value.toString();

  if (Array.isArray(value)) {
    if (collapsed) return `Array(${value.length})`;
    return `[${value.length} items]`;
  }

  if (typeof value === 'object') {
    if (collapsed) return `Object`;
    const keys = Object.keys(value);
    return `{${keys.length} properties}`;
  }

  return String(value);
};
</script>

<style scoped>
.json-viewer {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

.json-item {
  margin: 2px 0;
}

.json-key {
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  padding: 1px 0;
}

.json-key:hover {
  background-color: rgba(59, 130, 246, 0.1);
  border-radius: 2px;
}

.toggle-icon {
  width: 16px;
  display: inline-block;
  color: #6b7280;
  flex-shrink: 0;
}

.key-name {
  color: #881391;
  margin-right: 5px;
  font-weight: 500;
}

.json-value {
  color: #1a1aa6;
  word-break: break-word;
}

.json-children {
  border-left: 1px dashed #d1d5db;
  padding-left: 1rem;
  margin-left: 0.5rem;
}

.json-object > .json-item:first-child .json-children {
  margin-top: 4px;
}
</style>
