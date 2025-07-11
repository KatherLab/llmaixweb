<template>
  <div class="space-y-6">
    <!-- Basic Information -->
    <div class="space-y-4">
      <h4 class="text-sm font-medium text-gray-900 flex items-center">
        <svg class="h-4 w-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Basic Information
      </h4>

      <!-- Add this if not editing root -->
      <div v-if="propertyKey !== '__root__' && propertyKey !== 'items'">
        <label class="block text-sm font-medium text-gray-700 mb-1">
          {{ advancedMode ? 'Property Key' : 'Field Name' }}
        </label>
        <input
          :value="propertyKey"
          @input="$emit('update-key', $event.target.value)"
          class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
          placeholder="property_name"
          pattern="^[a-zA-Z_][a-zA-Z0-9_]*$"
        />
        <p class="mt-1 text-xs text-gray-500">
          Use lowercase with underscores (e.g., patient_name)
        </p>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            {{ advancedMode ? 'Title' : 'Display Name' }}
          </label>
          <input
            v-model="localProperty.title"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            :placeholder="`${propertyKey} display name`"
          />
        </div>

        <!-- Update the type select dropdown (around line 35) -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            {{ advancedMode ? 'Type' : 'Field Type' }}
          </label>
          <div class="relative group">
            <select
              v-model="localProperty.type"
              @change="onTypeChange"
              class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm pl-10"
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
              <div class="bg-gray-900 text-white text-xs rounded-lg p-2 shadow-lg">
                <p v-if="localProperty.type === 'string'">Text field for names, descriptions, etc.</p>
                <p v-else-if="localProperty.type === 'number'">Numeric values with optional decimals</p>
                <p v-else-if="localProperty.type === 'boolean'">True/false checkbox or toggle</p>
                <p v-else-if="localProperty.type === 'object'">Container for grouped fields</p>
                <p v-else-if="localProperty.type === 'array'">List of repeating items</p>
              </div>
            </div>
          </div>
        </div>

      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <textarea
          v-model="localProperty.description"
          rows="2"
          class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
          placeholder="Describe what this field captures..."
        />
      </div>
    </div>

    <!-- Type-specific Settings -->
    <div v-if="localProperty.type === 'string'" class="space-y-4">
      <h4 class="text-sm font-medium text-gray-900 flex items-center">
        <svg class="h-4 w-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        Text Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Minimum Length
          </label>
          <input
            v-model.number="localProperty.minLength"
            type="number"
            min="0"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Maximum Length
          </label>
          <input
            v-model.number="localProperty.maxLength"
            type="number"
            min="0"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="No maximum"
          />
        </div>
      </div>

      <!-- Format Selection -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Format
        </label>
        <select
          v-model="localProperty.format"
          class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
        >
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
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Pattern (Regular Expression)
          <button
            @click="showPatternHelp = !showPatternHelp"
            class="ml-1 text-gray-400 hover:text-gray-600"
          >
            <svg class="h-4 w-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </label>
        <input
          v-model="localProperty.pattern"
          class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
          placeholder="e.g., ^[A-Z]{2}[0-9]{4}$"
        />
        <div v-if="showPatternHelp" class="mt-2 p-3 bg-blue-50 rounded-md text-xs text-gray-700">
          <p class="font-medium mb-1">Common patterns:</p>
          <ul class="space-y-1">
            <li><code class="bg-white px-1 rounded">^[0-9]+$</code> - Numbers only</li>
            <li><code class="bg-white px-1 rounded">^[A-Za-z]+$</code> - Letters only</li>
            <li><code class="bg-white px-1 rounded">^[A-Z]{2}[0-9]{4}$</code> - 2 uppercase letters + 4 digits</li>
          </ul>
        </div>
      </div>

      <!-- Enum Values -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Allowed Values (Options)
        </label>
        <div class="space-y-2">
          <div
            v-for="(value, index) in enumValues"
            :key="index"
            class="flex items-center space-x-2"
          >
            <input
              v-model="enumValues[index]"
              class="flex-1 border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="Option value"
            />
            <button
              @click="removeEnumValue(index)"
              class="text-red-600 hover:text-red-800 p-1"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
          <button
            @click="addEnumValue"
            class="w-full py-2 border-2 border-dashed border-gray-300 rounded-md text-sm text-gray-600 hover:border-gray-400 hover:text-gray-700"
          >
            + Add Option
          </button>
        </div>
      </div>
    </div>

    <!-- Number Settings -->
    <div v-else-if="localProperty.type === 'number'" class="space-y-4">
      <h4 class="text-sm font-medium text-gray-900 flex items-center">
        <svg class="h-4 w-4 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
        </svg>
        Number Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Minimum Value
          </label>
          <input
            v-model.number="localProperty.minimum"
            type="number"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Maximum Value
          </label>
          <input
            v-model.number="localProperty.maximum"
            type="number"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="No maximum"
          />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Multiple Of
          </label>
          <input
            v-model.number="localProperty.multipleOf"
            type="number"
            step="any"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="e.g., 0.01 for cents"
          />
        </div>

        <div>
          <label class="flex items-center space-x-2">
            <input
              type="checkbox"
              v-model="isInteger"
              class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm font-medium text-gray-700">Integer only</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Boolean Settings -->
    <div v-else-if="localProperty.type === 'boolean'" class="space-y-4">
      <h4 class="text-sm font-medium text-gray-900 flex items-center">
        <svg class="h-4 w-4 mr-2 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Yes/No Settings
      </h4>

      <p class="text-sm text-gray-600">
        This field will capture true/false values. The user interface will show this as a checkbox or toggle switch.
      </p>
    </div>

    <!-- Array Settings -->
    <div v-else-if="localProperty.type === 'array'" class="space-y-4">
      <h4 class="text-sm font-medium text-gray-900 flex items-center">
        <svg class="h-4 w-4 mr-2 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
        List Settings
      </h4>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Minimum Items
          </label>
          <input
            v-model.number="localProperty.minItems"
            type="number"
            min="0"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="No minimum"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Maximum Items
          </label>
          <input
            v-model.number="localProperty.maxItems"
            type="number"
            min="0"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="No maximum"
          />
        </div>
      </div>

      <div>
        <label class="flex items-center space-x-2">
          <input
            type="checkbox"
            v-model="localProperty.uniqueItems"
            class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm font-medium text-gray-700">Items must be unique</span>
        </label>
      </div>
    </div>

    <!-- Object Settings -->
    <div v-else-if="localProperty.type === 'object'" class="space-y-4">
      <h4 class="text-sm font-medium text-gray-900 flex items-center">
        <svg class="h-4 w-4 mr-2 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        Group Settings
      </h4>

      <!-- Required Properties -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Required Fields
        </label>
        <div class="space-y-2">
          <label
            v-for="(propSchema, propKey) in localProperty.properties"
            :key="propKey"
            class="flex items-center space-x-2"
          >
            <input
              type="checkbox"
              :checked="isRequired(propKey)"
              @change="toggleRequired(propKey)"
              class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm text-gray-700">{{ propKey }}</span>
            <span class="text-xs text-gray-500">({{ propSchema.type }})</span>
          </label>
        </div>
        <p v-if="!localProperty.properties || Object.keys(localProperty.properties).length === 0" class="text-sm text-gray-500">
          Add properties to this group first
        </p>
      </div>

      <div v-if="advancedMode">
        <label class="flex items-center space-x-2">
          <input
            type="checkbox"
            v-model="localProperty.additionalProperties"
            class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm font-medium text-gray-700">Allow additional properties</span>
        </label>
      </div>
    </div>

    <!-- Common Settings -->
    <div class="space-y-4 pt-4 border-t">
      <h4 class="text-sm font-medium text-gray-900">Additional Settings</h4>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Default Value
        </label>
        <div v-if="localProperty.type === 'boolean'" class="flex items-center space-x-4">
          <label class="flex items-center space-x-2">
            <input
              type="radio"
              :value="undefined"
              :checked="localProperty.default === undefined"
              @change="localProperty.default = undefined"
              class="border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm">No default</span>
          </label>
          <label class="flex items-center space-x-2">
            <input
              type="radio"
              :value="true"
              v-model="localProperty.default"
              class="border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm">True</span>
          </label>
          <label class="flex items-center space-x-2">
            <input
              type="radio"
              :value="false"
              v-model="localProperty.default"
              class="border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="text-sm">False</span>
          </label>
        </div>
        <input
          v-else-if="localProperty.type === 'string'"
          v-model="localProperty.default"
          type="text"
          class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
          placeholder="No default value"
        />
        <input
          v-else-if="localProperty.type === 'number'"
          v-model.number="localProperty.default"
          type="number"
          class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
          placeholder="No default value"
        />
        <p v-else class="text-sm text-gray-500">
          Default values for {{ localProperty.type }} must be set in raw JSON mode
        </p>
      </div>

      <!-- Advanced Features -->
      <div v-if="advancedMode" class="space-y-4 pt-4 border-t">
        <h4 class="text-sm font-medium text-gray-900">Advanced Features</h4>

        <!-- Read Only -->
        <label class="flex items-center space-x-2">
          <input
            type="checkbox"
            v-model="localProperty.readOnly"
            class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span class="text-sm font-medium text-gray-700">Read-only field</span>
        </label>

        <!-- Examples -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Examples
          </label>
          <textarea
            v-model="examplesText"
            rows="2"
            class="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
            placeholder="Enter examples, one per line"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, h } from 'vue';

