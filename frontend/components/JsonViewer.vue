<template>
  <div class="json-viewer">
    <div v-for="(value, key) in parsedData" :key="key" class="json-item">
      <div class="json-key" @click="toggle(key)">
        <span class="toggle-icon">{{ isObject(value) ? (isExpanded(key) ? '▼' : '►') : ' ' }}</span>
        <span class="key-name">{{ key }}:</span>
        <span v-if="!isObject(value)" class="json-value">{{ formatValue(value) }}</span>
        <button
          v-if="!isObject(value)"
          @click.stop="copyValue(value)"
          class="ml-2 text-gray-400 hover:text-gray-600 text-xs"
          title="Copy value"
        >
          <svg class="w-3 h-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
            <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
          </svg>
        </button>
      </div>
      <div v-if="isObject(value) && isExpanded(key)" class="json-children">
        <JsonViewer :data="value" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useToast } from 'vue-toastification';

const props = defineProps({
  data: {
    type: [Object, Array],
    required: true
  }
});

const toast = useToast();
const expanded = ref({});

const parsedData = computed(() => {
  if (!props.data) return {};

  // Handle both objects and arrays
  if (Array.isArray(props.data)) {
    return Object.fromEntries(
      props.data.map((item, index) => [`[${index}]`, item])
    );
  }

  return props.data;
});

const isObject = (value) => {
  return value !== null && typeof value === 'object';
};

const toggle = (key) => {
  expanded.value[key] = !expanded.value[key];
};

const isExpanded = (key) => {
  return !!expanded.value[key];
};

const formatValue = (value) => {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'string') return `"${value}"`;
  return String(value);
};

const copyValue = (value) => {
  try {
    const stringValue = typeof value === 'object'
      ? JSON.stringify(value)
      : String(value);

    navigator.clipboard.writeText(stringValue);
    toast.success('Copied to clipboard!');
  } catch (err) {
    console.error('Failed to copy:', err);
    toast.error('Failed to copy to clipboard');
  }
};
</script>

<style scoped>
.json-viewer {
  font-family: monospace;
  font-size: 14px;
}

.json-item {
  margin: 2px 0;
}

.json-key {
  cursor: pointer;
  display: flex;
  align-items: flex-start;
}

.toggle-icon {
  width: 16px;
  display: inline-block;
}

.key-name {
  color: #881391;
  margin-right: 5px;
}

.json-value {
  color: #1a1aa6;
}

.json-children {
  border-left: 1px dashed #ccc;
  padding-left: 1rem;
}
</style>
