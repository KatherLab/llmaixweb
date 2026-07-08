<template>
  <div class="flex flex-col h-full">
    <!-- Find-in-document bar -->
    <div
      v-if="!textLoading && hasText"
      class="flex items-center gap-2 px-3 py-2 border-b border-default bg-surface-muted"
    >
      <Search class="h-4 w-4 text-content-subtle flex-shrink-0" />
      <input
        ref="inputRef"
        v-model="query"
        type="search"
        placeholder="Find in document…"
        class="flex-1 min-w-0 bg-transparent border-0 text-sm text-content placeholder-content-subtle focus:outline-none"
        @input="onQueryInput"
        @keydown.enter.prevent="onEnter($event)"
        @keydown.escape.prevent="clearSearch"
      />
      <span v-if="query" class="text-xs text-content-muted tabular-nums whitespace-nowrap">
        {{ matchCount === 0 ? 'No results' : `${currentIndex + 1} / ${matchCount}` }}
      </span>
      <BaseButton
        v-if="query"
        variant="icon"
        size="sm"
        :disabled="matchCount === 0"
        title="Previous match (Shift+Enter)"
        aria-label="Previous match"
        @click="prevMatch"
      >
        <ChevronUp class="h-4 w-4" />
      </BaseButton>
      <BaseButton
        v-if="query"
        variant="icon"
        size="sm"
        :disabled="matchCount === 0"
        title="Next match (Enter)"
        aria-label="Next match"
        @click="nextMatch"
      >
        <ChevronDown class="h-4 w-4" />
      </BaseButton>
      <BaseButton
        v-if="query"
        variant="icon"
        size="sm"
        title="Clear search (Esc)"
        aria-label="Clear search"
        @click="clearSearch"
      >
        <X class="h-4 w-4" />
      </BaseButton>
    </div>

    <div class="p-6 overflow-y-auto flex-1 min-h-0">
      <div v-if="textLoading" class="flex items-center justify-center py-12 text-content-subtle">
        <span class="mr-2"><LoadingSpinner size="small" color="current" inline label="" /></span>
        <span>Loading text…</span>
      </div>
      <div
        v-else
        ref="contentRef"
        class="markdown-content max-w-3xl mx-auto bg-surface-muted p-4 rounded-card"
        v-html="safeMarkdown"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount, computed } from 'vue'
import { ChevronDown, ChevronUp, Search, X } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface Props {
  textLoading?: boolean
  safeMarkdown?: string
}

const props = withDefaults(defineProps<Props>(), {
  textLoading: false,
  safeMarkdown: '',
})

const contentRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const query = ref('')
const matches = ref<HTMLElement[]>([])
const currentIndex = ref(-1)

const hasText = computed(
  () => !!props.safeMarkdown && props.safeMarkdown !== '<em>No text content available</em>',
)
const matchCount = computed(() => matches.value.length)

const MARK_CLASS = 'doc-search-hit'
const MARK_CURRENT_CLASS = 'doc-search-hit-current'

/**
 * Highlight all matches of `query` within the rendered content by walking
 * text nodes (tag-safe: never matches inside tag names or attributes).
 * Returns the list of created <mark> elements in document order.
 */
