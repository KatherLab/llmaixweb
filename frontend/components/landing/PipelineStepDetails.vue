<template>
  <div class="relative rounded-modal border border-default bg-surface p-8 backdrop-blur-sm">
    <!-- Step 1 Details -->
    <div v-if="step === 1" class="space-y-4">
      <h3 class="text-2xl font-bold text-content mb-4">{{ $t('landing.details.step1.title') }}</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-primary mb-3">
            {{ $t('landing.details.step1.supported_formats') }}
          </h4>
          <div class="space-y-2">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-card bg-primary-soft flex items-center justify-center">
                <span class="text-xs font-bold text-primary">PDF</span>
              </div>
              <span class="text-content-muted">{{ $t('landing.details.step1.format_pdf') }}</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-card bg-primary-soft flex items-center justify-center">
                <span class="text-xs font-bold text-primary">DOC</span>
              </div>
              <span class="text-content-muted">{{ $t('landing.details.step1.format_doc') }}</span>
            </div>
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-card bg-purple-100 flex items-center justify-center dark:bg-purple-500/10"
              >
                <span class="text-xs font-bold text-purple-600 dark:text-purple-400">IMG</span>
              </div>
              <span class="text-content-muted">{{ $t('landing.details.step1.format_img') }}</span>
            </div>
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-card bg-emerald-100 flex items-center justify-center dark:bg-emerald-500/10"
              >
                <span class="text-xs font-bold text-emerald-600 dark:text-emerald-400">CSV</span>
              </div>
              <span class="text-content-muted">{{ $t('landing.details.step1.format_csv') }}</span>
            </div>
          </div>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-primary mb-3">
            {{ $t('landing.details.step1.features') }}
          </h4>
          <ul class="space-y-2 text-content-muted">
            <li v-for="feature in uploadFeatures" :key="feature" class="flex items-start gap-2">
              <CheckIcon />
              {{ feature }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Step 2 Details -->
    <div v-if="step === 2" class="space-y-4">
      <h3 class="text-2xl font-bold text-content mb-4">{{ $t('landing.details.step2.title') }}</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-primary mb-3">
            {{ $t('landing.details.step2.ocr_engines') }}
          </h4>
          <div class="space-y-3">
            <div
              v-for="method in ocrMethods"
              :key="method.name"
              class="p-3 rounded-card bg-surface-muted border border-default"
            >
              <h5 class="font-semibold text-content mb-1">{{ method.name }}</h5>
              <p class="text-sm text-content-muted">{{ method.description }}</p>
            </div>
          </div>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-primary mb-3">
            {{ $t('landing.details.step2.document_parsers') }}
          </h4>
          <div class="space-y-3">
            <div
              v-for="parser in documentParsers"
              :key="parser.name"
              class="p-3 rounded-card bg-surface-muted border border-default"
            >
              <h5 class="font-semibold text-content mb-1">{{ parser.name }}</h5>
              <p class="text-sm text-content-muted">{{ parser.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3 Details -->
    <div v-if="step === 3" class="space-y-4">
      <h3 class="text-2xl font-bold text-content mb-4">{{ $t('landing.details.step3.title') }}</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-purple-600 mb-3 dark:text-purple-400">
            {{ $t('landing.details.step3.organization') }}
          </h4>
          <ul class="space-y-2 text-content-muted">
            <li v-for="feature in documentFeatures" :key="feature" class="flex items-start gap-2">
              <CheckIcon />
              {{ feature }}
            </li>
          </ul>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-purple-600 mb-3 dark:text-purple-400">
            {{ $t('landing.details.step3.selection_for_trials') }}
          </h4>
          <p class="text-content-muted mb-3">{{ $t('landing.details.step3.choose_documents') }}</p>
          <div class="space-y-3">
            <div
              v-for="option in selectionOptions"
              :key="option.name"
              class="p-3 rounded-card bg-purple-50 border border-purple-200 dark:bg-purple-500/10 dark:border-purple-500/30"
            >
              <h5 class="font-semibold text-content mb-1">{{ option.name }}</h5>
              <p class="text-sm text-content-muted">{{ option.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 4 Details -->
    <div v-if="step === 4" class="space-y-4">
      <h3 class="text-2xl font-bold text-content mb-4">{{ $t('landing.details.step4.title') }}</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-pink-600 mb-3 dark:text-pink-400">
            {{ $t('landing.details.step4.tree_based_editor') }}
          </h4>
          <div class="p-4 rounded-card bg-surface-muted border border-default">
            <div class="font-mono text-sm space-y-2">
              <div class="flex items-center gap-2">
                <span class="text-content-subtle">▼</span>
                <span class="text-orange-500 dark:text-orange-400">patient</span>
                <span class="text-content-subtle">:</span>
                <span class="text-primary">object</span>
              </div>
              <div class="ml-6 space-y-2">
                <div
                  v-for="field in schemaTreeFields"
                  :key="field.name"
                  class="flex items-center gap-2"
                >
                  <span class="text-emerald-600 dark:text-emerald-400">{{ field.name }}</span>
                  <span class="text-content-subtle">:</span>
                  <span :class="field.typeClass">{{ field.type }}</span>
                </div>
              </div>
            </div>
          </div>
          <p class="text-sm text-content-muted mt-3">
            {{ $t('landing.details.step4.build_nested') }}
          </p>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-pink-600 mb-3 dark:text-pink-400">
            {{ $t('landing.details.step4.schema_features') }}
          </h4>
          <ul class="space-y-2 text-content-muted">
            <li v-for="feature in schemaFeatures" :key="feature" class="flex items-start gap-2">
              <CheckIcon />
              {{ feature }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Step 5 Details -->
    <div v-if="step === 5" class="space-y-4">
      <h3 class="text-2xl font-bold text-content mb-4">{{ $t('landing.details.step5.title') }}</h3>
      <div class="space-y-6">
        <!-- Visual Flow -->
        <div class="p-6 rounded-card bg-surface-muted border border-default">
          <div class="flex items-center justify-between gap-4">
            <template v-for="(item, index) in extractionFlow" :key="item.label">
              <div class="text-center">
                <div
                  class="w-16 h-16 mx-auto mb-2 rounded-card flex items-center justify-center"
                  :class="item.bg"
                >
                  <component
                    :is="item.icon"
                    v-if="item.icon"
                    class="w-8 h-8"
                    :class="item.iconClass"
                  />
                  <span v-else class="text-2xl font-mono" :class="item.iconClass">{}</span>
                </div>
                <p class="text-sm text-content-muted">{{ item.label }}</p>
              </div>
              <div v-if="index < extractionFlow.length - 1" class="flex-1 flex items-center">
                <div class="w-full h-0.5" :class="flowArrows[index]?.line"></div>
                <ChevronRight class="w-6 h-6 -ml-1" :class="flowArrows[index]?.arrowClass" />
              </div>
            </template>
          </div>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h4 class="text-lg font-semibold text-emerald-600 mb-3 dark:text-emerald-400">
              {{ $t('landing.details.step5.compatible_providers') }}
            </h4>
            <div class="space-y-2">
              <div
                v-for="provider in llmProviders"
                :key="provider.name"
                class="p-3 rounded-card bg-surface-muted border border-default"
              >
                <h5 class="font-semibold text-content mb-1">
                  {{ provider.name }}
                </h5>
                <p class="text-sm text-content-muted">{{ provider.description }}</p>
              </div>
            </div>
          </div>
          <div>
            <h4 class="text-lg font-semibold text-emerald-600 mb-3 dark:text-emerald-400">
              {{ $t('landing.details.step5.trial_configuration') }}
            </h4>
            <ul class="space-y-2 text-content-muted">
              <li v-for="feature in trialConfig" :key="feature" class="flex items-start gap-2">
                <CheckIcon />
                {{ feature }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 6 Details -->
    <div v-if="step === 6" class="space-y-4">
      <h3 class="text-2xl font-bold text-content mb-4">{{ $t('landing.details.step6.title') }}</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-teal-600 mb-3 dark:text-teal-400">
            {{ $t('landing.details.step6.evaluation_process') }}
          </h4>
          <div class="space-y-3">
            <div v-for="item in evaluationProcess" :key="item.step" class="flex items-start gap-3">
              <div
                class="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center flex-shrink-0 mt-0.5 dark:bg-teal-500/20"
              >
                <span class="text-sm font-bold text-teal-600 dark:text-teal-400">{{
                  item.step
                }}</span>
              </div>
              <div>
                <h5 class="font-semibold text-content">{{ item.title }}</h5>
                <p class="text-sm text-content-muted">{{ item.description }}</p>
              </div>
            </div>
          </div>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-teal-600 mb-3 dark:text-teal-400">
            {{ $t('landing.details.step6.metrics_dashboard') }}
          </h4>
          <div class="p-4 rounded-card bg-surface-muted border border-default">
            <div class="space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-content-muted">{{
                  $t('landing.details.step6.overall_accuracy')
                }}</span>
                <span class="text-2xl font-bold text-teal-600 dark:text-teal-400">92.2%</span>
              </div>
              <div class="w-full bg-surface-sunken rounded-full h-2">
                <div
                  class="bg-gradient-to-r from-teal-500 to-emerald-500 h-2 rounded-full"
                  style="width: 92.2%"
                ></div>
              </div>
              <div class="grid grid-cols-2 gap-2 mt-4">
                <div class="text-center p-2 rounded-card bg-surface-sunken">
                  <p class="text-xs text-content-muted">
                    {{ $t('landing.details.step6.documents') }}
                  </p>
                  <p class="text-lg font-bold text-content">8</p>
                </div>
                <div class="text-center p-2 rounded-card bg-surface-sunken">
                  <p class="text-xs text-content-muted">
                    {{ $t('landing.details.step6.field_errors') }}
                  </p>
                  <p class="text-lg font-bold text-content">5</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Close button -->
    <button
      class="absolute top-4 right-4 text-content-subtle hover:text-content transition-colors"
      @click="$emit('close')"
    >
      <X class="w-6 h-6" />
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { FileText, MessageSquare, Database, Zap, ChevronRight, X } from '@lucide/vue'
import CheckIcon from '@/components/landing/CheckIcon.vue'

const { t } = useI18n({ useScope: 'global' })

interface Props {
  step?: number | null
}

withDefaults(defineProps<Props>(), {
  step: null,
})

defineEmits<{ close: [] }>()

// Step 1 data
const uploadFeatures: string[] = [
  t('landing.details.step1.upload_features.batch'),
  t('landing.details.step1.upload_features.detection'),
  t('landing.details.step1.upload_features.duplicate'),
]

// Step 2 data — matches the README's four-engine breakdown
const ocrMethods: { name: string; description: string }[] = [
  {
    name: t('landing.details.step2.methods.quick.name'),
    description: t('landing.details.step2.methods.quick.description'),
  },
  {
    name: t('landing.details.step2.methods.mistral.name'),
    description: t('landing.details.step2.methods.mistral.description'),
  },
  {
    name: t('landing.details.step2.methods.vision.name'),
    description: t('landing.details.step2.methods.vision.description'),
  },
]

const documentParsers: { name: string; description: string }[] = [
  {
    name: t('landing.details.step2.parsers.docling.name'),
    description: t('landing.details.step2.parsers.docling.description'),
  },
  {
    name: t('landing.details.step2.parsers.csv.name'),
    description: t('landing.details.step2.parsers.csv.description'),
  },
]

// Step 3 data
const documentFeatures: string[] = [
  t('landing.details.step3.document_features.sets'),
  t('landing.details.step3.document_features.filter'),
  t('landing.details.step3.document_features.preview'),
  t('landing.details.step3.document_features.track'),
]

const selectionOptions: { name: string; description: string }[] = [
  {
    name: t('landing.details.step3.selection_options.sets.name'),
    description: t('landing.details.step3.selection_options.sets.description'),
  },
  {
    name: t('landing.details.step3.selection_options.individual.name'),
    description: t('landing.details.step3.selection_options.individual.description'),
  },
]

// Step 4 data
const schemaTreeFields: { name: string; type: string; typeClass: string }[] = [
  { name: 'patient_id', type: 'string', typeClass: 'text-yellow-600 dark:text-yellow-400' },
  { name: 'first_name', type: 'string', typeClass: 'text-yellow-600 dark:text-yellow-400' },
  { name: 'diagnosis', type: 'array', typeClass: 'text-purple-600 dark:text-purple-400' },
]

const schemaFeatures: string[] = [
  t('landing.details.step4.schema_feature_items.nested'),
  t('landing.details.step4.schema_feature_items.types'),
  t('landing.details.step4.schema_feature_items.import_export'),
  t('landing.details.step4.schema_feature_items.templates'),
]

// Step 5 data
const extractionFlow: {
  label: string
  bg: string
  icon: Component | null
  iconClass: string
}[] = [
  {
    label: t('landing.details.step5.flow.document'),
    bg: 'bg-primary-soft',
    icon: FileText,
    iconClass: 'text-primary',
  },
  {
    label: t('landing.details.step5.flow.prompt'),
    bg: 'bg-primary-soft',
    icon: MessageSquare,
    iconClass: 'text-primary',
  },
  {
    label: t('landing.details.step5.flow.schema'),
    bg: 'bg-purple-100 dark:bg-purple-500/20',
    icon: Database,
    iconClass: 'text-purple-600 dark:text-purple-400',
  },
  {
    label: t('landing.details.step5.flow.llm_api'),
    bg: 'bg-emerald-100 dark:bg-emerald-500/20',
    icon: Zap,
    iconClass: 'text-emerald-600 dark:text-emerald-400',
  },
  {
    label: t('landing.details.step5.flow.json_output'),
    bg: 'bg-teal-100 dark:bg-teal-500/20',
    icon: null,
    iconClass: 'text-teal-600 dark:text-teal-400',
  },
]

const flowArrows: { line: string; arrowClass: string }[] = [
  { line: 'bg-gradient-to-r from-primary to-primary', arrowClass: 'text-primary' },
  { line: 'bg-gradient-to-r from-primary to-purple-500', arrowClass: 'text-purple-500' },
  { line: 'bg-gradient-to-r from-purple-500 to-emerald-500', arrowClass: 'text-emerald-500' },
  { line: 'bg-gradient-to-r from-emerald-500 to-teal-500', arrowClass: 'text-teal-500' },
]

const llmProviders: { name: string; description: string }[] = [
  {
    name: t('landing.details.step5.providers.openai.name'),
    description: t('landing.details.step5.providers.openai.description'),
  },
  {
    name: t('landing.details.step5.providers.local.name'),
    description: t('landing.details.step5.providers.local.description'),
  },
  {
    name: t('landing.details.step5.providers.custom.name'),
    description: t('landing.details.step5.providers.custom.description'),
  },
]

const trialConfig: string[] = [
  t('landing.details.step5.trial_config.limits'),
  t('landing.details.step5.trial_config.sets'),
  t('landing.details.step5.trial_config.compare'),
  t('landing.details.step5.trial_config.tokens'),
]

// Step 6 data
const evaluationProcess: { step: number; title: string; description: string }[] = [
  {
    step: 1,
    title: t('landing.details.step6.process.upload.title'),
    description: t('landing.details.step6.process.upload.description'),
  },
  {
    step: 2,
    title: t('landing.details.step6.process.map.title'),
    description: t('landing.details.step6.process.map.description'),
  },
  {
    step: 3,
    title: t('landing.details.step6.process.compute.title'),
    description: t('landing.details.step6.process.compute.description'),
  },
]
</script>
