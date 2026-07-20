<template>
  <div class="space-y-6">
    <!-- Basic Information -->
    <div class="space-y-4">
      <h4 class="text-sm font-medium text-content flex items-center">
        <Info class="h-4 w-4 mr-2 text-content-muted" />
        Basic Information
      </h4>

      <!-- Add this if not editing root -->
      <div v-if="propertyKey !== '__root__' && propertyKey !== 'items'">
        <label :class="labelClass" :for="`${uid}-key`">
          {{ advancedMode ? 'Property Key' : 'Field Name' }}
        </label>
        <input
          :id="`${uid}-key`"
          :value="propertyKey"
          :class="[inputClass, 'font-mono', keyError ? 'border-red-400 dark:border-red-600' : '']"
          placeholder="property_name"
          :aria-invalid="!!keyError"
          @input="onKeyInput(($event.target as HTMLInputElement).value)"
        />
        <p v-if="keyError" class="mt-1 text-xs text-red-600 dark:text-red-400">
          {{ keyError }}
        </p>
        <p v-else class="mt-1 text-xs text-content-muted">
          Use lowercase with underscores (e.g., patient_name)
        </p>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass" :for="`${uid}-title`">
            {{ advancedMode ? 'Title' : 'Display Name' }}
          </label>
          <input
            :id="`${uid}-title`"
            v-model="localProperty.title"
            :class="inputClass"
            :placeholder="`${propertyKey} display name`"
          />
        </div>

        <!-- Update the type select dropdown (around line 35) -->
        <div>
          <label :class="labelClass" :for="`${uid}-type`">
            {{ advancedMode ? 'Type' : 'Field Type' }}
          </label>
          <div class="relative group">
            <select
              :id="`${uid}-type`"
              v-model="localProperty.type"
              :class="[selectClass, 'pl-10']"
              @change="onTypeChange"
            >
              <option value="string">{{ advancedMode ? 'String' : 'Text' }}</option>
              <option value="number">{{ advancedMode ? 'Number' : 'Number' }}</option>
              <option value="boolean">{{ advancedMode ? 'Boolean' : 'Yes/No' }}</option>
              <option value="object">{{ advancedMode ? 'Object' : 'Group' }}</option>
              <option value="array">{{ advancedMode ? 'Array' : 'List' }}</option>
            </select>
            <div :class="['absolute left-3 top-2.5 rounded p-1', typeColorClass]">
              <component :is="typeIcon" class="h-4 w-4 text-white" />
            </div>
            <!-- Type description tooltip -->
            <div class="absolute left-0 top-full mt-1 hidden group-hover:block z-10 w-full">
              <div
                class="bg-inverse-surface text-inverse-content text-xs rounded-card p-2 shadow-lg"
              >
                <p v-if="localProperty.type === 'string'">
                  Text field for names, descriptions, etc.
                </p>
                <p v-else-if="localProperty.type === 'number'">
                  Numeric values with optional decimals
                </p>
                <p v-else-if="localProperty.type === 'boolean'">True/false checkbox or toggle</p>
                <p v-else-if="localProperty.type === 'object'">Container for grouped fields</p>
                <p v-else-if="localProperty.type === 'array'">List of repeating items</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <label :class="labelClass" :for="`${uid}-description`"> Description </label>
        <textarea
          :id="`${uid}-description`"
          v-model="localProperty.description"
          rows="2"
          :class="textareaClass"
          placeholder="Describe what this field captures..."
        />
      </div>
    </div>

    <!-- Type-specific Settings -->
    <div v-if="localProperty.type === 'string'" class="space-y-4">
      <h4 class="text-sm font-medium text-content flex items-center">
        <SquarePen class="h-4 w-4 mr-2 text-green-500" />
        Text Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass" :for="`${uid}-min-length`"> Minimum Length </label>
          <input
            :id="`${uid}-min-length`"
            v-model.number="localProperty.minLength"
            type="number"
            min="0"
            :class="inputClass"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label :class="labelClass" :for="`${uid}-max-length`"> Maximum Length </label>
          <input
            :id="`${uid}-max-length`"
            v-model.number="localProperty.maxLength"
            type="number"
            min="0"
            :class="inputClass"
            placeholder="No maximum"
          />
        </div>
      </div>

      <!-- Format Selection -->
      <div>
        <label :class="labelClass" :for="`${uid}-format`"> Format </label>
        <select :id="`${uid}-format`" v-model="localProperty.format" :class="selectClass">
          <option value="">No specific format</option>
          <option value="email">Email</option>
          <option value="uri">URL</option>
          <option value="date">Date (YYYY-MM-DD)</option>
          <option value="date-time">Date & Time</option>
          <option value="time">Time</option>
          <option value="ipv4">IPv4 Address</option>
          <option value="ipv6">IPv6 Address</option>
          <option value="uuid">UUID</option>
        </select>
      </div>

      <!-- Pattern -->
      <div>
        <label :class="labelClass" :for="`${uid}-pattern`">
          Pattern (Regular Expression)
          <button
            class="ml-1 text-content-subtle hover:text-content-muted"
            @click="showPatternHelp = !showPatternHelp"
          >
            <CircleHelp class="h-4 w-4 inline" />
          </button>
        </label>
        <input
          :id="`${uid}-pattern`"
          v-model="localProperty.pattern"
          :class="[inputClass, 'font-mono']"
          placeholder="e.g., ^[A-Z]{2}[0-9]{4}$"
        />
        <Callout v-if="showPatternHelp" variant="info" class="mt-2 text-xs">
          <p class="font-medium mb-1">Common patterns:</p>
          <ul class="space-y-1">
            <li><code class="bg-surface-muted px-1 rounded">^[0-9]+$</code> - Numbers only</li>
            <li><code class="bg-surface-muted px-1 rounded">^[A-Za-z]+$</code> - Letters only</li>
            <li>
              <code class="bg-surface-muted px-1 rounded">^[A-Z]{2}[0-9]{4}$</code>
              - 2 uppercase letters + 4 digits
            </li>
          </ul>
        </Callout>
      </div>

      <!-- Enum Values -->
      <div>
        <label :class="labelClass"> Allowed Values (Options) </label>
        <div class="space-y-2">
          <div
            v-for="(_value, index) in enumValues"
            :key="index"
            class="flex items-center space-x-2"
          >
            <input
              v-model="enumValues[index]"
              :class="[inputClass, 'flex-1']"
              placeholder="Option value"
            />
            <BaseButton
              variant="link"
              tone="red"
              class="p-1"
              aria-label="Remove enum value"
              @click="removeEnumValue(index)"
            >
              <Trash2 class="h-4 w-4" aria-hidden="true" />
            </BaseButton>
          </div>
          <button
            class="w-full py-2 border-2 border-dashed border-strong rounded-card text-sm text-content-muted hover:border-strong hover:text-content"
            @click="addEnumValue"
          >
            + Add Option
          </button>
        </div>
      </div>
    </div>

    <!-- Number Settings -->
    <div v-else-if="localProperty.type === 'number'" class="space-y-4">
      <h4 class="text-sm font-medium text-content flex items-center">
        <Hash class="h-4 w-4 mr-2 text-primary" />
        Number Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass" :for="`${uid}-minimum`"> Minimum Value </label>
          <input
            :id="`${uid}-minimum`"
            v-model.number="localProperty.minimum"
            type="number"
            :class="inputClass"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label :class="labelClass" :for="`${uid}-maximum`"> Maximum Value </label>
          <input
            :id="`${uid}-maximum`"
            v-model.number="localProperty.maximum"
            type="number"
            :class="inputClass"
            placeholder="No maximum"
          />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass" :for="`${uid}-multiple-of`"> Multiple Of </label>
          <input
            :id="`${uid}-multiple-of`"
            v-model.number="localProperty.multipleOf"
            type="number"
            step="any"
            :class="inputClass"
            placeholder="e.g., 0.01 for cents"
          />
        </div>

        <div>
          <label class="flex items-center space-x-2">
            <input
              v-model="isInteger"
              type="checkbox"
              class="rounded border-strong text-primary focus:ring-ring"
            />
            <span class="text-sm font-medium text-content-muted">Integer only</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Boolean Settings -->
    <div v-else-if="localProperty.type === 'boolean'" class="space-y-4">
      <h4 class="text-sm font-medium text-content flex items-center">
        <CircleCheckBig class="h-4 w-4 mr-2 text-purple-500" />
        Yes/No Settings
      </h4>

      <p class="text-sm text-content-muted">
        This field will capture true/false values. The user interface will show this as a checkbox
        or toggle switch.
      </p>
    </div>

    <!-- Array Settings -->
    <div v-else-if="localProperty.type === 'array'" class="space-y-4">
      <h4 class="text-sm font-medium text-content flex items-center">
        <List class="h-4 w-4 mr-2 text-pink-500" />
        List Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass" :for="`${uid}-min-items`"> Minimum Items </label>
          <input
            :id="`${uid}-min-items`"
            v-model.number="localProperty.minItems"
            type="number"
            min="0"
            :class="inputClass"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label :class="labelClass" :for="`${uid}-max-items`"> Maximum Items </label>
          <input
            :id="`${uid}-max-items`"
            v-model.number="localProperty.maxItems"
            type="number"
            min="0"
            :class="inputClass"
            placeholder="No maximum"
          />
        </div>
      </div>

      <div>
        <label class="flex items-center space-x-2">
          <input
            v-model="localProperty.uniqueItems"
            type="checkbox"
            class="rounded border-strong text-primary focus:ring-ring"
          />
          <span class="text-sm font-medium text-content-muted">Items must be unique</span>
        </label>
      </div>
    </div>

    <!-- Object Settings -->
    <div v-else-if="localProperty.type === 'object'" class="space-y-4">
      <h4 class="text-sm font-medium text-content flex items-center">
        <Layers class="h-4 w-4 mr-2 text-orange-500" />
        Group Settings
      </h4>

      <!-- Required Properties -->
      <div>
        <label :class="labelClass"> Required Fields </label>
        <div class="space-y-2">
          <label
            v-for="(propSchema, propKey) in localProperty.properties"
            :key="propKey"
            class="flex items-center space-x-2"
          >
            <input
              type="checkbox"
              :checked="isRequired(propKey)"
              class="rounded border-strong text-primary focus:ring-ring"
              @change="toggleRequired(propKey)"
            />
            <span class="text-sm text-content-muted">{{ propKey }}</span>
            <span class="text-xs text-content-muted">({{ propSchema.type }})</span>
          </label>
        </div>
        <p
          v-if="!localProperty.properties || Object.keys(localProperty.properties).length === 0"
          class="text-sm text-content-muted"
        >
          Add properties to this group first
        </p>
      </div>

      <div v-if="advancedMode">
        <label class="flex items-center space-x-2">
          <input
            v-model="localProperty.additionalProperties"
            type="checkbox"
            class="rounded border-strong text-primary focus:ring-ring"
          />
          <span class="text-sm font-medium text-content-muted">Allow additional properties</span>
        </label>
      </div>
    </div>

    <!-- Common Settings -->
    <div class="space-y-4 pt-4 border-t">
      <h4 class="text-sm font-medium text-content">Additional Settings</h4>

      <div>
        <label :class="labelClass" :for="hasDefaultInput ? `${uid}-default` : undefined">
          Default Value
        </label>
        <div v-if="localProperty.type === 'boolean'" class="flex items-center space-x-4">
          <label class="flex items-center space-x-2">
            <input
              type="radio"
              :value="undefined"
              :checked="localProperty.default === undefined"
              class="border-strong text-primary focus:ring-ring"
              @change="localProperty.default = undefined"
            />
            <span class="text-sm text-content-muted">No default</span>
          </label>
          <label class="flex items-center space-x-2">
            <input
              v-model="localProperty.default"
              type="radio"
              :value="true"
              class="border-strong text-primary focus:ring-ring"
            />
            <span class="text-sm text-content-muted">True</span>
          </label>
          <label class="flex items-center space-x-2">
            <input
              v-model="localProperty.default"
              type="radio"
              :value="false"
              class="border-strong text-primary focus:ring-ring"
            />
            <span class="text-sm text-content-muted">False</span>
          </label>
        </div>
        <input
          v-else-if="localProperty.type === 'string'"
          :id="`${uid}-default`"
          v-model="localProperty.default"
          type="text"
          :class="inputClass"
          placeholder="No default value"
        />
        <input
          v-else-if="localProperty.type === 'number'"
          :id="`${uid}-default`"
          v-model.number="localProperty.default"
          type="number"
          :class="inputClass"
          placeholder="No default value"
        />
        <p v-else class="text-sm text-content-muted">
          Default values for {{ localProperty.type }} must be set in raw JSON mode
        </p>
      </div>

      <!-- Advanced Features -->
      <div v-if="advancedMode" class="space-y-4 pt-4 border-t">
        <h4 class="text-sm font-medium text-content">Advanced Features</h4>

        <!-- Read Only -->
        <label class="flex items-center space-x-2">
          <input
            v-model="localProperty.readOnly"
            type="checkbox"
            class="rounded border-strong text-primary focus:ring-ring"
          />
          <span class="text-sm font-medium text-content-muted">Read-only field</span>
        </label>

        <!-- Examples -->
        <div>
          <label :class="labelClass" :for="`${uid}-examples`"> Examples </label>
          <textarea
            :id="`${uid}-examples`"
            v-model="examplesText"
            rows="2"
            :class="[textareaClass, 'font-mono']"
            placeholder="Enter examples, one per line"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, useId, type Component } from 'vue'
