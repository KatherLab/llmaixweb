<template>
  <div class="json-viewer">
    <div v-if="!data" class="text-gray-500 italic text-xs">null</div>
    <div v-else-if="typeof data !== 'object'" class="json-value text-xs">{{ formatValue(data) }}</div>
    <div v-else class="json-object">
      <div v-for="(value, key) in data" :key="key" class="json-item">
        <div class="json-key" @click="toggleExpanded(key)">
          <span class="toggle-icon">
            <span
              v-if="isExpandable(value)"
              class="w-3 h-3 transition-transform text-gray-400 cursor-pointer inline-block"
              :class="{ 'transform rotate-90': expanded[key] }"
            >
              ▶
            </span>
            <span v-else class="w-3 h-3 inline-block"></span>
          </span>
          <span class="key-name text-xs font-medium text-purple-700">{{ key }}:</span>
          <span v-if="!isExpandable(value) || !expanded[key]" class="json-value text-xs ml-1">
            {{ formatValue(value, !expanded[key]) }}
          </span>
        </div>
        <div v-if="isExpandable(value) && expanded[key]" class="json-children ml-3 pl-2 border-l border-gray-200">
          <JsonViewer :data="value" :max-depth="maxDepth - 1" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue';

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
  font-size: 0.75rem;
  line-height: 1.4;
}

.json-item {
  margin: 1px 0;
}

.json-key {
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  padding: 1px 0;
  border-radius: 2px;
}

.json-key:hover {
  background-color: rgba(99, 102, 241, 0.05);
}

.toggle-icon {
  width: 12px;
  display: inline-block;
  flex-shrink: 0;
  margin-right: 2px;
}

.key-name {
  margin-right: 4px;
  font-weight: 500;
}

.json-value {
  color: #1e40af;
  word-break: break-word;
}
</style>
