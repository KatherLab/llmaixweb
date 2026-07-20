import { onMounted, onUnmounted, type Ref } from 'vue'
import type { SchemaDefinition } from '@/types'

/**
 * Keyboard shortcut handling for the visual schema editor.
 *
 * - N (plain key, no modifiers): open the "add property" modal — only when the
 *   current schema is an object (i.e. properties can be added), focus is not in
 *   an editable field, and no editor modal is already open.
 *
 * Notes:
 * - Ctrl/Cmd+N is reserved by browsers (new window) and cannot be intercepted,
 *   so a plain key is used instead.
 * - Escape is deliberately NOT handled here: BaseModal owns Escape handling,
 *   and modals like EditPropertyModal opt out of Escape-to-close on purpose
 *   (confirm-discard flow). A window-level Escape handler would bypass that.
 *
 * @param opts
 * @param opts.showAddPropertyModal
 * @param opts.showEditPropertyModal
 * @param opts.showDeleteModal
 * @param opts.showHelp
 * @param opts.currentSchema
 */
interface UseSchemaKeyboardOptions {
  showAddPropertyModal: Ref<boolean>
  showEditPropertyModal: Ref<boolean>
  showDeleteModal: Ref<boolean>
  showHelp: Ref<boolean>
  currentSchema: Ref<SchemaDefinition>
}

export function useSchemaKeyboard({
  showAddPropertyModal,
  showEditPropertyModal,
  showDeleteModal,
  showHelp,
  currentSchema,
}: UseSchemaKeyboardOptions): void {
  const handleKeyboard = (e: KeyboardEvent): void => {
    // Plain "N" for new property (no modifiers — Ctrl/Cmd+N is browser-reserved)
    if (e.key !== 'n' && e.key !== 'N') return
    if (e.ctrlKey || e.metaKey || e.altKey) return

    // Ignore while typing in an editable field
    const target = e.target as HTMLElement | null
    const tag = target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable) {
      return
    }

    // Ignore while any editor modal is open (the shortcut only applies to the canvas)
    if (
      showAddPropertyModal.value ||
      showEditPropertyModal.value ||
      showDeleteModal.value ||
      showHelp.value
    ) {
      return
    }

    if (currentSchema.value.type !== 'object') return

    e.preventDefault()
    showAddPropertyModal.value = true
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeyboard)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyboard)
  })
}
