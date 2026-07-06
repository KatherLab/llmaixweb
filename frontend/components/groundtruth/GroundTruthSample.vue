<template>
  <div
    class="mt-2 p-2 bg-surface-muted rounded-card border border-default text-xs max-h-64 overflow-auto w-full"
  >
    <div class="font-bold mb-1 text-content-muted">Ground Truth Sample</div>
    <div v-if="format === 'json' || format === 'zip'">
      <pre class="break-all whitespace-pre-wrap text-content-muted">{{ prettyJson(doc) }}</pre>
    </div>
    <div v-else>
      <table class="w-full text-xs">
        <tr v-for="(v, k) in doc" :key="k">
          <td class="font-mono text-content-muted py-0.5 pr-2">{{ k }}</td>
          <td class="text-content-muted py-0.5">{{ v }}</td>
        </tr>
      </table>
    </div>
  </div>
</template>
<script setup lang="ts">
interface Props {
  doc?: Record<string, unknown>
  format?: string
}

withDefaults(defineProps<Props>(), {
  doc: () => ({}),
  format: '',
})

function prettyJson(o: unknown): string {
  try {
    return JSON.stringify(o, null, 2)
  } catch {
    return ''
  }
}
</script>
