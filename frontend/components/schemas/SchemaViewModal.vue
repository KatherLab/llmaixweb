<template>
  <BaseModal
    :open="open"
    size="lg"
    body-class="p-6"
    footer-class="dark:bg-slate-800"
    @close="emit('close')"
  >
    <template #header>
      <div class="flex items-center gap-2">
        <h3 class="text-lg font-medium text-slate-900 dark:text-white">
          {{ schema?.schema_name }}
        </h3>
        <span
          v-if="isSnapshot"
          :class="['text-[10px] uppercase tracking-wide px-2 py-0.5 rounded', getPillClass('blue')]"
          title="Frozen copy of the schema as it was when the trial ran"
          >Snapshot</span
        >
      </div>
    </template>

    <div class="bg-slate-50 dark:bg-slate-800 p-4 rounded-md overflow-auto max-h-96">
      <SchemaFieldList :schema-definition="schema?.schema_definition" show-raw-json-toggle />
    </div>

    <template #footer>
      <BaseButton v-if="copyable" variant="primary" @click="copyToClipboard">Copy</BaseButton>
      <BaseButton variant="secondary" @click="emit('close')">Close</BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import SchemaFieldList from './SchemaFieldList.vue'
import { getPillClass } from '@/utils/statusStyles'
import type { Schema } from '@/types'

interface Props {
  open: boolean
  schema?: Schema | null
  isSnapshot?: boolean
  copyable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  schema: null,
  isSnapshot: false,
  copyable: true,
})

const emit = defineEmits<{
  close: []
}>()

const toast = useToast()

function copyToClipboard() {
  if (!props.schema) return
  navigator.clipboard.writeText(JSON.stringify(props.schema.schema_definition, null, 2))
  toast.success('Schema copied!')
}
</script>
