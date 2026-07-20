<template>
  <div class="schema-tree">
    <ul class="space-y-1">
      <li>
        <button
          type="button"
          :class="[
            'w-full text-left px-3 py-1.5 rounded-card text-sm transition-colors flex items-center space-x-2',
            (currentPath ?? []).length === 0
              ? 'bg-primary-soft text-primary font-medium'
              : 'hover:bg-surface-muted text-content-muted',
          ]"
          @click="$emit('navigate', [])"
        >
          <Home class="h-4 w-4" />
          <span>{{ $t('schemaEditor.tree.root') }}</span>
          <span class="text-xs text-content-muted">{{ schema.type }}</span>
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

<script setup lang="ts">
import { Home } from '@lucide/vue'
import TreeNode from './TreeNode.vue'
import type { SchemaDefinition } from '@/types'

interface Props {
  schema: SchemaDefinition
  currentPath?: string[]
}

withDefaults(defineProps<Props>(), {
  currentPath: () => [],
})

defineEmits<{
  navigate: [path: string[]]
}>()
</script>

<style scoped>
.schema-tree {
  font-size: 0.875rem;
}
</style>
