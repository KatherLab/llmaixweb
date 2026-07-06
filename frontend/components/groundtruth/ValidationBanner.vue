<template>
  <div v-if="status" class="ml-2">
    <Callout v-if="status.errors?.length" variant="danger" class="text-xs">
      <b>{{ status.errors.length }} validation errors</b>:
      <ul class="list-disc pl-4">
        <li v-for="e in status.errors.slice(0, 5)" :key="e">{{ e }}</li>
        <li v-if="status.errors.length > 5">...and {{ status.errors.length - 5 }} more</li>
      </ul>
    </Callout>
    <Callout v-else-if="status.warnings?.length" variant="warning" class="text-xs">
      <b>{{ status.warnings.length }} warning(s)</b>:
      <ul class="list-disc pl-4">
        <li v-for="w in status.warnings.slice(0, 5)" :key="w">{{ w }}</li>
        <li v-if="status.warnings.length > 5">...and {{ status.warnings.length - 5 }} more</li>
      </ul>
    </Callout>
    <Callout v-else variant="success" class="text-xs"> Validation passed! </Callout>
  </div>
</template>
<script setup lang="ts">
import Callout from '@/components/common/Callout.vue'

interface ValidationStatus {
  errors?: string[]
  warnings?: string[]
}

defineProps<{ status?: ValidationStatus }>()
</script>
