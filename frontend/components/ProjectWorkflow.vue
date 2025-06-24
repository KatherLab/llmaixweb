<!-- src/components/ProjectWorkflow.vue -->
<template>
  <div class="w-full">
    <div class="flex flex-col space-y-4 sm:hidden">
      <label for="current-step" class="sr-only">Select a step</label>
      <select
        id="current-step"
        v-model="selectedStep"
        @change="$emit('change-step', selectedStep)"
        class="block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
      >
        <option v-for="step in steps" :key="step.id" :value="step.id">{{ step.name }}</option>
      </select>
    </div>

    <nav class="hidden sm:flex" aria-label="Project workflow">
      <ol class="flex items-center w-full">
        <li
          v-for="(step, index) in steps"
          :key="step.id"
          :class="[
            'relative flex items-center',
            index < steps.length - 1 ? 'pr-8 w-full' : ''
          ]"
        >
          <div
            class="flex items-center"
            :class="{ 'group': step.id !== currentStep }"
            @click="$emit('change-step', step.id)"
          >
            <span
              class="flex items-center justify-center w-10 h-10 rounded-full text-sm font-medium"
              :class="[
                step.id === currentStep
                  ? 'bg-blue-600 text-white'
                  : isStepComplete(index)
                    ? 'bg-blue-100 text-blue-600 group-hover:bg-blue-200'
                    : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200'
              ]"
            >
              <span v-if="isStepComplete(index) && step.id !== currentStep">
                <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
              </span>
              <span v-else>{{ index + 1 }}</span>
            </span>
            <span
              class="ml-3 text-sm font-medium cursor-pointer"
              :class="[
                step.id === currentStep
                  ? 'text-blue-600'
                  : isStepComplete(index)
                    ? 'text-blue-600 group-hover:text-blue-800'
                    : 'text-gray-500 group-hover:text-gray-700'
              ]"
            >
              {{ step.name }}
            </span>
          </div>

          <div v-if="index < steps.length - 1" class="hidden sm:block w-full bg-gray-200 h-0.5 ml-4"></div>
        </li>
      </ol>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  currentStep: {
    type: String,
    default: 'files'
  }
});

defineEmits(['change-step']);

const steps = [
  { id: 'files', name: 'Upload Files' },
  { id: 'preprocessing', name: 'Preprocess Files' },
  { id: 'documents', name: 'Documents' },
  { id: 'schemas', name: 'JSON Schemas' },
  { id: 'trials', name: 'Run Trials' },
  { id: 'results', name: 'Results' }
];

const selectedStep = ref(props.currentStep);

// Determine which steps are "complete" based on the current step
const isStepComplete = (stepIndex) => {
  const currentStepIndex = steps.findIndex(step => step.id === props.currentStep);
  return stepIndex < currentStepIndex;
};
</script>
