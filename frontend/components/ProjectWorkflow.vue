<template>
  <nav class="w-full flex flex-col items-center py-2" aria-label="Workflow">
    <ol class="flex w-full max-w-5xl justify-between items-center relative">
      <li
        v-for="(step, idx) in steps"
        :key="step.id"
        class="relative flex-1 flex flex-col items-center group"
      >
        <!-- Horizontal connector bar, except for the first step -->
        <div
          v-if="idx > 0"
          class="absolute left-0 top-1/2 h-0.5 w-1/2"
          :class="[
            idx <= currentIdx ? 'bg-blue-400' : 'bg-gray-200'
          ]"
          style="transform: translateY(-50%); z-index: 0;"
        ></div>
        <div
          v-if="idx < steps.length - 1"
          class="absolute right-0 top-1/2 h-0.5 w-1/2"
          :class="[
            idx < currentIdx ? 'bg-blue-400' : 'bg-gray-200'
          ]"
          style="transform: translateY(-50%); z-index: 0;"
        ></div>

        <!-- Step circle -->
        <button
          @click="$emit('change-step', step.id)"
          class="relative z-10 flex items-center justify-center w-11 h-11 rounded-full border-2 transition-all duration-200
            focus:outline-none focus:ring-2 focus:ring-blue-400"
          :class="[
            idx < currentIdx
              ? 'bg-blue-50 border-blue-300 shadow-sm'
              : idx === currentIdx
                ? 'bg-white border-blue-500 shadow ring-2 ring-blue-200 scale-105'
                : 'bg-white border-gray-300 shadow'
          ]"
        >
          <!-- Checkmark for completed -->
          <span v-if="idx < currentIdx" class="text-blue-500">
            <svg class="w-5 h-5" viewBox="0 0 20 20" fill="none"><path d="M6 10.5l3 3 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
          <!-- Step number -->
          <span v-else class="text-base font-bold"
                :class="idx === currentIdx ? 'text-blue-600' : 'text-blue-400'">
            {{ idx + 1 }}
          </span>
        </button>
        <!-- Step name -->
        <div class="mt-1 text-xs font-semibold leading-tight text-center"
            :class="[
              idx === currentIdx ? 'text-blue-600'
                : idx < currentIdx ? 'text-blue-400'
                : 'text-gray-400'
            ]">
          {{ step.name }}
        </div>
      </li>
    </ol>
  </nav>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  currentStep: { type: String, required: true }
});
const emit = defineEmits(['change-step']);

const steps = [
  { id: 'files', name: 'Upload Files' },
  { id: 'preprocessing', name: 'Preprocess' },
  { id: 'documents', name: 'Documents' },
  { id: 'schemas', name: 'Schemas' },
  { id: 'trials', name: 'Run Trials' },
  { id: 'evaluation', name: 'Evaluation' }
];

const currentIdx = computed(() =>
  steps.findIndex(s => s.id === props.currentStep)
);
</script>
