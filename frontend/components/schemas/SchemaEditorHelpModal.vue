<template>
  <BaseModal
    :open="open"
    size="lg"
    :closeable="false"
    :close-on-esc="false"
    body-class="p-6"
    footer-class="bg-surface-muted"
    @close="$emit('close')"
  >
    <template #header>
      <h3 class="text-lg font-semibold text-content">{{ $t('schemaEditor.help.title') }}</h3>
    </template>

    <div class="space-y-4">
      <div>
        <h4 class="font-medium text-content mb-2">{{ $t('schemaEditor.help.field_types') }}</h4>
        <div class="grid grid-cols-2 gap-3">
          <div v-for="type in availableTypes" :key="type.value" class="flex items-start space-x-3">
            <div :class="['rounded-card p-2', type.color]">
              <component :is="type.icon" class="h-5 w-5 text-white" />
            </div>
            <div>
              <p class="font-medium text-sm">{{ type.label }}</p>
              <p class="text-xs text-content-muted">{{ type.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h4 class="font-medium text-content mb-2">{{ $t('schemaEditor.help.tips') }}</h4>
        <ul class="text-sm text-content-muted space-y-1">
          <li>• {{ $t('schemaEditor.help.tip_click') }}</li>
          <li>• {{ $t('schemaEditor.help.tip_breadcrumb') }}</li>
          <li>
            • {{ $t('schemaEditor.help.tip_key_before') }}
            <kbd class="px-1 py-0.5 bg-surface-sunken rounded text-xs">N</kbd>
            {{ $t('schemaEditor.help.tip_key_after') }}
          </li>
          <li>• {{ $t('schemaEditor.help.tip_developer') }}</li>
        </ul>
      </div>
    </div>

    <template #footer>
      <BaseButton variant="secondary" class="w-full" @click="$emit('close')">{{
        $t('schemaEditor.help.close')
      }}</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import type { Component } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface AvailableType {
  value: string
  label: string
  color: string
  icon: Component
  description: string
}

interface Props {
  open: boolean
  availableTypes: AvailableType[]
}

defineProps<Props>()

defineEmits<{
  close: []
}>()
</script>