import {
  CircleCheckBig,
  CircleHelp,
  Hash,
  Info,
  Layers,
  List,
  SquarePen,
  Trash2,
} from '@lucide/vue'
import { getTypeIcon, getTypeColor } from '@/utils/schemaTypeIcons'
import { inputClass, textareaClass, selectClass, labelClass } from '@/utils/formStyles'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import type { SchemaDefinition, SchemaProperty } from '@/types'

interface Props {
  property: SchemaDefinition | SchemaProperty
  propertyKey: string
  advancedMode?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  advancedMode: false,
})

const emit = defineEmits<{
  update: [schema: SchemaProperty]
  'update-key': [key: string]
}>()

// Unique per-instance prefix for label/input ids (the editor can be mounted
// twice at once: inline in VisualSchemaEditor and inside EditPropertyModal).
const uid = useId()

const localProperty = ref<SchemaProperty>(JSON.parse(JSON.stringify(props.property)))
const showPatternHelp = ref(false)

// --- Property key validation ---
// Keys become JSON schema property names, so they must be valid identifiers.
// The old `pattern` attribute never ran (no native form submit) — validate
// inline instead. The draft mirrors what the user typed; the `propertyKey`
// prop itself only changes when the parent commits the rename on save.
const KEY_PATTERN = /^[a-zA-Z_][a-zA-Z0-9_]*$/
const keyDraft = ref(props.propertyKey)
watch(
  () => props.propertyKey,
  (v) => {
    keyDraft.value = v
  },
)
const onKeyInput = (value: string) => {
  keyDraft.value = value
  emit('update-key', value)
}
const keyError = computed<string | null>(() => {
  const key = keyDraft.value.trim()
  if (!key) return 'A key is required'
  if (!KEY_PATTERN.test(key)) {
    return 'Only letters, numbers and underscores — must not start with a number (e.g., patient_name)'
  }
  return null
})
const enumValues = ref<string[]>(props.property.enum ? [...(props.property.enum as string[])] : [])
const examplesText = ref(
  (props.property.examples as string[]) ? (props.property.examples as string[]).join('\n') : '',
)

