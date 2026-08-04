import { inject, computed, type ComputedRef } from 'vue'
import type { ProjectAccessLevel } from '@/types'

/**
 * The current user's access to the project being viewed.
 *
 * `ProjectDetail.vue` provides both keys; any descendant can read them without
 * threading a prop through every intermediate component. Outside a project view
 * (or before the project has loaded) this reports full access, so components
 * reused elsewhere — the landing-page demo, standalone modals — keep working.
 *
 * This shapes the UI only. Every project route is gated independently on the
 * backend (`core/security.can_access_project`), so hiding a button is a
 * courtesy, not the security boundary.
 */
export function useProjectAccess(): {
  canEdit: ComputedRef<boolean>
  accessLevel: ComputedRef<ProjectAccessLevel>
  isOwner: ComputedRef<boolean>
  isReadOnly: ComputedRef<boolean>
} {
  const injectedCanEdit = inject<ComputedRef<boolean> | undefined>('projectCanEdit', undefined)
  const injectedLevel = inject<ComputedRef<ProjectAccessLevel> | undefined>(
    'projectAccessLevel',
    undefined,
  )

  const canEdit = computed(() => injectedCanEdit?.value ?? true)
  const accessLevel = computed<ProjectAccessLevel>(() => injectedLevel?.value ?? 'owner')

  return {
    canEdit,
    accessLevel,
    isOwner: computed(() => accessLevel.value === 'owner'),
    isReadOnly: computed(() => !canEdit.value),
  }
}
