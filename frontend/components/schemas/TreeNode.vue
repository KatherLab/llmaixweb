<template>
  <li>
    <div class="relative">
      <!-- Connection lines -->
      <div class="absolute left-0 top-0 -ml-3 mt-2.5 h-full w-0.5 bg-surface-sunken"></div>
      <div class="absolute left-0 top-2.5 -ml-3 w-3 h-0.5 bg-surface-sunken"></div>

      <!-- Node row. A div with button semantics rather than a <button>: the
           expand/collapse caret inside is a real button, and nesting buttons
           is invalid HTML with ambiguous keyboard behavior. -->
      <div
        role="button"
        tabindex="0"
        :class="[
          'w-full cursor-pointer text-left px-3 py-1.5 rounded-card text-sm transition-colors flex items-center justify-between group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          isActive
            ? 'bg-primary-soft text-primary font-medium'
            : 'hover:bg-surface-muted text-content-muted',
        ]"
        @click="navigate"
        @keydown.enter.prevent="navigate"
        @keydown.space.prevent="navigate"
      >
        <div class="flex items-center space-x-2">
          <!-- Expand/Collapse icon for containers -->
          <button
            v-if="hasChildren"
            type="button"
            class="h-3 w-3 text-content-subtle transition-transform cursor-pointer p-0 hover:text-content-muted"
            :class="{ 'rotate-90': isExpanded }"
            :aria-label="isExpanded ? $t('schemaEditor.collapse') : $t('schemaEditor.expand')"
            :aria-expanded="isExpanded"
            @click.stop="toggleExpanded"
            @keydown.enter.stop
            @keydown.space.stop
          >
            <ChevronRight />
          </button>
          <div v-else class="w-3"></div>

          <!-- Type icon -->
          <div :class="['p-1 rounded', typeColorClass]">
            <component :is="typeIcon" class="h-3 w-3 text-white" />
          </div>

          <!-- Node name -->
          <span class="truncate">
            {{ isArrayItem ? $t('schemaEditor.array_items') : nodeKey }}
          </span>
        </div>

        <!-- Type label -->
        <span class="text-xs text-content-muted ml-2">
          {{ nodeSchema.type }}
        </span>
      </div>
    </div>

    <!-- Children -->
    <ul v-if="isExpanded && hasChildren" class="mt-1 ml-6 space-y-1">
      <!-- Object properties -->
      <template v-if="nodeSchema.type === 'object' && nodeSchema.properties">
        <TreeNode
          v-for="(propSchema, propKey) in nodeSchema.properties"
          :key="propKey"
          :node-key="propKey"
          :node-schema="propSchema"
          :path="[...path, propKey]"
          :current-path="currentPath"
          @navigate="$emit('navigate', $event)"
        />
      </template>

      <!-- Array items -->
      <template v-else-if="nodeSchema.type === 'array' && nodeSchema.items">
        <TreeNode
          node-key="items"
          :node-schema="nodeSchema.items"
          :path="[...path, 'items']"
          :current-path="currentPath"
          :is-array-item="true"
          @navigate="$emit('navigate', $event)"
        />
      </template>
    </ul>
  </li>
</template>

<script setup lang="ts">
import { ref, computed, type Component } from 'vue'
import { ChevronRight } from '@lucide/vue'
import { getTypeIcon, getTypeColor } from '@/utils/schemaTypeIcons'
import type { SchemaProperty } from '@/types'

interface Props {
  nodeKey: string
  nodeSchema: SchemaProperty
  path: string[]
  currentPath?: string[]
  isArrayItem?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  currentPath: () => [],
  isArrayItem: false,
})

const emit = defineEmits<{
  navigate: [path: string[]]
}>()

const isExpanded = ref(true)

const hasChildren = computed(() => {
  return (
    (props.nodeSchema.type === 'object' &&
      props.nodeSchema.properties &&
      Object.keys(props.nodeSchema.properties).length > 0) ||
    (props.nodeSchema.type === 'array' && props.nodeSchema.items)
  )
})

const isActive = computed(() => {
  return JSON.stringify(props.path) === JSON.stringify(props.currentPath)
})

const typeColorClass = computed(() => getTypeColor(props.nodeSchema.type))

// Type Icons: shared via @/utils/schemaTypeIcons
const typeIcon = computed<Component>(() => getTypeIcon(props.nodeSchema.type))

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

const navigate = () => {
  emit('navigate', props.path)
}
</script>
