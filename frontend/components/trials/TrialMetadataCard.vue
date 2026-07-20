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
          <label :class="[labelClass, 'tracking-wide']" for="trial-meta-name"
            >{{ $t('trials.metadata.name_label') }}
            <span class="text-content-subtle font-normal">{{
              $t('trials.metadata.optional')
            }}</span></label
          >
          <input
            id="trial-meta-name"
            v-model="name"
            :class="inputClass"
            maxlength="100"
            :placeholder="$t('trials.metadata.name_placeholder')"
          />
        </div>
        <div>
          <label :class="[labelClass, 'tracking-wide']" for="trial-meta-description"
            >{{ $t('trials.metadata.description_label') }}
            <span class="text-content-subtle font-normal">{{
              $t('trials.metadata.optional')
            }}</span></label
          >
          <textarea
            id="trial-meta-description"
            v-model="description"
            :class="textareaClass"
            maxlength="512"
            :placeholder="$t('trials.metadata.description_placeholder')"
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
