<template>
  <div>
    <!-- Friendly field list (default view) -->
    <ul v-if="fields.length" class="space-y-1">
      <li
        v-for="field in fields"
        :key="field.path"
        :style="{ paddingLeft: `${field.depth * 1.25}rem` }"
        class="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-3 py-1"
      >
        <!-- Type badge -->
        <span
          :class="[
            getTypePillClass(field.type),
            'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap shrink-0 w-fit',
          ]"
        >
          <component :is="getTypeIcon(field.type)" class="h-3 w-3" aria-hidden="true" />
          {{ typeLabel(field.type) }}
        </span>

        <!-- Name + path + required -->
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-sm font-medium text-slate-800 dark:text-slate-200">{{
              field.name
            }}</span>
            <span
              v-if="field.required"
              class="text-[10px] font-semibold uppercase tracking-wide text-pink-600 dark:text-pink-400"
              >required</span
            >
            <span v-if="field.enum.length" class="text-[10px] text-slate-500 dark:text-slate-400"
              >{{ field.enum.length }} options</span
            >
            <span v-if="field.format" class="text-[10px] text-slate-500 dark:text-slate-400">{{
              field.format
            }}</span>
          </div>
          <p
            v-if="field.description"
            class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 break-words"
          >
            {{ field.description }}
          </p>
        </div>
      </li>
    </ul>
    <p v-else class="text-sm text-slate-500 dark:text-slate-400 italic">No fields defined.</p>

    <!-- Optional raw JSON for advanced users (collapsed by default) -->
    <details v-if="showRawJsonToggle" class="mt-4">
      <summary class="text-xs text-blue-700 dark:text-blue-400 cursor-pointer hover:underline">
        Show raw JSON (advanced)
      </summary>
      <pre
        class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded p-2 mt-1 max-h-64 overflow-auto font-mono text-xs text-slate-700 dark:text-slate-300"
        >{{ formatJSON(schemaDefinition) }}</pre>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { flattenSchemaFields } from '@/utils/schemaFieldList'
import { formatJSON } from '@/utils/schemaTemplates'
import { getTypeIcon, getTypePillClass } from '@/utils/schemaTypeIcons'
import type { SchemaDefinition } from '@/types'

interface Props {
  schemaDefinition?: SchemaDefinition | string | null
  showRawJsonToggle?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  schemaDefinition: null,
  showRawJsonToggle: false,
})

const fields = computed(() => flattenSchemaFields(props.schemaDefinition))

const typeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    string: 'Text',
    number: 'Number',
    integer: 'Integer',
    boolean: 'Yes/No',
    object: 'Group',
    array: 'List',
    any: 'Any',
  }
  return labels[type] || type
}
</script>
