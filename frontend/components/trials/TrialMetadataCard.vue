<template>
  <div
    class="mb-8 bg-surface rounded-modal border border-default shadow flex items-center px-6 py-5 gap-4"
  >
    <div class="flex-shrink-0">
      <Info class="w-8 h-8 text-primary" />
    </div>
    <div class="w-full">
      <div class="grid grid-cols-1 gap-4">
        <div>
          <label :class="[labelClass, 'tracking-wide']"
            >Trial Name <span class="text-content-subtle font-normal">(optional)</span></label
          >
          <input
            v-model="name"
            :class="inputClass"
            maxlength="100"
            placeholder="E.g. Contract Extraction Run Q3"
          />
        </div>
        <div>
          <label :class="[labelClass, 'tracking-wide']"
            >Description <span class="text-content-subtle font-normal">(optional)</span></label
          >
          <textarea
            v-model="description"
            :class="textareaClass"
            maxlength="512"
            placeholder="Short summary for this trial (e.g. doc type, goal, changes etc)"
            rows="2"
          ></textarea>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Info } from '@lucide/vue'
import { inputClass, textareaClass, labelClass } from '@/utils/formStyles'

const name = defineModel<string>('name', { default: '' })
const description = defineModel<string>('description', { default: '' })
</script>
