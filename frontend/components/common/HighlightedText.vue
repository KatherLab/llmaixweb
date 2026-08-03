<!--
  Plain text with highlighted ranges.

  Takes offsets into the raw string rather than walking rendered DOM (the way
  DocumentTextView's find-in-page does), because provenance ranges are computed
  against exactly this string — the text the model was given. Overlapping
  ranges are resolved by confidence, so a verbatim hit is never hidden under a
  fuzzy one that happens to span it.

  Emits `select` when a highlight is clicked, which is what makes the link
  bidirectional: click a value to find its source, click a source span to find
  the value it fed.
-->
<template>
  <pre
    class="text-xs text-content-muted whitespace-pre-wrap break-words font-mono p-4 overflow-auto h-full"
  ><template v-for="(seg, i) in segments" :key="i"><mark
      v-if="seg.range"
      :ref="(el) => registerMark(el, seg.range!.id)"
      :class="[
        'rounded px-0.5 cursor-pointer transition-shadow',
        PROVENANCE_STYLES[seg.range.kind].mark,
        seg.range.id === activeId ? 'ring-2 ring-primary ring-offset-1 ring-offset-surface-muted' : '',
      ]"
      :title="markTitle(seg.range)"
      @click="emit('select', seg.range.id)"
    >{{ seg.text }}</mark><template v-else>{{ seg.text }}</template></template></pre>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { PROVENANCE_RANK, type ProvenanceKind } from '@/utils/provenance'
import { PROVENANCE_STYLES } from '@/utils/provenanceStyles'

export interface HighlightRange {
  /** Stable id — the leaf path the range belongs to, plus its match index. */
  id: string
  /** Human label of the field this range supports, shown on hover. */
  label?: string
  start: number
  end: number
  kind: ProvenanceKind
}

interface Props {
  text: string
  ranges: HighlightRange[]
  /** The range to emphasise and scroll into view. */
  activeId?: string
}

const props = withDefaults(defineProps<Props>(), {
  activeId: '',
})

const emit = defineEmits<{ (e: 'select', id: string): void }>()

const { t } = useI18n({ useScope: 'global' })

const marks = new Map<string, HTMLElement>()

function registerMark(el: unknown, id: string): void {
  // Vue passes null on unmount — drop the entry rather than holding a detached
  // node for every range the user has cycled through.
  if (el instanceof HTMLElement) marks.set(id, el)
  else if (el === null) marks.delete(id)
}

interface Segment {
  text: string
  range: HighlightRange | null
}

/**
 * Cut the text at every range boundary, then give each piece the strongest
 * range covering it. Splitting on boundaries (rather than nesting) keeps the
 * output a flat list of spans, which is what makes overlaps renderable at all.
 */
const segments = computed<Segment[]>(() => {
  const text = props.text || ''
  const valid = props.ranges.filter((r) => r.start >= 0 && r.end > r.start && r.start < text.length)
  if (!valid.length) return text ? [{ text, range: null }] : []

  const bounds = new Set<number>([0, text.length])
  for (const r of valid) {
    bounds.add(Math.max(0, r.start))
    bounds.add(Math.min(text.length, r.end))
  }
  const points = [...bounds].sort((a, b) => a - b)

  const out: Segment[] = []
  for (let i = 0; i < points.length - 1; i++) {
    const start = points[i]
    const end = points[i + 1]
    if (end <= start) continue
    let winner: HighlightRange | null = null
    for (const r of valid) {
      if (r.start > start || r.end < end) continue
      if (r.id === props.activeId) {
        winner = r
        break
      }
      if (!winner || PROVENANCE_RANK[r.kind] > PROVENANCE_RANK[winner.kind]) winner = r
    }
    const piece = text.slice(start, end)
    // Merge runs of unhighlighted text so the DOM stays small on long documents.
    const prev = out[out.length - 1]
    if (!winner && prev && !prev.range) prev.text += piece
    else out.push({ text: piece, range: winner })
  }
  return out
})

function markTitle(range: HighlightRange): string {
  const tier = t(PROVENANCE_STYLES[range.kind].labelKey)
  return range.label ? `${range.label} — ${tier}` : tier
}

// Bring the active range into view whenever it changes (clicking a value in
// the result pane must land the user on the span, not leave them scrolling).
watch(
  () => props.activeId,
  async (id) => {
    if (!id) return
    await nextTick()
    marks.get(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  },
)

watch(
  () => props.text,
  () => marks.clear(),
)
</script>