// Type Icons + colors: shared via @/utils/schemaTypeIcons

// Computed properties
const typeIcon = computed<Component>(() => getTypeIcon(localProperty.value.type))

const typeColorClass = computed(() => getTypeColor(localProperty.value.type))

// Only string/number types render a single default-value input the label can point at.
const hasDefaultInput = computed(
  () => localProperty.value.type === 'string' || localProperty.value.type === 'number',
)

const isInteger = computed<boolean>({
  get: () => localProperty.value.type === 'integer',
  set: (value) => {
    localProperty.value.type = value ? 'integer' : 'number'
  },
})

// Watch for changes and emit updates
watch(
  localProperty,
  (newValue) => {
    // Clean up the property before emitting
    const cleaned: SchemaProperty = {
      type: newValue.type,
    }

    // Add other properties based on type
    for (const [key, value] of Object.entries(newValue)) {
      // Skip if it's undefined, null, or empty string
      if (value === undefined || value === null || value === '') {
        continue
      }

      // Skip type since we already added it
      if (key === 'type') {
        continue
      }

      // Filter out properties that don't belong to the current type
      const isStringProp = ['enum', 'pattern', 'minLength', 'maxLength', 'format'].includes(key)
      const isNumberProp = ['minimum', 'maximum', 'multipleOf'].includes(key)
      const isArrayProp = ['minItems', 'maxItems', 'uniqueItems', 'items'].includes(key)
      const isObjectProp = ['properties', 'required', 'additionalProperties'].includes(key)
      const isCommonProp = ['title', 'description', 'default', 'examples', 'readOnly'].includes(key)

      // Only include properties that are common or belong to the current type
      if (isCommonProp) {
        cleaned[key] = value
      } else if (newValue.type === 'string' && isStringProp) {
        cleaned[key] = value
      } else if ((newValue.type === 'number' || newValue.type === 'integer') && isNumberProp) {
        cleaned[key] = value
      } else if (newValue.type === 'array' && isArrayProp) {
        cleaned[key] = value
      } else if (newValue.type === 'object' && isObjectProp) {
        cleaned[key] = value
      } else if (newValue.type === 'boolean') {
        // Boolean has no specific properties besides common ones
        continue
      }
    }

    emit('update', cleaned)
  },
  { deep: true },
)

