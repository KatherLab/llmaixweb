<template>
  <BaseModal :open="open" title="Trial Schema" size="lg" body-class="p-6" @close="$emit('close')">
    <div class="flex items-center gap-2 mb-2">
      <h4 class="font-semibold">{{ schema?.schema_name }}</h4>
      <span
        v-if="isSnapshot"
        :class="['text-[10px] uppercase tracking-wide px-2 py-0.5 rounded', getPillClass('blue')]"
        title="Frozen copy of the schema as it was when the trial ran"
        >Snapshot</span
      >
    </div>
    <pre class="bg-slate-50 border rounded-md p-4 overflow-x-auto text-xs font-mono max-h-96">{{
      JSON.stringify(schema?.schema_definition, null, 2)
    }}</pre>
    <template #footer>
      <BaseButton variant="primary" @click="copyToClipboard">Copy</BaseButton>
    </template>
  </BaseModal>
</template>
<script setup>
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { getPillClass } from '@/utils/statusStyles'

const props = defineProps({
  open: Boolean,
  schema: { type: Object, default: () => ({}) },
  isSnapshot: { type: Boolean, default: false },
})
defineEmits(['close'])

const toast = useToast()

function copyToClipboard() {
  if (!props.schema) return
  navigator.clipboard.writeText(JSON.stringify(props.schema.schema_definition, null, 2))
  toast.success('Schema copied!')
}
</script>
