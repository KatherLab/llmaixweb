<template>
  <div>
    <div class="flex items-center gap-1 mb-1.5">
      <label :class="labelClass" for="trial-model-select"
        >{{ $t('trials.select.model_label') }} <span class="text-red-500">*</span></label
      >
      <Tooltip :text="modelHelpText">
        <Info class="h-4 w-4 text-content-subtle hover:text-content-muted" />
      </Tooltip>
    </div>
    <select
      id="trial-model-select"
      v-model="model"
      :disabled="isLoadingModels || isTestingConnection || (availableModels ?? []).length === 0"
      :class="[selectClass, 'disabled:opacity-60 disabled:cursor-not-allowed']"
    >
      <option disabled value="">
        {{
          isLoadingModels || isTestingConnection
            ? $t('trials.select.model_loading')
            : (availableModels ?? []).length === 0
              ? $t('trials.select.model_none')
              : $t('trials.select.model_placeholder')
        }}
      </option>
      <option v-for="mdl in availableModels ?? []" :key="mdl" :value="mdl">
        {{ mdl }}
      </option>
    </select>
    <p class="mt-1 text-xs text-content-muted">
      {{ $t('trials.select.model_help') }}
    </p>
    <div v-if="configStatus?.type === 'error'" class="text-xs text-red-500 mt-1">
      {{ configStatus.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Info } from '@lucide/vue'
import Tooltip from '@/components/common/Tooltip.vue'
import { selectClass, labelClass } from '@/utils/formStyles'

interface StatusDescriptor {
  type: 'loading' | 'warning' | 'error' | 'success' | 'none'
  message: string
}

withDefaults(
  defineProps<{
    availableModels?: string[]
    isLoadingModels?: boolean
    isTestingConnection?: boolean
    configStatus?: StatusDescriptor
  }>(),
  {
    availableModels: () => [],
    isLoadingModels: false,
    isTestingConnection: false,
    configStatus: () => ({ type: 'none', message: '' }),
  },
)

const { t } = useI18n({ useScope: 'global' })

const modelHelpText = t('trials.select.model_help_tooltip')

const model = defineModel<string>({ default: '' })
</script>
