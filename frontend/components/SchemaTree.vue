<template>
  <div class="schema-tree">
    <ul class="space-y-1">
      <li>
        <button
            type="button"
          @click="$emit('navigate', [])"
          :class="[
            'w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors flex items-center space-x-2',
            currentPath.length === 0
              ? 'bg-blue-50 text-blue-700 font-medium'
              : 'hover:bg-gray-100 text-gray-700'
          ]"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <span>Root</span>
          <span class="text-xs text-gray-500">{{ schema.type }}</span>
        </button>

        <!-- Root properties -->
        <ul v-if="schema.type === 'object' && schema.properties" class="mt-1 ml-4 space-y-1">
          <TreeNode
            v-for="(propSchema, propKey) in schema.properties"
            :key="propKey"
            :node-key="propKey"
            :node-schema="propSchema"
            :path="[propKey]"
            :current-path="currentPath"
            @navigate="$emit('navigate', $event)"
          />
        </ul>

        <!-- Array items -->
        <ul v-else-if="schema.type === 'array' && schema.items" class="mt-1 ml-4 space-y-1">
          <TreeNode
            node-key="items"
            :node-schema="schema.items"
            :path="['items']"
            :current-path="currentPath"
            :is-array-item="true"
            @navigate="$emit('navigate', $event)"
          />
        </ul>
      </li>
    </ul>
  </div>
</template>

<script setup>
import TreeNode from './TreeNode.vue';

defineProps({
  schema: {
    type: Object,
    required: true
  },
  currentPath: {
    type: Array,
    default: () => []
  }
});

defineEmits(['navigate']);
</script>

<style scoped>
.schema-tree {
  font-size: 0.875rem;
}
</style>
