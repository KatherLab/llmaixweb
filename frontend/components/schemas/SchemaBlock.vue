<template>
  <div class="schema-block">
    <!-- Main Block Container -->
    <div
      :class="[
        'rounded-card shadow-sm border-2 overflow-hidden transition-all',
        blockColorClass,
        'hover:shadow-md',
      ]"
    >
      <!-- Block Header -->
      <div :class="['px-4 py-3', headerColorClass]">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <!-- Type Icon -->
            <div class="bg-white/20 rounded-card p-2">
              <component :is="typeIcon" class="h-5 w-5 text-white" />
            </div>

            <!-- Schema Info -->
            <div>
              <h3 class="text-white font-medium">
                {{ schema.title || formatTitle((path ?? []).at(-1)) || 'Root Schema' }}
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
              class="p-2 bg-white/20 hover:bg-white/30 rounded-card transition-colors"
              title="Edit Settings"
              aria-label="Edit settings"
              @click="$emit('edit-property', { key: getCurrentKey(), schema: schema })"
            >
              <SquarePen class="h-4 w-4 text-white" />
            </button>

            <!-- Add Property Button (for objects) -->
            <button
              v-if="schema.type === 'object'"
              type="button"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-card transition-colors"
              title="Add Property"
              aria-label="Add property"
              @click="$emit('add-property')"
            >
              <Plus class="h-4 w-4 text-white" />
            </button>

            <!-- Toggle Details Button -->
            <button
              type="button"
              class="p-2 bg-white/20 hover:bg-white/30 rounded-card transition-colors"
              :title="showDetails ? 'Hide Details' : 'Show Details'"
              :aria-label="showDetails ? 'Hide details' : 'Show details'"
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
        <div v-if="showDetails" class="bg-surface border-t border-default">
          <div class="p-4 space-y-3">
            <!-- Type-specific constraints -->
            <div v-if="schema.type === 'string'" class="grid grid-cols-2 gap-3">
              <div v-if="schema.minLength !== undefined">
                <label class="block text-xs font-medium text-content-muted"> Min Length </label>
                <p class="text-sm text-content">{{ schema.minLength }}</p>
              </div>
              <div v-if="schema.maxLength !== undefined">
                <label class="block text-xs font-medium text-content-muted"> Max Length </label>
                <p class="text-sm text-content">{{ schema.maxLength }}</p>
              </div>
              <div v-if="schema.pattern" class="col-span-2">
                <label class="block text-xs font-medium text-content-muted"> Pattern </label>
                <code class="text-xs bg-surface-sunken px-2 py-1 rounded">
                  {{ schema.pattern }}
                </code>
              </div>
              <div v-if="schema.format" class="col-span-2">
                <label class="block text-xs font-medium text-content-muted"> Format </label>
                <span class="text-sm text-content">{{ schema.format }}</span>
              </div>
            </div>

            <div v-if="schema.type === 'number'" class="grid grid-cols-2 gap-3">
              <div v-if="schema.minimum !== undefined">
                <label class="block text-xs font-medium text-content-muted"> Minimum </label>
                <p class="text-sm text-content">{{ schema.minimum }}</p>
              </div>
              <div v-if="schema.maximum !== undefined">
                <label class="block text-xs font-medium text-content-muted"> Maximum </label>
                <p class="text-sm text-content">{{ schema.maximum }}</p>
              </div>
            </div>

            <!-- Enum values -->
            <div
              v-if="Array.isArray(schema.enum) && (schema.enum as unknown[]).length > 0"
              class="bg-primary-soft rounded-card p-3"
            >
              <label class="block text-xs font-medium text-primary mb-2 flex items-center">
                <List class="h-4 w-4 mr-1" />
                Allowed Values
              </label>
              <div class="grid grid-cols-2 gap-2">
                <div
                  v-for="(value, index) in schema.enum"
                  :key="index"
                  class="flex items-center space-x-2 bg-surface rounded-card px-3 py-2 shadow-sm border border-default"
                >
                  <span class="text-primary font-medium text-lg">{{ index + 1 }}</span>
                  <span class="text-sm text-content font-medium">{{ value }}</span>
                </div>
              </div>
            </div>

            <!-- Required fields (for objects) -->
            <div v-if="schema.type === 'object' && schema.required && schema.required.length > 0">
              <label class="block text-xs font-medium text-content-muted mb-1">
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
              <label class="block text-xs font-medium text-content-muted"> Default Value </label>
              <p class="text-sm text-content">
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
        <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-surface-sunken"></div>

        <!-- Properties -->
        <div class="space-y-3 pl-6">
          <div v-for="(propSchema, propKey) in schema.properties" :key="propKey" class="relative">
            <!-- Horizontal Connection -->
            <div class="absolute -left-6 top-6 w-6 h-0.5 bg-surface-sunken"></div>

            <!-- Property Block -->
            <div
              class="bg-surface rounded-card shadow-sm border border-default hover:border-primary p-3 hover:shadow-md transition-all duration-200 cursor-pointer group"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <code class="text-sm font-medium text-content-muted">{{ propKey }}</code>
                  <span
                    v-if="schema.required && schema.required.includes(propKey)"
                    class="text-xs text-red-600 dark:text-red-400"
                  >
                    *required
                  </span>
                </div>
                <div class="flex items-center space-x-1">
                  <button
                    type="button"
                    class="p-1 text-content-muted hover:text-content hover:bg-surface-muted rounded"
                    title="Edit Property"
                    aria-label="Edit property"
                    @click="$emit('edit-property', { key: propKey, schema: propSchema })"
                  >
                    <SquarePen class="h-4 w-4" />
                  </button>
                  <button
                    v-if="propSchema.type === 'object' || propSchema.type === 'array'"
                    type="button"
                    class="p-1 text-primary hover:text-primary hover:bg-primary-soft rounded"
                    title="Navigate Into"
                    aria-label="Navigate into"
                    @click="$emit('navigate', propKey)"
                  >
                    <ArrowRight class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
                    title="Delete Property"
                    aria-label="Delete property"
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
                <span v-if="propSchema.title" class="text-xs text-content-muted">
                  {{ propSchema.title }}
                </span>
              </div>

              <!-- Enum preview -->
              <div v-if="propSchema.enum && propSchema.enum.length > 0" class="mt-1">
                <span class="text-xs text-content-muted">
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
        <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-surface-sunken"></div>

        <!-- Array Item Schema -->
        <div class="pl-6">
          <!-- Horizontal Connection -->
          <div class="absolute left-0 top-6 w-6 h-0.5 bg-surface-sunken"></div>

          <div class="bg-surface rounded-card shadow-sm border border-default p-3">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-content-muted">Array Items</span>
              <div class="flex items-center space-x-1">
                <button
                  type="button"
                  class="p-1 text-content-muted hover:text-content hover:bg-surface-muted rounded"
                  title="Edit Array Items"
                  aria-label="Edit array items"
                  @click="$emit('edit-property', { key: 'items', schema: schema.items })"
                >
                  <SquarePen class="h-4 w-4" />
                </button>
                <button
                  v-if="schema.items.type === 'object'"
                  type="button"
                  class="p-1 text-primary hover:text-primary hover:bg-primary-soft rounded"
                  title="Navigate Into Items"
                  aria-label="Navigate into items"
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

