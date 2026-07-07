<!--
  Shared right-anchored slide-over drawer.

  Wraps BaseModal(placement="right") with the chrome every slide-over in the app
  repeats: a header (title + subtitle + optional actions slot), a full-height
  body, and an optional footer. Pass `total` (and index/hasPrev/hasNext) to get
  the built-in prev/next document nav control in the header; omit `total` for
  single-record slide-overs (e.g. file preview, preprocessing history).

  Slots:
    - default     : body content (body is `!p-0 flex-1 overflow-hidden` by
                    default so inner panes manage their own padding/scroll)
    - #header     : replaces the title/subtitle/actions row entirely
    - #actions    : extra header controls rendered left of the nav / close
    - #footer     : footer row

  Emits: close, prev, next.
-->
<template>
  <BaseModal
    :open="open"
    placement="right"
    :panel-class="`w-screen ${maxWidth}`"
    header-class="bg-surface-muted"
    :body-class="`!p-0 flex-1 overflow-hidden ${bodyClass}`"
    :footer-class="`bg-surface-muted ${footerClass}`"
    @close="emit('close')"
  >
    <template #header>
      <slot name="header">
        <div class="flex items-center justify-between gap-4 flex-1 min-w-0 pr-8">
          <div class="min-w-0">
            <h3 class="text-base font-semibold text-content truncate">{{ title }}</h3>
            <p v-if="subtitle" class="text-xs text-content-subtle mt-0.5 truncate">
              {{ subtitle }}
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <slot name="actions" />
            <template v-if="showNav">
              <BaseButton variant="secondary" size="sm" :disabled="!hasPrev" @click="emit('prev')">
                <ChevronLeft class="h-4 w-4" />
              </BaseButton>
              <span
                class="text-xs font-medium text-content-muted tabular-nums px-1 whitespace-nowrap"
              >
                {{ index + 1 }} / {{ total }}
              </span>
              <BaseButton variant="secondary" size="sm" :disabled="!hasNext" @click="emit('next')">
                <ChevronRight class="h-4 w-4" />
              </BaseButton>
            </template>
          </div>
        </div>
      </slot>
    </template>

    <slot />

    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'

interface Props {
  open: boolean
  title?: string
  subtitle?: string
  // Tailwind max-width class for the drawer panel. Defaults very wide so the
  // split (file | content) layout has room; narrow it (e.g. 'max-w-md') for
  // single-column slide-overs like preprocessing history.
  maxWidth?: string
  bodyClass?: string
  footerClass?: string
  // Document navigation. When `total` is provided, the header renders the
  // prev/next control + "x / y" indicator. Omit for single-record slide-overs.
  index?: number
  total?: number
  hasPrev?: boolean
  hasNext?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  subtitle: '',
  maxWidth: 'max-w-[95rem]',
  bodyClass: '',
  footerClass: '',
  index: 0,
  total: undefined,
  hasPrev: false,
  hasNext: false,
})

const emit = defineEmits<{ close: []; prev: []; next: [] }>()

const showNav = computed(() => props.total !== undefined)
</script>
