<template>
  <li>
    <div class="relative">
      <!-- Connection lines -->
      <div
        class="absolute left-0 top-0 -ml-3 mt-2.5 h-full w-0.5 bg-slate-200 dark:bg-slate-700"
      ></div>
      <div class="absolute left-0 top-2.5 -ml-3 w-3 h-0.5 bg-slate-200 dark:bg-slate-700"></div>

      <!-- Node button -->
      <button
        type="button"
        :class="[
          'w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors flex items-center justify-between group',
          isActive
            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
            : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300',
        ]"
        @click="navigate"
      >
        <div class="flex items-center space-x-2">
          <!-- Expand/Collapse icon for containers -->
          <button
            v-if="hasChildren"
            type="button"
            class="h-3 w-3 text-slate-400 dark:text-slate-500 transition-transform cursor-pointer p-0 hover:text-slate-600 dark:hover:text-slate-300"
            :class="{ 'rotate-90': isExpanded }"
            @click.stop="toggleExpanded"
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
            {{ isArrayItem ? 'Array Items' : nodeKey }}
          </span>
        </div>

        <!-- Type label -->
        <span class="text-xs text-slate-500 dark:text-slate-400 ml-2">
          {{ nodeSchema.type }}
        </span>
      </button>
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

<script setup>
import { ref, computed } from 'vue'
import { ChevronRight } from '@lucide/vue'
import { getTypeIcon, getTypeColor } from '@/utils/schemaTypeIcons'

const props = defineProps({
  nodeKey: {
    type: String,
    required: true,
  },
  nodeSchema: {
    type: Object,
    required: true,
  },
  path: {
    type: Array,
    required: true,
  },
  currentPath: {
    type: Array,
    default: () => [],
  },
  isArrayItem: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['navigate'])

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
const typeIcon = computed(() => getTypeIcon(props.nodeSchema.type))

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

const navigate = () => {
  emit('navigate', props.path)
}
</script>