const props = defineProps({
  property: {
    type: Object,
    required: true
  },
  propertyKey: {
    type: String,
    required: true
  },
  advancedMode: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update', 'update-key']);

const localProperty = ref(JSON.parse(JSON.stringify(props.property)));
const showPatternHelp = ref(false);
const enumValues = ref(props.property.enum ? [...props.property.enum] : []);
const examplesText = ref(props.property.examples ? props.property.examples.join('\n') : '');

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
  return icons[localProperty.value.type] || StringIcon;
});

const typeColorClass = computed(() => {
  const colors = {
    string: 'bg-green-500',
    number: 'bg-blue-500',
    boolean: 'bg-purple-500',
    object: 'bg-orange-500',
    array: 'bg-pink-500'
  };
  return colors[localProperty.value.type] || 'bg-gray-500';
});

const isInteger = computed({
  get: () => localProperty.value.type === 'integer',
  set: (value) => {
    localProperty.value.type = value ? 'integer' : 'number';
  }
});

// Watch for changes and emit updates
watch(localProperty, (newValue) => {
  // Clean up the property before emitting
  const cleaned = {};

  // Always include type
  cleaned.type = newValue.type;

  // Add other properties based on type
  for (const [key, value] of Object.entries(newValue)) {
    // Skip if it's undefined, null, or empty string
    if (value === undefined || value === null || value === '') {
      continue;
    }

    // Skip type since we already added it
    if (key === 'type') {
      continue;
    }

    // Filter out properties that don't belong to the current type
    const isStringProp = ['enum', 'pattern', 'minLength', 'maxLength', 'format'].includes(key);
    const isNumberProp = ['minimum', 'maximum', 'multipleOf'].includes(key);
    const isArrayProp = ['minItems', 'maxItems', 'uniqueItems', 'items'].includes(key);
    const isObjectProp = ['properties', 'required', 'additionalProperties'].includes(key);
    const isCommonProp = ['title', 'description', 'default', 'examples', 'readOnly'].includes(key);

    // Only include properties that are common or belong to the current type
    if (isCommonProp) {
      cleaned[key] = value;
    } else if (newValue.type === 'string' && isStringProp) {
      cleaned[key] = value;
    } else if ((newValue.type === 'number' || newValue.type === 'integer') && isNumberProp) {
      cleaned[key] = value;
    } else if (newValue.type === 'array' && isArrayProp) {
      cleaned[key] = value;
    } else if (newValue.type === 'object' && isObjectProp) {
      cleaned[key] = value;
    } else if (newValue.type === 'boolean') {
      // Boolean has no specific properties besides common ones
      continue;
    }
  }

  emit('update', cleaned);
}, { deep: true });



