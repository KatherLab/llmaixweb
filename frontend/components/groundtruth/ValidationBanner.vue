<template>
  <div v-if="status" class="ml-2">
    <div v-if="status.errors?.length" class="p-2 bg-red-50 text-red-700 rounded text-xs">
      <b>{{ status.errors.length }} validation errors</b>:
      <ul class="list-disc pl-4">
        <li v-for="e in status.errors.slice(0,5)" :key="e">{{ e }}</li>
        <li v-if="status.errors.length > 5">...and {{ status.errors.length - 5 }} more</li>
      </ul>
    </div>
    <div v-else-if="status.warnings?.length" class="p-2 bg-yellow-50 text-yellow-800 rounded text-xs">
      <b>{{ status.warnings.length }} warning(s)</b>:
      <ul class="list-disc pl-4">
        <li v-for="w in status.warnings.slice(0,5)" :key="w">{{ w }}</li>
        <li v-if="status.warnings.length > 5">...and {{ status.warnings.length - 5 }} more</li>
      </ul>
    </div>
    <div v-else class="p-2 bg-green-50 text-green-700 rounded text-xs">
      Validation passed!
    </div>
  </div>
</template>
<script setup>
const props = defineProps({ status: Object });
</script>
