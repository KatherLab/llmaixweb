<template>
  <div class="mt-2 bg-surface-muted border border-default rounded-card p-4 grid gap-6">
    <FormField
      v-model="apiKey"
      :label="$t('trials.custom_api.api_key_label')"
      type="password"
      maxlength="512"
      :placeholder="$t('trials.custom_api.api_key_placeholder')"
      autocomplete="off"
    />
    <FormField
      v-model="baseUrl"
      :label="$t('trials.custom_api.base_url_label')"
      type="text"
      maxlength="512"
      :placeholder="$t('trials.custom_api.base_url_placeholder')"
      autocomplete="off"
    />
  </div>
</template>

<script setup lang="ts">
import FormField from '@/components/common/FormField.vue'

const apiKey = defineModel<string>('apiKey', { default: '' })
const baseUrl = defineModel<string>('baseUrl', { default: '' })
</script>
