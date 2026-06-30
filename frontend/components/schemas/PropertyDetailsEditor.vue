<template>
  <div class="space-y-6">
    <!-- Basic Information -->
    <div class="space-y-4">
      <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100 flex items-center">
        <Info class="h-4 w-4 mr-2 text-slate-500 dark:text-slate-400" />
        Basic Information
      </h4>

      <!-- Add this if not editing root -->
      <div v-if="propertyKey !== '__root__' && propertyKey !== 'items'">
        <label :class="labelClass">
          {{ advancedMode ? 'Property Key' : 'Field Name' }}
        </label>
        <input
          :value="propertyKey"
          :class="[inputClass, 'font-mono']"
          placeholder="property_name"
          pattern="^[a-zA-Z_][a-zA-Z0-9_]*$"
          @input="$emit('update-key', $event.target.value)"
        />
        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Use lowercase with underscores (e.g., patient_name)
        </p>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass">
            {{ advancedMode ? 'Title' : 'Display Name' }}
          </label>
          <input
            v-model="localProperty.title"
            :class="inputClass"
            :placeholder="`${propertyKey} display name`"
          />
        </div>

        <!-- Update the type select dropdown (around line 35) -->
        <div>
          <label :class="labelClass">
            {{ advancedMode ? 'Type' : 'Field Type' }}
          </label>
          <div class="relative group">
            <select
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
              <div class="bg-slate-900 text-white text-xs rounded-lg p-2 shadow-lg">
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
        <label :class="labelClass"> Description </label>
        <textarea
          v-model="localProperty.description"
          rows="2"
          :class="textareaClass"
          placeholder="Describe what this field captures..."
        />
      </div>
    </div>

    <!-- Type-specific Settings -->
    <div v-if="localProperty.type === 'string'" class="space-y-4">
      <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100 flex items-center">
        <SquarePen class="h-4 w-4 mr-2 text-green-500" />
        Text Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass"> Minimum Length </label>
          <input
            v-model.number="localProperty.minLength"
            type="number"
            min="0"
            :class="inputClass"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label :class="labelClass"> Maximum Length </label>
          <input
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
        <label :class="labelClass"> Format </label>
        <select v-model="localProperty.format" :class="selectClass">
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
        <label :class="labelClass">
          Pattern (Regular Expression)
          <button
            class="ml-1 text-slate-400 dark:text-slate-500 dark:hover:text-slate-300 hover:text-slate-600"
            @click="showPatternHelp = !showPatternHelp"
          >
            <CircleHelp class="h-4 w-4 inline" />
          </button>
        </label>
        <input
          v-model="localProperty.pattern"
          :class="[inputClass, 'font-mono']"
          placeholder="e.g., ^[A-Z]{2}[0-9]{4}$"
        />
        <div
          v-if="showPatternHelp"
          class="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md text-xs text-slate-700 dark:text-slate-300"
        >
          <p class="font-medium mb-1">Common patterns:</p>
          <ul class="space-y-1">
            <li>
              <code class="bg-white dark:bg-slate-800 px-1 rounded">^[0-9]+$</code> - Numbers only
            </li>
            <li>
              <code class="bg-white dark:bg-slate-800 px-1 rounded">^[A-Za-z]+$</code> - Letters
              only
            </li>
            <li>
              <code class="bg-white dark:bg-slate-800 px-1 rounded">^[A-Z]{2}[0-9]{4}$</code>
              - 2 uppercase letters + 4 digits
            </li>
          </ul>
        </div>
      </div>

      <!-- Enum Values -->
      <div>
        <label :class="labelClass"> Allowed Values (Options) </label>
        <div class="space-y-2">
          <div
            v-for="(value, index) in enumValues"
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
            class="w-full py-2 border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-md text-sm text-slate-600 dark:text-slate-400 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-700 dark:hover:text-slate-200"
            @click="addEnumValue"
          >
            + Add Option
          </button>
        </div>
      </div>
    </div>

    <!-- Number Settings -->
    <div v-else-if="localProperty.type === 'number'" class="space-y-4">
      <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100 flex items-center">
        <Hash class="h-4 w-4 mr-2 text-blue-500" />
        Number Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass"> Minimum Value </label>
          <input
            v-model.number="localProperty.minimum"
            type="number"
            :class="inputClass"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label :class="labelClass"> Maximum Value </label>
          <input
            v-model.number="localProperty.maximum"
            type="number"
            :class="inputClass"
            placeholder="No maximum"
          />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass"> Multiple Of </label>
          <input
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
              class="rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Integer only</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Boolean Settings -->
    <div v-else-if="localProperty.type === 'boolean'" class="space-y-4">
      <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100 flex items-center">
        <CircleCheckBig class="h-4 w-4 mr-2 text-purple-500" />
        Yes/No Settings
      </h4>

      <p class="text-sm text-slate-600 dark:text-slate-400">
        This field will capture true/false values. The user interface will show this as a checkbox
        or toggle switch.
      </p>
    </div>

    <!-- Array Settings -->
    <div v-else-if="localProperty.type === 'array'" class="space-y-4">
      <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100 flex items-center">
        <List class="h-4 w-4 mr-2 text-pink-500" />
        List Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label :class="labelClass"> Minimum Items </label>
          <input
            v-model.number="localProperty.minItems"
            type="number"
            min="0"
            :class="inputClass"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label :class="labelClass"> Maximum Items </label>
          <input
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
            class="rounded border-slate-300 dark:border-slate-600 dark:bg-slate-700 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm font-medium text-slate-700 dark:text-slate-300"
            >Items must be unique</span
          >
        </label>
      </div>
    </div>

    <!-- Object Settings -->
    <div v-else-if="localProperty.type === 'object'" class="space-y-4">
      <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100 flex items-center">
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
              class="rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
              @change="toggleRequired(propKey)"
            />
            <span class="text-sm text-slate-700 dark:text-slate-300">{{ propKey }}</span>
            <span class="text-xs text-slate-500 dark:text-slate-400">({{ propSchema.type }})</span>
          </label>
        </div>
        <p
          v-if="!localProperty.properties || Object.keys(localProperty.properties).length === 0"
          class="text-sm text-slate-500 dark:text-slate-400"
        >
          Add properties to this group first
        </p>
      </div>

      <div v-if="advancedMode">
        <label class="flex items-center space-x-2">
          <input
            v-model="localProperty.additionalProperties"
            type="checkbox"
            class="rounded border-slate-300 dark:border-slate-600 dark:bg-slate-700 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm font-medium text-slate-700 dark:text-slate-300"
            >Allow additional properties</span
          >
        </label>
      </div>
    </div>

    <!-- Common Settings -->
    <div class="space-y-4 pt-4 border-t">
      <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100">Additional Settings</h4>

      <div>
        <label :class="labelClass"> Default Value </label>
        <div v-if="localProperty.type === 'boolean'" class="flex items-center space-x-4">
          <label class="flex items-center space-x-2">
            <input
              type="radio"
              :value="undefined"
              :checked="localProperty.default === undefined"
              class="border-slate-300 dark:border-slate-600 dark:bg-slate-700 text-blue-600 focus:ring-blue-500"
              @change="localProperty.default = undefined"
            />
            <span class="text-sm dark:text-slate-300">No default</span>
          </label>
          <label class="flex items-center space-x-2">
            <input
              v-model="localProperty.default"
              type="radio"
              :value="true"
              class="border-slate-300 dark:border-slate-600 dark:bg-slate-700 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm dark:text-slate-300">True</span>
          </label>
          <label class="flex items-center space-x-2">
            <input
              v-model="localProperty.default"
              type="radio"
              :value="false"
              class="border-slate-300 dark:border-slate-600 dark:bg-slate-700 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm dark:text-slate-300">False</span>
          </label>
        </div>
        <input
          v-else-if="localProperty.type === 'string'"
          v-model="localProperty.default"
          type="text"
          :class="inputClass"
          placeholder="No default value"
        />
        <input
          v-else-if="localProperty.type === 'number'"
          v-model.number="localProperty.default"
          type="number"
          :class="inputClass"
          placeholder="No default value"
        />
        <p v-else class="text-sm text-slate-500 dark:text-slate-400">
          Default values for {{ localProperty.type }} must be set in raw JSON mode
        </p>
      </div>

      <!-- Advanced Features -->
      <div v-if="advancedMode" class="space-y-4 pt-4 border-t">
        <h4 class="text-sm font-medium text-slate-900 dark:text-slate-100">Advanced Features</h4>

        <!-- Read Only -->
        <label class="flex items-center space-x-2">
          <input
            v-model="localProperty.readOnly"
            type="checkbox"
            class="rounded border-slate-300 dark:border-slate-600 dark:bg-slate-700 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm font-medium text-slate-700 dark:text-slate-300"
            >Read-only field</span
          >
        </label>

        <!-- Examples -->
        <div>
          <label :class="labelClass"> Examples </label>
          <textarea
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

<script setup>
import { ref, computed, watch } from 'vue'
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

const props = defineProps({
  property: {
    type: Object,
    required: true,
  },
  propertyKey: {
    type: String,
    required: true,
  },
  advancedMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update', 'update-key'])

const localProperty = ref(JSON.parse(JSON.stringify(props.property)))
const showPatternHelp = ref(false)
const enumValues = ref(props.property.enum ? [...props.property.enum] : [])
const examplesText = ref(props.property.examples ? props.property.examples.join('\n') : '')

// Type Icons + colors: shared via @/utils/schemaTypeIcons

// Computed properties
const typeIcon = computed(() => getTypeIcon(localProperty.value.type))

const typeColorClass = computed(() => getTypeColor(localProperty.value.type))

const isInteger = computed({
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
    const cleaned = {}

    // Always include type
    cleaned.type = newValue.type

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

const removeEnumValue = (index) => {
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
const isRequired = (propKey) => {
  return localProperty.value.required && localProperty.value.required.includes(propKey)
}

const toggleRequired = (propKey) => {
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
  const newProperty = {
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
