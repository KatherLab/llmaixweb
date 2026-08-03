<template>
  <!--
    These two are credentials for someone else's LLM endpoint, not a login for
    this site. Browsers ignore `autocomplete="off"` on a password field when
    they hold a saved credential for the origin, so an autofilled password used
    to land here silently — and any non-empty key flips the whole dialog into
    custom-API mode, which then fails to list models. Hence
    `autocomplete="new-password"`, non-credential field names, and the
    password-manager opt-outs.
  -->
  <div class="mt-2 bg-surface-muted border border-default rounded-card p-4 grid gap-6">
    <FormField
      v-model="apiKey"
      :label="$t('trials.custom_api.api_key_label')"
      type="password"
      maxlength="512"
      :placeholder="$t('trials.custom_api.api_key_placeholder')"
      autocomplete="new-password"
      name="llm_api_key"
      ignore-password-managers
    />
    <FormField
      v-model="baseUrl"
      :label="$t('trials.custom_api.base_url_label')"
      type="text"
      maxlength="512"
      :placeholder="$t('trials.custom_api.base_url_placeholder')"
      autocomplete="off"
      name="llm_base_url"
      ignore-password-managers
    />
  </div>
</template>

<script setup lang="ts">
import FormField from '@/components/common/FormField.vue'

const apiKey = defineModel<string>('apiKey', { default: '' })
const baseUrl = defineModel<string>('baseUrl', { default: '' })
</script>
