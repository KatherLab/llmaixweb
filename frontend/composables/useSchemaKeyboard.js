import { onMounted, onUnmounted } from 'vue'

/**
 * Keyboard shortcut handling for the visual schema editor.
 *
 * - Ctrl/Cmd + N: open the "add property" modal (only when the current schema
 *   is an object, i.e. properties can be added).
 * - Escape: close all editor modals.
 *
 * Extracted verbatim from VisualSchemaEditor.vue — no behavior changes.
 *
 * @param {object} opts
 * @param {import('vue').Ref<boolean>} opts.showAddPropertyModal
 * @param {import('vue').Ref<boolean>} opts.showEditPropertyModal
 * @param {import('vue').Ref<boolean>} opts.showDeleteModal
 * @param {import('vue').Ref<boolean>} opts.showHelp
 * @param {import('vue').Ref<object>} opts.currentSchema
 */
export function useSchemaKeyboard({
  showAddPropertyModal,
  showEditPropertyModal,
  showDeleteModal,
  showHelp,
  currentSchema,
}) {
  const handleKeyboard = (e) => {
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
