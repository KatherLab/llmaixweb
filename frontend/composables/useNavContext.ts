/**
 * Contextual navbar center.
 *
 * Allows a routed page (e.g. ProjectDetail) to publish a compact set of
 * controls into the global navbar's center region — turning the single
 * sticky navbar into a contextual one (breadcrumb + workflow tabs) instead
 * of stacking a second sticky header below it.
 *
 * The page sets the context on mount and clears it on unmount; AppLayout
 * reactively renders either the published context or the default
 * Projects/Admin links.
 */
import { ref, type Ref } from 'vue'

export interface WorkflowStep {
  id: string
  name: string
  isComplete: boolean
}

export interface ProjectNavContext {
  /** Project name, shown as the trailing breadcrumb segment. */
  projectName: string
  /** Ordered workflow steps (drives the centered pill tabs + completion checks). */
  steps: WorkflowStep[]
  /** Currently active step id. */
  currentStep: string
  /** Switch to a step (page handles URL query update). */
  onStepChange: (stepId: string) => void
  /** Open project settings (gear shown in the navbar right cluster). */
  onOpenSettings: () => void
}

/** Module-level holder. null = no contextual nav → AppLayout shows default center links. */
export const navContext: Ref<ProjectNavContext | null> = ref<ProjectNavContext | null>(null)

/** Set the contextual nav (call from a page's onMounted). */
export function setNavContext(ctx: ProjectNavContext): void {
  navContext.value = ctx
}

/** Clear the contextual nav (call from a page's onUnmounted). */
export function clearNavContext(): void {
  navContext.value = null
}
