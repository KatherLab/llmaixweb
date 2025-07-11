<template>
  <li>
    <div class="relative">
      <!-- Connection lines -->
      <div class="absolute left-0 top-0 -ml-3 mt-2.5 h-full w-0.5 bg-gray-200"></div>
      <div class="absolute left-0 top-2.5 -ml-3 w-3 h-0.5 bg-gray-200"></div>

      <!-- Node button -->
      <button
        type="button"
        @click="navigate"
        :class="[
          'w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors flex items-center justify-between group',
          isActive
            ? 'bg-blue-50 text-blue-700 font-medium'
            : 'hover:bg-gray-100 text-gray-700'
        ]"
      >
        <div class="flex items-center space-x-2">
          <!-- Expand/Collapse icon for containers -->
          <button
            v-if="hasChildren"
            type="button"
            @click.stop="toggleExpanded"
            class="h-3 w-3 text-gray-400 transition-transform cursor-pointer p-0 hover:text-gray-600"
            :class="{ 'rotate-90': isExpanded }"
          >
            <svg
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
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
        <span class="text-xs text-gray-500 ml-2">
          {{ nodeSchema.type }}
        </span>
      </button>
    </div>

    <!-- Children -->
    <ul v-if="isExpanded && hasChildren" class="mt-1 ml-6 space-y-1">
      <!-- Object properties -->
      <TreeNode
        v-if="nodeSchema.type === 'object' && nodeSchema.properties"
        v-for="(propSchema, propKey) in nodeSchema.properties"
        :key="propKey"
        :node-key="propKey"
        :node-schema="propSchema"
        :path="[...path, propKey]"
        :current-path="currentPath"
        @navigate="$emit('navigate', $event)"
      />

      <!-- Array items -->
      <TreeNode
        v-else-if="nodeSchema.type === 'array' && nodeSchema.items"
        node-key="items"
        :node-schema="nodeSchema.items"
        :path="[...path, 'items']"
        :current-path="currentPath"
        :is-array-item="true"
        @navigate="$emit('navigate', $event)"
      />
    </ul>
  </li>
</template>

<script setup>
import { ref, computed, h } from 'vue';

const props = defineProps({
  nodeKey: {
    type: String,
    required: true
  },
  nodeSchema: {
    type: Object,
    required: true
  },
  path: {
    type: Array,
    required: true
  },
  currentPath: {
    type: Array,
    default: () => []
  },
  isArrayItem: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['navigate']);

const isExpanded = ref(true);

const hasChildren = computed(() => {
  return (props.nodeSchema.type === 'object' && props.nodeSchema.properties && Object.keys(props.nodeSchema.properties).length > 0) ||
         (props.nodeSchema.type === 'array' && props.nodeSchema.items);
});

const isActive = computed(() => {
  return JSON.stringify(props.path) === JSON.stringify(props.currentPath);
});

const typeColorClass = computed(() => {
  const colors = {
    string: 'bg-green-500',
    number: 'bg-blue-500',
    boolean: 'bg-purple-500',
    object: 'bg-orange-500',
    array: 'bg-pink-500'
  };
  return colors[props.nodeSchema.type] || 'bg-gray-500';
});

// Type Icons (reusing from SchemaBlock)
const StringIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z'
      })
    ]);
  }
};

const NumberIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M7 20l4-16m2 16l4-16M6 9h14M4 15h14'
      })
    ]);
  }
};

const BooleanIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
      })
    ]);
  }
};

const ObjectIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10'
      })
    ]);
  }
};

const ArrayIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M4 6h16M4 10h16M4 14h16M4 18h16'
      })
    ]);
  }
};

const typeIcon = computed(() => {
  const icons = {
    string: StringIcon,
    number: NumberIcon,
    boolean: BooleanIcon,
    object: ObjectIcon,
    array: ArrayIcon
  };
  return icons[props.nodeSchema.type] || StringIcon;
});

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value;
};

const navigate = () => {
  emit('navigate', props.path);
};
</script>