// Enum management
watch(
  enumValues,
  (newValues) => {
    const filtered = newValues.filter((v) => v && v.trim())
    if (filtered.length > 0) {
      localProperty.value.enum = filtered
    } else {
      // Important: use Vue's delete to ensure reactivity
      if (localProperty.value.enum) {
        delete localProperty.value.enum
      }
    }
  },
  { deep: true },
)

const addEnumValue = () => {
  enumValues.value.push('')
}

const removeEnumValue = (index: number) => {
  enumValues.value.splice(index, 1)
}

// Examples management
watch(examplesText, (newText) => {
  const examples = newText.split('\n').filter((line) => line.trim())
  if (examples.length > 0) {
    localProperty.value.examples = examples
  } else {
    delete localProperty.value.examples
  }
})

// Required fields management
const isRequired = (propKey: string): boolean => {
  return !!localProperty.value.required && localProperty.value.required.includes(propKey)
}

const toggleRequired = (propKey: string) => {
  if (!localProperty.value.required) {
    localProperty.value.required = []
  }

  const index = localProperty.value.required.indexOf(propKey)
  if (index === -1) {
    localProperty.value.required.push(propKey)
  } else {
    localProperty.value.required.splice(index, 1)
  }

  if (localProperty.value.required.length === 0) {
    delete localProperty.value.required
  }
}

// Type change handler
const onTypeChange = () => {
  // Store the values we want to preserve
  const preservedTitle = localProperty.value.title || ''
  const preservedDescription = localProperty.value.description || ''
  const newType = localProperty.value.type

  // Create a completely new object with only the type and preserved values
  const newProperty: SchemaProperty = {
    type: newType,
  }

  // Only add title and description if they have values
  if (preservedTitle) {
    newProperty.title = preservedTitle
  }
  if (preservedDescription) {
    newProperty.description = preservedDescription
  }

  // Add type-specific defaults
  if (newProperty.type === 'object') {
    newProperty.properties = {}
  } else if (newProperty.type === 'array') {
    newProperty.items = { type: 'string' }
  }

  // Replace the entire localProperty value
  localProperty.value = newProperty

  // Clear enum values
  enumValues.value = []

  // Clear examples text
  examplesText.value = ''

  // Emit the clean property immediately
  emit('update', newProperty)
}
</script>
