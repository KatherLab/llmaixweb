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
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>

            <!-- Add Property Button (for objects) -->
            <button
              v-if="schema.type === 'object'"
              type="button"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Add Property"
              @click="$emit('add-property')"
            >
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>

            <!-- Toggle Details Button -->
            <button
              type="button"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              :title="showDetails ? 'Hide Details' : 'Show Details'"
              @click="showDetails = !showDetails"
            >
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  :d="showDetails ? 'M19 9l-7 7-7-7' : 'M9 5l7 7-7 7'"
                />
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
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 6h16M4 10h16M4 14h16M4 18h16"
                  />
                </svg>
                Allowed Values
              </label>
              <div class="grid grid-cols-2 gap-2">
                <div
                  v-for="(value, index) in schema.enum"
                  :key="index"
                  class="flex items-center space-x-2 bg-white rounded-md px-3 py-2 shadow-sm border border-blue-200"
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
          <div v-for="(propSchema, propKey) in schema.properties" :key="propKey" class="relative">
            <!-- Horizontal Connection -->
            <div class="absolute -left-6 top-6 w-6 h-0.5 bg-gray-300"></div>

            <!-- Property Block -->
            <div
              class="bg-white rounded-lg shadow-sm border p-3 hover:shadow-md hover:border-blue-300 transition-all duration-200 cursor-pointer group"
            >
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
                    class="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                    title="Edit Property"
                    @click="$emit('edit-property', { key: propKey, schema: propSchema })"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <button
                    v-if="propSchema.type === 'object' || propSchema.type === 'array'"
                    type="button"
                    class="p-1 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded"
                    title="Navigate Into"
                    @click="$emit('navigate', propKey)"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded"
                    title="Delete Property"
                    @click="$emit('delete-property', propKey)"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
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
                  class="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                  title="Edit Array Items"
                  @click="$emit('edit-property', { key: 'items', schema: schema.items })"
                >
                  <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                </button>
                <button
                  v-if="schema.items.type === 'object'"
                  type="button"
                  class="p-1 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded"
                  title="Navigate Into Items"
                  @click="$emit('navigate', 'items')"
                >
                  <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 7l5 5m0 0l-5 5m5-5H6"
                    />
                  </svg>
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
import { getTypeIcon, getTypeColor, getTypePillClass } from '@/utils/schemaTypeIcons'

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

const blockColorClass = computed(() => {
  const colors = {
    string: 'border-green-200',
    number: 'border-blue-200',
    boolean: 'border-purple-200',
    object: 'border-orange-200',
    array: 'border-pink-200',
  }
  return colors[props.schema.type] || 'border-gray-200'
})

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