function highlightMatches(rawQuery: string): HTMLElement[] {
  const root = contentRef.value
  if (!root) return []
  clearHighlights(root)

  const q = rawQuery.trim()
  if (!q) return []

  const lowerQ = q.toLowerCase()
  const found: HTMLElement[] = []
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => {
      // Skip <script>/<style> and our own <mark> highlights.
      const parent = node.parentElement
      if (!parent) return NodeFilter.FILTER_REJECT
      const tag = parent.tagName
      if (tag === 'SCRIPT' || tag === 'STYLE') return NodeFilter.FILTER_REJECT
      if (parent.classList?.contains(MARK_CLASS)) return NodeFilter.FILTER_REJECT
      return node.nodeValue && node.nodeValue.toLowerCase().includes(lowerQ)
        ? NodeFilter.FILTER_ACCEPT
        : NodeFilter.FILTER_REJECT
    },
  })

  const nodesToProcess: Text[] = []
  while (walker.nextNode()) {
    nodesToProcess.push(walker.currentNode as Text)
  }

  for (const textNode of nodesToProcess) {
    const text = textNode.nodeValue || ''
    const lower = text.toLowerCase()
    let i = 0
    let idx = lower.indexOf(lowerQ, i)
    const frag = document.createDocumentFragment()
    let any = false
    while (idx !== -1) {
      if (idx > i) frag.appendChild(document.createTextNode(text.slice(i, idx)))
      const mark = document.createElement('mark')
      mark.className = MARK_CLASS
      mark.textContent = text.slice(idx, idx + q.length)
      frag.appendChild(mark)
      found.push(mark)
      any = true
      i = idx + q.length
      idx = lower.indexOf(lowerQ, i)
    }
    if (any) {
      if (i < text.length) frag.appendChild(document.createTextNode(text.slice(i)))
      textNode.parentNode?.replaceChild(frag, textNode)
    }
  }

  return found
}

function clearHighlights(root: HTMLElement): void {
  const marks = root.querySelectorAll(`.${MARK_CLASS}`)
  marks.forEach((mark) => {
    const parent = mark.parentNode
    if (!parent) return
    // Replace the <mark> with its text, then merge adjacent text nodes so
    // re-searching doesn't fragment the DOM across runs.
    parent.replaceChild(document.createTextNode(mark.textContent || ''), mark)
    parent.normalize()
  })
}

function setCurrent(idx: number): void {
  // Clear previous "current" marker.
  matches.value.forEach((m) => m.classList.remove(MARK_CURRENT_CLASS))
  if (matches.value.length === 0) {
    currentIndex.value = -1
    return
  }
  const wrapped = ((idx % matches.value.length) + matches.value.length) % matches.value.length
  currentIndex.value = wrapped
  const el = matches.value[wrapped]
  if (el) {
    el.classList.add(MARK_CURRENT_CLASS)
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function runSearch(): void {
  const q = query.value.trim()
  if (!q) {
    matches.value = []
    currentIndex.value = -1
    if (contentRef.value) clearHighlights(contentRef.value)
    return
  }
  matches.value = highlightMatches(q)
  setCurrent(matches.value.length > 0 ? 0 : -1)
}

function nextMatch(): void {
  if (matches.value.length === 0) return
  setCurrent(currentIndex.value + 1)
}

function prevMatch(): void {
  if (matches.value.length === 0) return
  setCurrent(currentIndex.value - 1)
}

function onQueryInput(): void {
  // Re-run on every input change; cheap for typical document sizes.
  runSearch()
}

function onEnter(e: KeyboardEvent): void {
  if (matches.value.length === 0) return
  if (e.shiftKey) prevMatch()
  else nextMatch()
}

function clearSearch(): void {
  query.value = ''
  matches.value = []
  currentIndex.value = -1
  if (contentRef.value) clearHighlights(contentRef.value)
  inputRef.value?.focus()
}

// Re-run the search when the underlying content changes (e.g. document swap,
// version restore) so highlights stay in sync with what's on screen.
watch(
  () => props.safeMarkdown,
  () => {
    // Wait for the new v-html to paint before walking the DOM.
    nextTick(() => {
      if (query.value.trim()) runSearch()
    })
  },
)

onBeforeUnmount(() => {
  matches.value = []
})
</script>

<style scoped>
:deep(.doc-search-hit) {
  background-color: rgba(250, 204, 21, 0.4); /* yellow-300 @ 40% */
  color: inherit;
  border-radius: 2px;
  padding: 0 1px;
}
:deep(.doc-search-hit-current) {
  background-color: rgba(249, 115, 22, 0.7); /* orange-500 @ 70% */
  color: #fff;
}
:deep(.dark .doc-search-hit) {
  background-color: rgba(250, 204, 21, 0.3);
}
:deep(.dark .doc-search-hit-current) {
  background-color: rgba(249, 115, 22, 0.85);
  color: #fff;
}
</style>