// Enum management
watch(enumValues, (newValues) => {
  const filtered = newValues.filter(v => v && v.trim());
  if (filtered.length > 0) {
    localProperty.value.enum = filtered;
  } else {
    // Important: use Vue's delete to ensure reactivity
    if (localProperty.value.enum) {
      delete localProperty.value.enum;
    }
  }
}, { deep: true });


const addEnumValue = () => {
  enumValues.value.push('');
};

const removeEnumValue = (index) => {
  enumValues.value.splice(index, 1);
};

// Examples management
watch(examplesText, (newText) => {
  const examples = newText.split('\n').filter(line => line.trim());
  if (examples.length > 0) {
    localProperty.value.examples = examples;
  } else {
    delete localProperty.value.examples;
  }
});

// Required fields management
const isRequired = (propKey) => {
  return localProperty.value.required && localProperty.value.required.includes(propKey);
};

const toggleRequired = (propKey) => {
  if (!localProperty.value.required) {
    localProperty.value.required = [];
  }

  const index = localProperty.value.required.indexOf(propKey);
  if (index === -1) {
    localProperty.value.required.push(propKey);
  } else {
    localProperty.value.required.splice(index, 1);
  }

  if (localProperty.value.required.length === 0) {
    delete localProperty.value.required;
  }
};

// Type change handler
const onTypeChange = () => {
  // Store the values we want to preserve
  const preservedTitle = localProperty.value.title || '';
  const preservedDescription = localProperty.value.description || '';
  const newType = localProperty.value.type;

  // Create a completely new object with only the type and preserved values
  const newProperty = {
    type: newType
  };

  // Only add title and description if they have values
  if (preservedTitle) {
    newProperty.title = preservedTitle;
  }
  if (preservedDescription) {
    newProperty.description = preservedDescription;
  }

  // Add type-specific defaults
  if (newProperty.type === 'object') {
    newProperty.properties = {};
  } else if (newProperty.type === 'array') {
    newProperty.items = { type: 'string' };
  }

  // Replace the entire localProperty value
  localProperty.value = newProperty;

  // Clear enum values
  enumValues.value = [];

  // Clear examples text
  examplesText.value = '';

  // Emit the clean property immediately
  emit('update', newProperty);
};


// Clear undefined values before emitting
const cleanProperty = (prop) => {
  const cleaned = {};
  for (const [key, value] of Object.entries(prop)) {
    if (value !== undefined && value !== '') {
      cleaned[key] = value;
    }
  }
  return cleaned;
};
</script>
