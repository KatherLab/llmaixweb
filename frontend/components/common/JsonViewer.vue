<template>
  <div class="json-viewer">
    <div v-if="!data" class="text-content-muted italic text-xs">null</div>
    <div v-else-if="typeof data !== 'object'" class="json-value text-xs">
      {{ formatValue(data) }}
    </div>
    <div v-else class="json-object">
      <div v-for="(value, key) in data" :key="key" class="json-item">
        <div
          class="json-key"
          :class="{ 'json-key-selected': childPath(key) === selectedPath }"
          :tabindex="isExpandable(value) ? 0 : undefined"
          :role="isExpandable(value) ? 'button' : undefined"
          :aria-expanded="isExpandable(value) ? !!expanded[key] : undefined"
          @click="toggleExpanded(key)"
          @keydown.enter.prevent="toggleExpanded(key)"
          @keydown.space.prevent="toggleExpanded(key)"
        >
          <span class="toggle-icon">
            <ChevronRight
              v-if="isExpandable(value)"
              class="w-3 h-3 transition-transform text-content-subtle cursor-pointer inline-block"
              :class="{ 'rotate-90': expanded[key] }"
            />
            <span v-else class="w-3 h-3 inline-block"></span>
          </span>
          <span class="key-name text-xs font-medium text-primary">{{ key }}:</span>
          <template v-if="!isExpandable(value) || !expanded[key]">
            <!-- Provenance-enabled leaves become clickable and carry a
                 confidence dot; without `annotations` this is a plain span and
                 the viewer behaves exactly as before. -->
            <component
              :is="annotationFor(key) ? 'button' : 'span'"
              :type="annotationFor(key) ? 'button' : undefined"
              class="json-value text-xs ml-1 text-left"
              :class="annotationFor(key) ? 'json-value-actionable' : ''"
              :title="annotationFor(key)?.title"
              @click.stop="onValueClick(key)"
            >
              {{ formatValue(value, !expanded[key]) }}
              <span
                v-if="annotationFor(key)"
                class="provenance-dot"
                :class="annotationFor(key)!.dotClass"
                aria-hidden="true"
              />
              <span
                v-if="(annotationFor(key)?.count ?? 0) > 1"
                class="text-[10px] text-content-subtle ml-0.5"
                >×{{ annotationFor(key)!.count }}</span
              >
            </component>
          </template>
        </div>
        <div
          v-if="isExpandable(value) && expanded[key]"
          class="json-children ml-3 pl-2 border-l border-default"
        >
          <JsonViewer
            :data="value as JsonValue"
            :max-depth="(maxDepth ?? 0) - 1"
            :path="childPath(key)"
            :annotations="annotations"
            :selected-path="selectedPath"
            @select="emit('select', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ChevronRight } from '@lucide/vue'

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null

/** Per-leaf provenance summary, keyed by JSON path (see utils/provenance.ts). */
export interface JsonAnnotation {
  dotClass: string
  title: string
  count: number
}

interface Props {
  // Accepts any JSON-shaped value (object, array, primitive, or null).
  data?: JsonValue
  maxDepth?: number
  /** JSON path of `data` itself; children extend it (`a.b[0].c`). */
  path?: string
  /** Optional path→annotation map. Presence turns leaves into select targets. */
  annotations?: Record<string, JsonAnnotation>
  selectedPath?: string
}

const props = withDefaults(defineProps<Props>(), {
  data: null,
  // Children only render once expanded, so a generous limit costs nothing and keeps
  // deeply nested extraction schemas (list → object → list → object) explorable.
  maxDepth: 10,
  path: '',
  annotations: undefined,
  selectedPath: '',
})

const emit = defineEmits<{ (e: 'select', path: string): void }>()

const expanded = reactive<Record<string, boolean>>({})

const isExpandable = (value: unknown): boolean => {
  return !!value && typeof value === 'object' && props.maxDepth > 0
}

/**
 * Path of a child key. Array indices use bracket syntax so the result matches
 * the backend's evidence map (`medications[0].dose`) exactly.
 */
const childPath = (key: string | number): string => {
  if (Array.isArray(props.data)) return `${props.path}[${key}]`
  return props.path ? `${props.path}.${key}` : String(key)
}

const annotationFor = (key: string | number): JsonAnnotation | undefined =>
  props.annotations?.[childPath(key)]

const onValueClick = (key: string | number): void => {
  if (annotationFor(key)) emit('select', childPath(key))
}

const toggleExpanded = (key: string | number): void => {
  const k = String(key)
  // Arrays are indexed by their numeric-string keys here too, so they must not be excluded —
  // otherwise objects inside a list render a chevron that does nothing.
  if (props.data && typeof props.data === 'object') {
    if (isExpandable((props.data as Record<string, unknown>)[k])) {
      expanded[k] = !expanded[k]
    }
  }
}

const formatValue = (value: unknown, collapsed = false): string => {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'string') return `"${value}"`
  if (typeof value === 'boolean') return value.toString()
  if (typeof value === 'number') return value.toString()

  if (Array.isArray(value)) {
    if (collapsed) return `Array(${value.length})`
    return `[${value.length} items]`
  }

  if (typeof value === 'object') {
    if (collapsed) return `Object`
    const keys = Object.keys(value)
    return `{${keys.length} properties}`
  }

  return String(value)
}
</script>

<style scoped>
.json-viewer {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.75rem;
  line-height: 1.4;
}

.json-item {
  margin: 1px 0;
}

.json-key {
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  padding: 1px 0;
  border-radius: 2px;
}

.json-key:hover {
  background-color: var(--color-primary-soft);
}

.json-key-selected {
  background-color: var(--color-primary-soft);
  box-shadow: inset 2px 0 0 var(--color-primary);
}

.toggle-icon {
  width: 12px;
  display: inline-block;
  flex-shrink: 0;
  margin-right: 2px;
}

.key-name {
  margin-right: 4px;
  font-weight: 500;
}

.json-value {
  color: var(--color-primary);
  word-break: break-word;
}

.json-value-actionable {
  cursor: pointer;
  border-radius: 2px;
}

.json-value-actionable:hover {
  text-decoration: underline;
}

.provenance-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  margin-left: 4px;
  vertical-align: middle;
}
</style>
