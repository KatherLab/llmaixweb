import { onMounted, onUnmounted, type Ref } from 'vue'
import type { SchemaDefinition } from '@/types'

/**
 * Keyboard shortcut handling for the visual schema editor.
 *
 * - Ctrl/Cmd + N: open the "add property" modal (only when the current schema
 *   is an object, i.e. properties can be added).
 * - Escape: close all editor modals.
 *
 * Extracted verbatim from VisualSchemaEditor.vue — no behavior changes.
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
    // Ctrl/Cmd + N for new property
    if ((e.ctrlKey || e.metaKey) && e.key === 'n' && currentSchema.value.type === 'object') {
      e.preventDefault()
      showAddPropertyModal.value = true
    }
    // Escape to close modals
    if (e.key === 'Escape') {
      showAddPropertyModal.value = false
      showEditPropertyModal.value = false
      showDeleteModal.value = false
      showHelp.value = false
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeyboard)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyboard)
  })
}