<script setup lang="ts">
import { ref, computed, onMounted, type Component } from 'vue'
import { ArrowRight, ChevronRight, List, Plus, SquarePen, Trash2 } from '@lucide/vue'
import {
  getTypeIcon,
  getTypeColor,
  getTypePillClass,
  getTypeBlockBorder,
} from '@/utils/schemaTypeIcons'
import type { SchemaDefinition, SchemaProperty } from '@/types'

interface Props {
  schema: SchemaDefinition
  path?: string[]
  advancedMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  path: () => [],
  advancedMode: false,
})

defineEmits<{
  update: [schema: SchemaProperty]
  'add-property': []
  'edit-property': [payload: { key: string; schema: SchemaDefinition | SchemaProperty }]
  'delete-property': [key: string]
  navigate: [key: string]
  'edit-root': []
}>()

const showDetails = ref(false)

// Type Icons + colors: shared via @/utils/schemaTypeIcons

// Computed properties
const typeIcon = computed<Component>(() => getTypeIcon(props.schema.type))

const typeLabel = computed(() => {
  return getTypeLabel(props.schema.type)
})

const blockColorClass = computed(() => getTypeBlockBorder(props.schema.type))

const headerColorClass = computed(() => getTypeColor(props.schema.type))

// Methods
const getTypeLabel = (type: string | undefined): string => {
  if (!type) return ''
  if (props.advancedMode) {
    return type.charAt(0).toUpperCase() + type.slice(1)
  }

  const labels: Record<string, string> = {
    string: 'Text',
    number: 'Number',
    boolean: 'Yes/No',
    object: 'Group',
    array: 'List',
  }
  return labels[type] || type
}

const getTypeBadgeClass = (type: string | undefined): string => getTypePillClass(type)

const formatTitle = (key: string | undefined): string => {
  if (!key) return ''
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

const getCurrentKey = (): string => {
  // For root level, return a special identifier
  if (props.path.length === 0) {
    return '__root__'
  }
  // Return the last segment of the path
  return props.path[props.path.length - 1] ?? ''
}

onMounted(() => {
  // Auto-expand details for leaf elements (string, number, boolean)
  if (props.schema.type && ['string', 'number', 'boolean'].includes(props.schema.type)) {
    showDetails.value = true
  }
})
</script>

<style scoped>
.schema-block {
  @apply transition-all duration-200;
}
</style>
