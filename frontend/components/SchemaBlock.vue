<template>
  <div class="schema-block">
    <!-- Main Block Container -->
    <div
      :class="[
        'rounded-lg shadow-sm border-2 overflow-hidden transition-all',
        blockColorClass,
        'hover:shadow-md'
      ]"
    >
      <!-- Block Header -->
      <div :class="['px-4 py-3', headerColorClass]">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <!-- Type Icon -->
            <div class="bg-white/20 rounded-lg p-2">
              <component :is="typeIcon" class="h-5 w-5 text-white" />
            </div>

            <!-- Schema Info -->
            <div>
              <h3 class="text-white font-medium">
                {{ schema.title || formatTitle(path[path.length - 1]) || 'Root Schema' }}
              </h3>
              <p class="text-white/80 text-sm">
                {{ typeLabel }}
                <span v-if="schema.description" class="ml-2 text-xs">
                  • {{ schema.description }}
                </span>
              </p>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center space-x-2">
            <!-- Edit Root Schema Button (for root level) -->
            <button
              v-if="path.length === 0"
              type="button"
              @click="$emit('edit-root')"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Edit Schema Settings"
            >
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>

            <!-- Add Property Button (for objects) -->
            <button
              v-if="schema.type === 'object'"
              type="button"
              @click="$emit('add-property')"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Add Property"
            >
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </button>

            <!-- Edit Button -->
            <button
              type="button"
              @click="showDetails = !showDetails"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              :title="showDetails ? 'Hide Details' : 'Show Details'"
            >
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  :d="showDetails ? 'M19 9l-7 7-7-7' : 'M9 5l7 7-7 7'" />
              </svg>
            </button>
          </div>
        </div>
      </div>


      <!-- Block Details -->
      <transition
        enter-active-class="transition-all duration-200 ease-out"
        leave-active-class="transition-all duration-200 ease-in"
        enter-from-class="max-h-0 opacity-0"
        enter-to-class="max-h-96 opacity-100"
        leave-from-class="max-h-96 opacity-100"
        leave-to-class="max-h-0 opacity-0"
      >
        <div v-if="showDetails" class="bg-white border-t">
          <div class="p-4 space-y-3">
            <!-- Type-specific constraints -->
            <div v-if="schema.type === 'string'" class="grid grid-cols-2 gap-3">
              <div v-if="schema.minLength !== undefined">
                <label class="block text-xs font-medium text-gray-600">Min Length</label>
                <p class="text-sm text-gray-900">{{ schema.minLength }}</p>
              </div>
              <div v-if="schema.maxLength !== undefined">
                <label class="block text-xs font-medium text-gray-600">Max Length</label>
                <p class="text-sm text-gray-900">{{ schema.maxLength }}</p>
              </div>
              <div v-if="schema.pattern" class="col-span-2">
                <label class="block text-xs font-medium text-gray-600">Pattern</label>
                <code class="text-xs bg-gray-100 px-2 py-1 rounded">{{ schema.pattern }}</code>
              </div>
              <div v-if="schema.format" class="col-span-2">
                <label class="block text-xs font-medium text-gray-600">Format</label>
                <span class="text-sm text-gray-900">{{ schema.format }}</span>
              </div>
            </div>

            <div v-if="schema.type === 'number'" class="grid grid-cols-2 gap-3">
              <div v-if="schema.minimum !== undefined">
                <label class="block text-xs font-medium text-gray-600">Minimum</label>
                <p class="text-sm text-gray-900">{{ schema.minimum }}</p>
              </div>
              <div v-if="schema.maximum !== undefined">
                <label class="block text-xs font-medium text-gray-600">Maximum</label>
                <p class="text-sm text-gray-900">{{ schema.maximum }}</p>
              </div>
            </div>

            <!-- Enum values -->
            <div v-if="schema.enum && schema.enum.length > 0" class="bg-blue-50 rounded-lg p-3">
              <label class="block text-xs font-medium text-blue-900 mb-2 flex items-center">
                <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                Allowed Values
              </label>
              <div class="grid grid-cols-2 gap-2">
                <div
                  v-for="(value, index) in schema.enum"
                  :key="index"
                  class="flex items-center space-x-2 bg-white rounded-md px-3 py-2 shadow-sm"
                >
                  <span class="text-blue-600 font-medium text-lg">{{ index + 1 }}</span>
                  <span class="text-sm text-gray-900 font-medium">{{ value }}</span>
                </div>
              </div>
            </div>

            <!-- Required fields (for objects) -->
            <div v-if="schema.type === 'object' && schema.required && schema.required.length > 0">
              <label class="block text-xs font-medium text-gray-600 mb-1">Required Fields</label>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="field in schema.required"
                  :key="field"
                  class="px-2 py-1 bg-red-100 text-red-700 rounded text-xs"
                >
                  {{ field }}
                </span>
              </div>
            </div>

            <!-- Default value -->
            <div v-if="schema.default !== undefined">
              <label class="block text-xs font-medium text-gray-600">Default Value</label>
              <p class="text-sm text-gray-900">{{ JSON.stringify(schema.default) }}</p>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- Object Properties -->
    <div v-if="schema.type === 'object' && schema.properties" class="mt-4 ml-6">
      <div class="relative">
        <!-- Connection Line -->
        <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-gray-300"></div>

        <!-- Properties -->
        <div class="space-y-3 pl-6">
          <div
            v-for="(propSchema, propKey) in schema.properties"
            :key="propKey"
            class="relative"
          >
            <!-- Horizontal Connection -->
            <div class="absolute -left-6 top-6 w-6 h-0.5 bg-gray-300"></div>

            <!-- Property Block -->
            <div class="bg-white rounded-lg shadow-sm border p-3 hover:shadow-md hover:border-blue-300 transition-all duration-200 cursor-pointer group">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <code class="text-sm font-medium text-gray-700">{{ propKey }}</code>
                  <span
                    v-if="schema.required && schema.required.includes(propKey)"
                    class="text-xs text-red-600"
                  >
                    *required
                  </span>
                </div>
                <div class="flex items-center space-x-1">
                  <button
                    type="button"
                    @click="$emit('edit-property', { key: propKey, schema: propSchema })"
                    class="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                    title="Edit Property"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    v-if="propSchema.type === 'object' || propSchema.type === 'array'"
                    type="button"
                    @click="$emit('navigate', propKey)"
                    class="p-1 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded"
                    title="Navigate Into"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    @click="$emit('delete-property', propKey)"
                    class="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
                    title="Delete Property"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Mini Type Badge -->
              <div class="flex items-center space-x-2">
                <span :class="['px-2 py-0.5 rounded text-xs font-medium', getTypeBadgeClass(propSchema.type)]">
                  {{ getTypeLabel(propSchema.type) }}
                </span>
                <span v-if="propSchema.title" class="text-xs text-gray-600">
                  {{ propSchema.title }}
                </span>
              </div>

              <!-- Enum preview -->
              <div v-if="propSchema.enum && propSchema.enum.length > 0" class="mt-1">
                <span class="text-xs text-gray-500">
                  Options: {{ propSchema.enum.slice(0, 3).join(', ') }}
                  <span v-if="propSchema.enum.length > 3">...</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Array Items -->
    <div v-if="schema.type === 'array' && schema.items" class="mt-4 ml-6">
      <div class="relative">
        <!-- Connection Line -->
        <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-gray-300"></div>

        <!-- Array Item Schema -->
        <div class="pl-6">
          <!-- Horizontal Connection -->
          <div class="absolute left-0 top-6 w-6 h-0.5 bg-gray-300"></div>

          <div class="bg-white rounded-lg shadow-sm border p-3">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-gray-700">Array Items</span>
              <div class="flex items-center space-x-1">
                <button
                  type="button"
                  @click="$emit('edit-property', { key: 'items', schema: schema.items })"
                  class="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                  title="Edit Array Items"
                >
                  <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  v-if="schema.items.type === 'object'"
                  type="button"
                  @click="$emit('navigate', 'items')"
                  class="p-1 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded"
                  title="Navigate Into Items"
                >
                  <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </button>
              </div>
            </div>

            <span :class="['px-2 py-0.5 rounded text-xs font-medium', getTypeBadgeClass(schema.items.type)]">
              {{ getTypeLabel(schema.items.type) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h, onMounted } from 'vue';

const props = defineProps({
  schema: {
    type: Object,
    required: true
  },
  path: {
    type: Array,
    default: () => []
  },
  advancedMode: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update', 'add-property', 'edit-property', 'delete-property', 'navigate', 'edit-root']);

const showDetails = ref(false);

// Type Icons
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

// Computed properties
const typeIcon = computed(() => {
  const icons = {
    string: StringIcon,
    number: NumberIcon,
    boolean: BooleanIcon,
    object: ObjectIcon,
    array: ArrayIcon
  };
  return icons[props.schema.type] || StringIcon;
});

const typeLabel = computed(() => {
  return getTypeLabel(props.schema.type);
});

const blockColorClass = computed(() => {
  const colors = {
    string: 'border-green-200',
    number: 'border-blue-200',
    boolean: 'border-purple-200',
    object: 'border-orange-200',
    array: 'border-pink-200'
  };
  return colors[props.schema.type] || 'border-gray-200';
});

const headerColorClass = computed(() => {
  const colors = {
    string: 'bg-green-500',
    number: 'bg-blue-500',
    boolean: 'bg-purple-500',
    object: 'bg-orange-500',
    array: 'bg-pink-500'
  };
  return colors[props.schema.type] || 'bg-gray-500';
});

// Methods
const getTypeLabel = (type) => {
  if (props.advancedMode) {
    return type.charAt(0).toUpperCase() + type.slice(1);
  }

  const labels = {
    string: 'Text',
    number: 'Number',
    boolean: 'Yes/No',
    object: 'Group',
    array: 'List'
  };
  return labels[type] || type;
};

const getTypeBadgeClass = (type) => {
  const classes = {
    string: 'bg-green-100 text-green-700',
    number: 'bg-blue-100 text-blue-700',
    boolean: 'bg-purple-100 text-purple-700',
    object: 'bg-orange-100 text-orange-700',
    array: 'bg-pink-100 text-pink-700'
  };
  return classes[type] || 'bg-gray-100 text-gray-700';
};

const formatTitle = (key) => {
  if (!key) return '';
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
};

onMounted(() => {
  // Auto-expand details for leaf elements (string, number, boolean)
  if (['string', 'number', 'boolean'].includes(props.schema.type)) {
    showDetails.value = true;
  }
});
</script>

<style scoped>
.schema-block {
  @apply transition-all duration-200;
}
</style>
