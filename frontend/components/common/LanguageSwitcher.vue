<template>
  <div ref="container" class="relative">
    <button
      ref="triggerButton"
      type="button"
      :aria-label="t('nav.select_language')"
      :aria-expanded="open"
      aria-haspopup="true"
      class="p-2 rounded-full hover:bg-surface-sunken transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
      @click="open = !open"
    >
      <Languages class="w-5 h-5 text-content-muted" />
    </button>
    <transition name="fade-slide">
      <div
        v-if="open"
        class="absolute right-0 mt-3 w-44 rounded-modal shadow-xl bg-surface ring-1 ring-default-border z-50 py-1"
        role="menu"
      >
        <button
          v-for="loc in supportedLocales"
          :key="loc"
          type="button"
          role="menuitemradio"
          :aria-checked="loc === locale"
          class="flex items-center justify-between w-full px-4 py-2 text-sm font-medium text-content-muted hover:bg-primary-soft hover:text-primary transition-colors"
          :class="{ 'text-primary': loc === locale }"
          @click="select(loc)"
        >
          {{ t(`language.${loc}`) }}
          <Check v-if="loc === locale" class="w-4 h-4" />
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Languages, Check } from '@lucide/vue'
import { useLocale } from '@/composables/useLocale'
import { useClickOutside } from '@/composables/useClickOutside'
import type { SupportedLocale } from '@/i18n'

const { t } = useI18n({ useScope: 'global' })
const { locale, supportedLocales, setLocale } = useLocale()

const open = ref(false)
const container = ref<HTMLElement | null>(null)

useClickOutside(container, () => {
  open.value = false
})

async function select(loc: SupportedLocale): Promise<void> {
  await setLocale(loc)
  open.value = false
}
</script>
