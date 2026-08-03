<template>
  <div class="mt-2 bg-surface-muted border border-default rounded-card p-4 grid gap-6">
    <div>
      <label :class="labelClass" for="advanced-max-completion-tokens">
        {{ $t('trials.advanced.max_tokens_label') }}
        <span class="text-content-subtle font-normal">{{ $t('trials.advanced.optional') }}</span>
      </label>
      <input
        id="advanced-max-completion-tokens"
        v-model="maxCompletionTokens"
        :class="inputClass"
        min="1"
        :placeholder="$t('trials.advanced.max_tokens_placeholder')"
        type="number"
      />
      <p class="mt-1 text-xs text-content-muted">
        {{ $t('trials.advanced.max_tokens_help') }}
      </p>
    </div>
    <div>
      <label :class="labelClass" for="advanced-temperature">
        {{ $t('trials.advanced.temperature_label') }}
        <span class="text-content-subtle font-normal">{{ $t('trials.advanced.optional') }}</span>
      </label>
      <input
        id="advanced-temperature"
        v-model="temperature"
        :class="inputClass"
        min="0"
        max="2"
        step="0.01"
        :placeholder="$t('trials.advanced.temperature_placeholder')"
        type="number"
      />
      <p class="mt-1 text-xs text-content-muted">
        {{ $t('trials.advanced.temperature_help') }}
      </p>
    </div>
    <div>
      <label :class="labelClass" for="advanced-reasoning-effort">
        {{ $t('trials.advanced.reasoning_label') }}
        <span class="text-content-subtle font-normal">{{ $t('trials.advanced.optional') }}</span>
      </label>
      <select id="advanced-reasoning-effort" v-model="reasoningEffort" :class="selectClass">
        <option value="">{{ $t('trials.advanced.reasoning_default') }}</option>
        <option value="low">{{ $t('trials.advanced.reasoning_low') }}</option>
        <option value="medium">{{ $t('trials.advanced.reasoning_medium') }}</option>
        <option value="high">{{ $t('trials.advanced.reasoning_high') }}</option>
      </select>
      <p class="mt-1 text-xs text-content-muted">
        {{ $t('trials.advanced.reasoning_help') }}
      </p>
    </div>
    <div>
      <label :class="labelClass" for="advanced-prompt-language">
        {{ $t('trials.advanced.prompt_language_label') }}
      </label>
      <select id="advanced-prompt-language" v-model="promptLanguage" :class="selectClass">
        <option v-for="code in SUPPORTED_LOCALES" :key="code" :value="code">
          {{ $t(`language.${code}`) }}
        </option>
      </select>
      <p class="mt-1 text-xs text-content-muted">
        {{ $t('trials.advanced.prompt_language_help') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'
import { SUPPORTED_LOCALES } from '@/i18n'

const maxCompletionTokens = defineModel<string>('maxCompletionTokens', { default: '' })
const temperature = defineModel<string>('temperature', { default: '' })
const reasoningEffort = defineModel<string>('reasoningEffort', { default: '' })
// Language of the instructions the backend appends to the prompt (injection
// guard, schema line, evidence rules). Defaults to the UI language upstream.
const promptLanguage = defineModel<string>('promptLanguage', { default: 'en' })
</script>
