<template>
  <div class="mt-2 p-2 bg-gray-50 rounded-lg border text-xs max-h-64 overflow-auto w-full">
    <div class="font-bold mb-1">Ground Truth Sample</div>
    <div v-if="format === 'json' || format === 'zip'">
      <pre class="break-all whitespace-pre-wrap">{{ prettyJson(doc) }}</pre>
    </div>
    <div v-else>
      <table class="w-full text-xs">
        <tr v-for="(v, k) in doc" :key="k">
          <td class="font-mono text-gray-700 py-0.5 pr-2">{{ k }}</td>
          <td class="text-gray-500 py-0.5">{{ v }}</td>
        </tr>
      </table>
    </div>
  </div>
</template>
<script setup>
const props = defineProps({
  doc: Object,
  format: String,
});
function prettyJson(o) {
  try {
    return JSON.stringify(o, null, 2);
  } catch {
    return "";
  }
}
</script>
