<template>
  <div class="schema-block">
    <!-- Main Block Container -->
    <div
      :class="[
        'rounded-lg shadow-sm border-2 overflow-hidden transition-all',
        blockColorClass,
        'hover:shadow-md',
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
            <!-- Edit Button (always show for current block) -->
            <button
              type="button"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Edit Settings"
              @click="$emit('edit-property', { key: getCurrentKey(), schema: schema })"
            >
              <SquarePen class="h-4 w-4 text-white" />
            </button>

            <!-- Add Property Button (for objects) -->
            <button
              v-if="schema.type === 'object'"
              type="button"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Add Property"
              @click="$emit('add-property')"
            >
              <Plus class="h-4 w-4 text-white" />
            </button>

            <!-- Toggle Details Button -->
            <button
              type="button"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              :title="showDetails ? 'Hide Details' : 'Show Details'"
              @click="showDetails = !showDetails"
            >
              <ChevronRight
                :class="['h-4 w-4 text-white transition-transform', showDetails ? 'rotate-90' : '']"
              />
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
        <div v-if="showDetails" class="bg-white dark:bg-slate-800 border-t dark:border-slate-700">
          <div class="p-4 space-y-3">
            <!-- Type-specific constraints -->
            <div v-if="schema.type === 'string'" class="grid grid-cols-2 gap-3">
              <div v-if="schema.minLength !== undefined">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400">
                  Min Length
                </label>
                <p class="text-sm text-slate-900 dark:text-slate-100">{{ schema.minLength }}</p>
              </div>
              <div v-if="schema.maxLength !== undefined">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400">
                  Max Length
                </label>
                <p class="text-sm text-slate-900 dark:text-slate-100">{{ schema.maxLength }}</p>
              </div>
              <div v-if="schema.pattern" class="col-span-2">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400">
                  Pattern
                </label>
                <code class="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                  {{ schema.pattern }}
                </code>
              </div>
              <div v-if="schema.format" class="col-span-2">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400">
                  Format
                </label>
                <span class="text-sm text-slate-900 dark:text-slate-100">{{ schema.format }}</span>
              </div>
            </div>

            <div v-if="schema.type === 'number'" class="grid grid-cols-2 gap-3">
              <div v-if="schema.minimum !== undefined">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400">
                  Minimum
                </label>
                <p class="text-sm text-slate-900 dark:text-slate-100">{{ schema.minimum }}</p>
              </div>
              <div v-if="schema.maximum !== undefined">
                <label class="block text-xs font-medium text-slate-600 dark:text-slate-400">
                  Maximum
                </label>
                <p class="text-sm text-slate-900 dark:text-slate-100">{{ schema.maximum }}</p>
              </div>
            </div>

            <!-- Enum values -->
            <div
              v-if="schema.enum && schema.enum.length > 0"
              class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3"
            >
              <label
                class="block text-xs font-medium text-blue-900 dark:text-blue-300 mb-2 flex items-center"
              >
                <List class="h-4 w-4 mr-1" />
                Allowed Values
              </label>
              <div class="grid grid-cols-2 gap-2">
                <div
                  v-for="(value, index) in schema.enum"
                  :key="index"
                  class="flex items-center space-x-2 bg-white dark:bg-slate-800 rounded-md px-3 py-2 shadow-sm border border-blue-200 dark:border-blue-800"
                >
                  <span class="text-blue-600 font-medium text-lg">{{ index + 1 }}</span>
                  <span class="text-sm text-slate-900 dark:text-slate-100 font-medium">{{
                    value
                  }}</span>
                </div>
              </div>
            </div>

            <!-- Required fields (for objects) -->
            <div v-if="schema.type === 'object' && schema.required && schema.required.length > 0">
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                Required Fields
              </label>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="field in schema.required"
                  :key="field"
                  class="px-2 py-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 rounded text-xs"
                >
                  {{ field }}
                </span>
              </div>
            </div>

            <!-- Default value -->
            <div v-if="schema.default !== undefined">
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400">
                Default Value
              </label>
              <p class="text-sm text-slate-900 dark:text-slate-100">
                {{ JSON.stringify(schema.default) }}
              </p>
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- Object Properties -->
    <div v-if="schema.type === 'object' && schema.properties" class="mt-4 ml-6">
      <div class="relative">
        <!-- Connection Line -->
        <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-slate-300 dark:bg-slate-600"></div>

        <!-- Properties -->
        <div class="space-y-3 pl-6">
          <div v-for="(propSchema, propKey) in schema.properties" :key="propKey" class="relative">
            <!-- Horizontal Connection -->
            <div class="absolute -left-6 top-6 w-6 h-0.5 bg-slate-300 dark:bg-slate-600"></div>

            <!-- Property Block -->
            <div
              class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border dark:border-slate-700 dark:hover:border-blue-600 p-3 hover:shadow-md hover:border-blue-300 transition-all duration-200 cursor-pointer group"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <code class="text-sm font-medium text-slate-700 dark:text-slate-300">{{
                    propKey
                  }}</code>
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
                    class="p-1 text-slate-500 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700 hover:text-slate-700 hover:bg-slate-100 rounded"
                    title="Edit Property"
                    @click="$emit('edit-property', { key: propKey, schema: propSchema })"
                  >
                    <SquarePen class="h-4 w-4" />
                  </button>
                  <button
                    v-if="propSchema.type === 'object' || propSchema.type === 'array'"
                    type="button"
                    class="p-1 text-blue-500 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded"
                    title="Navigate Into"
                    @click="$emit('navigate', propKey)"
                  >
                    <ArrowRight class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
                    title="Delete Property"
                    @click="$emit('delete-property', propKey)"
                  >
                    <Trash2 class="h-4 w-4" />
                  </button>
                </div>
              </div>

              <!-- Mini Type Badge -->
              <div class="flex items-center space-x-2">
                <span
                  :class="[
                    'px-2 py-0.5 rounded text-xs font-medium',
                    getTypeBadgeClass(propSchema.type),
                  ]"
                >
                  {{ getTypeLabel(propSchema.type) }}
                </span>
                <span v-if="propSchema.title" class="text-xs text-slate-600 dark:text-slate-400">
                  {{ propSchema.title }}
                </span>
              </div>

              <!-- Enum preview -->
              <div v-if="propSchema.enum && propSchema.enum.length > 0" class="mt-1">
                <span class="text-xs text-slate-500 dark:text-slate-400">
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
        <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-slate-300 dark:bg-slate-600"></div>

        <!-- Array Item Schema -->
        <div class="pl-6">
          <!-- Horizontal Connection -->
          <div class="absolute left-0 top-6 w-6 h-0.5 bg-slate-300 dark:bg-slate-600"></div>

          <div
            class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border dark:border-slate-700 p-3"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-slate-700 dark:text-slate-300"
                >Array Items</span
              >
              <div class="flex items-center space-x-1">
                <button
                  type="button"
                  class="p-1 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded"
                  title="Edit Array Items"
                  @click="$emit('edit-property', { key: 'items', schema: schema.items })"
                >
                  <SquarePen class="h-4 w-4" />
                </button>
                <button
                  v-if="schema.items.type === 'object'"
                  type="button"
                  class="p-1 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded"
                  title="Navigate Into Items"
                  @click="$emit('navigate', 'items')"
                >
                  <ArrowRight class="h-4 w-4" />
                </button>
              </div>
            </div>

            <span
              :class="[
                'px-2 py-0.5 rounded text-xs font-medium',
                getTypeBadgeClass(schema.items.type),
              ]"
            >
              {{ getTypeLabel(schema.items.type) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ArrowRight, ChevronRight, List, Plus, SquarePen, Trash2 } from '@lucide/vue'
import {
  getTypeIcon,
  getTypeColor,
  getTypePillClass,
  getTypeBlockBorder,
} from '@/utils/schemaTypeIcons'

const props = defineProps({
  schema: {
    type: Object,
    required: true,
  },
  path: {
    type: Array,
    default: () => [],
  },
  advancedMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'update',
  'add-property',
  'edit-property',
  'delete-property',
  'navigate',
  'edit-root',
])

const showDetails = ref(false)

// Type Icons + colors: shared via @/utils/schemaTypeIcons

// Computed properties
const typeIcon = computed(() => getTypeIcon(props.schema.type))

const typeLabel = computed(() => {
  return getTypeLabel(props.schema.type)
})

const blockColorClass = computed(() => getTypeBlockBorder(props.schema.type))

const headerColorClass = computed(() => getTypeColor(props.schema.type))

// Methods
const getTypeLabel = (type) => {
  if (props.advancedMode) {
    return type.charAt(0).toUpperCase() + type.slice(1)
  }

  const labels = {
    string: 'Text',
    number: 'Number',
    boolean: 'Yes/No',
    object: 'Group',
    array: 'List',
  }
  return labels[type] || type
}

const getTypeBadgeClass = (type) => getTypePillClass(type)

const formatTitle = (key) => {
  if (!key) return ''
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

const getCurrentKey = () => {
  // For root level, return a special identifier
  if (props.path.length === 0) {
    return '__root__'
  }
  // Return the last segment of the path
  return props.path[props.path.length - 1]
}

onMounted(() => {
  // Auto-expand details for leaf elements (string, number, boolean)
  if (['string', 'number', 'boolean'].includes(props.schema.type)) {
    showDetails.value = true
  }
})
</script>

<style scoped>
.schema-block {
  @apply transition-all duration-200;
}
</style>
