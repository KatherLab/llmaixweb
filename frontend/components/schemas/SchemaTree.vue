<template>
  <div class="schema-tree">
    <ul class="space-y-1">
      <li>
        <button
          type="button"
          :class="[
            'w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors flex items-center space-x-2',
            currentPath.length === 0
              ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
              : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300',
          ]"
          @click="$emit('navigate', [])"
        >
          <Home class="h-4 w-4" />
          <span>Root</span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{{ schema.type }}</span>
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
import { Home } from '@lucide/vue'
import TreeNode from './TreeNode.vue'

defineProps({
  schema: {
    type: Object,
    required: true,
  },
  currentPath: {
    type: Array,
    default: () => [],
  },
})

defineEmits(['navigate'])
</script>

<style scoped>
.schema-tree {
  font-size: 0.875rem;
}
</style>
