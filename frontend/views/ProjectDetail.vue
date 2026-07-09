<template>
  <div class="min-h-screen bg-surface-muted">
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-4">
      <!-- Loading, Error, Main Content -->
      <div v-if="isLoading" class="flex flex-col items-center py-24">
        <LoadingSpinner size="large" />
        <span class="mt-4 text-content-subtle text-lg">Loading project...</span>
      </div>

      <ErrorBanner v-else-if="error" :message="error" class="mb-4 rounded-modal" />

      <!-- Workspace with glassmorphism -->
      <GlassCard v-else padding="lg" rounded="modal" class="mb-20">
        <!-- Per-step prerequisite hint: shown when the current tab's inputs
             aren't ready yet, with a deep-link to the prior step. -->
        <Callout
          v-if="prerequisiteHint"
          variant="info"
          :title="prerequisiteHint.title"
          class="mb-4"
        >
          <p class="mt-1">{{ prerequisiteHint.body }}</p>
          <BaseButton
            variant="link"
            tone="blue"
            class="mt-2 p-0 h-auto"
            @click="goToStep(prerequisiteHint.targetStep)"
          >
            Go to {{ prerequisiteHint.targetLabel }} →
          </BaseButton>
        </Callout>
        <transition name="fade" mode="out-in">
          <!-- Show each tab as content, but only if it's currentStep -->
          <FilesAndProcessing
            v-if="currentStep === 'files'"
            key="files"
            :project-id="projectId"
            @files-changed="refreshProject"
          />
          <DocumentsManagement
            v-else-if="currentStep === 'documents'"
            key="documents"
            :project-id="projectId"
          />
          <SchemaManagement
            v-else-if="currentStep === 'schemas'"
            key="schemas"
            :project-id="projectId"
          />
          <TrialsManagement
            v-else-if="currentStep === 'trials'"
            key="trials"
            :project-id="projectId"
          />
          <EvaluationView
            v-else-if="currentStep === 'evaluation'"
            key="evaluation"
            :project-id="projectId"
          />
        </transition>
      </GlassCard>
    </main>

    <!-- Settings Modal -->
    <ProjectSettingsModal
      v-if="showSettingsModal"
      :open="showSettingsModal"
      :initial-name="project.name || undefined"
      :initial-description="project.description || undefined"
      :is-saving="isSaving"
      @save="saveProjectEdits"
      @close="showSettingsModal = false"
      @delete="showDeleteConfirmation = true"
    />

    <!-- Delete Confirmation Modal -->
    <ConfirmationDialog
      v-if="showDeleteConfirmation"
      :open="showDeleteConfirmation"
      title="Delete Project"
      message="Are you sure you want to delete this project? This action cannot be undone and all associated files and data will be lost."
      confirm-text="Delete Project"
      confirm-variant="danger"
      @confirm="deleteProject"
      @cancel="showDeleteConfirmation = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, provide, watch, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { projectsApi } from '@/services/projectsApi'
import type { Project, ProjectUpdate } from '@/types'
import { setNavContext, clearNavContext } from '@/composables/useNavContext'
// Tab components are lazy-loaded so each workflow step is code-split into its
// own chunk (only one tab is rendered at a time, see the v-if chain below).
const FilesAndProcessing = defineAsyncComponent(
  () => import('@/components/files/FilesAndProcessing.vue'),
)
const DocumentsManagement = defineAsyncComponent(
  () => import('@/components/documents/DocumentsManagement.vue'),
)
const TrialsManagement = defineAsyncComponent(
  () => import('@/components/trials/TrialsManagement.vue'),
)
const SchemaManagement = defineAsyncComponent(
  () => import('@/components/schemas/SchemaManagement.vue'),
)
const EvaluationView = defineAsyncComponent(
  () => import('@/components/evaluation/EvaluationView.vue'),
)
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import ProjectSettingsModal from '@/components/projects/ProjectSettingsModal.vue'
import { useToast } from '@/composables/useToast'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import GlassCard from '@/components/common/GlassCard.vue'
import Callout from '@/components/common/Callout.vue'
import BaseButton from '@/components/common/BaseButton.vue'

// --- DATA ---
const route = useRoute()
const router = useRouter()
const toast = useToast()

const projectId = computed<string | number>(() => route.params.projectId as string | number)
const project = ref<Project>({} as Project)
const isLoading = ref<boolean>(true)
const error = ref<string>('')
const isSaving = ref<boolean>(false)
const showSettingsModal = ref<boolean>(false)
const showDeleteConfirmation = ref<boolean>(false)

// Workflow step management with tab workspace
const validSteps = ['files', 'documents', 'schemas', 'trials', 'evaluation']
// `isComplete` drives the step-number → check-mark progression cue. Each step
// is marked done when its corresponding aggregate count on the Project payload
// is non-zero. Navigation stays free (no hard gating).
const steps = computed(() => [
  {
    id: 'files',
    name: 'Files & Preprocessing',
    isComplete: (project.value.document_count ?? 0) > 0,
  },
  { id: 'documents', name: 'Documents', isComplete: (project.value.document_count ?? 0) > 0 },
  {
    id: 'schemas',
    name: 'Schemas & Prompts',
    isComplete: (project.value.schema_count ?? 0) > 0 && (project.value.prompt_count ?? 0) > 0,
  },
  { id: 'trials', name: 'Run Trials', isComplete: (project.value.trial_count ?? 0) > 0 },
  {
    id: 'evaluation',
    name: 'Evaluation',
    isComplete: (project.value.evaluation_count ?? 0) > 0,
  },
])
const defaultStep = 'files'

// Per-step prerequisite guidance. Returns null when the current step's inputs
// are ready (so no hint shows). Drives the Callout above the workspace.
const stepLabels: Record<string, string> = {
  files: 'Files & Preprocessing',
  documents: 'Documents',
  schemas: 'Schemas & Prompts',
  trials: 'Run Trials',
  evaluation: 'Evaluation',
}
const prerequisiteHint = computed<{
  title: string
  body: string
  targetStep: string
  targetLabel: string
} | null>(() => {
  const p = project.value
  const docCount = p.document_count ?? 0
  const schemaCount = p.schema_count ?? 0
  const promptCount = p.prompt_count ?? 0
  const trialCount = p.trial_count ?? 0
  switch (currentStep.value) {
    case 'documents':
      if (docCount === 0)
        return {
          title: 'No documents yet',
          body: 'Preprocess your uploaded files to generate documents. Documents are the extracted text the LLM reads during a trial.',
          targetStep: 'files',
          targetLabel: stepLabels.files,
        }
      return null
    case 'schemas':
      return null // schemas/prompts can be authored at any time
    case 'trials':
      if (docCount === 0)
        return {
          title: 'No documents to run a trial on',
          body: 'A trial extracts structured data from your documents. Preprocess files first to generate documents.',
          targetStep: 'files',
          targetLabel: stepLabels.files,
        }
      if (schemaCount === 0 || promptCount === 0)
        return {
          title: schemaCount === 0 ? 'No schema yet' : 'No prompt yet',
          body: 'A trial needs a schema (the fields to extract) and a prompt (extraction instructions). Create both before running a trial.',
          targetStep: 'schemas',
          targetLabel: stepLabels.schemas,
        }
      return null
    case 'evaluation':
      if (trialCount === 0)
        return {
          title: 'No trials to evaluate',
          body: 'Evaluation compares trial results against ground-truth data. Run a trial first to produce results to evaluate.',
          targetStep: 'trials',
          targetLabel: stepLabels.trials,
        }
      return null
    default:
      return null
  }
})

function goToStep(stepId: string): void {
  handleStepChange(stepId)
}

// Tabs (persisted in localStorage for true SaaS "workspace" vibes)
// Current step is managed via URL query param
const currentStep = computed<string>(() => {
  const tab = route.query.tab
  return typeof tab === 'string' && validSteps.includes(tab) ? tab : defaultStep
})

// --- LIFECYCLE ---
onMounted(() => {
  fetchProject()
  handleQueryParams()
})

// Publish the project context into the global navbar (breadcrumb + centered
// workflow tabs + settings gear), replacing the default Projects/Admin links.
// Re-published whenever the project name, steps, or active step change.
watch(
  [() => project.value.name, steps, currentStep],
  () => {
    setNavContext({
      projectName: project.value.name || 'Project',
      steps: steps.value,
      currentStep: currentStep.value,
      onStepChange: handleStepChange,
      onOpenSettings: () => {
        showSettingsModal.value = true
      },
    })
  },
  { immediate: true },
)

onUnmounted(() => {
  clearNavContext()
})

// Watch for route query changes (e.g., from ActivityBell navigation)
watch(
  () => route.query,
  (newQuery) => {
    if (newQuery.expandTrial || newQuery.expandTask || newQuery.tab) {
      handleQueryParams()
    }
  },
)

// Handle query parameters for tab and expand parameters
function handleQueryParams(): void {
  const queryTab = route.query.tab
  const expandTask = route.query.expandTask
  const expandTrial = route.query.expandTrial

  // Handle tab switch from query
  if (queryTab && typeof queryTab === 'string' && validSteps.includes(queryTab)) {
    handleStepChange(queryTab)
  }

  // Pass expand parameters to child components via custom events
  // Need to wait for tab change to render the component first
  if (expandTask) {
    const taskId = String(expandTask)
    // Ensure we're on the files tab
    if (currentStep.value !== 'files') {
      handleStepChange('files')
    }
    // Wait for component to render and then dispatch event
    setTimeout(() => {
      document.dispatchEvent(
        new CustomEvent('expand-preprocessing-task', { detail: { id: taskId } }),
      )
      // Clean up query params after handling
      const { expandTask: _omit, ...rest } = route.query
      void _omit
      router.replace({ query: { ...rest, expandTask: undefined } })
    }, 300)
  }

  if (expandTrial) {
    const trialId = String(expandTrial)
    // Ensure we're on the trials tab
    if (currentStep.value !== 'trials') {
      handleStepChange('trials')
    }
    // Wait for component to render and then dispatch event
    setTimeout(() => {
      document.dispatchEvent(new CustomEvent('expand-trial', { detail: { id: trialId } }))
      // Clean up query params after handling
      const { expandTrial: _omit, ...rest } = route.query
      void _omit
      router.replace({ query: { ...rest, expandTrial: undefined } })
    }, 300)
  }
}

// --- API ---
const fetchProject = async (): Promise<void> => {
  isLoading.value = true
  try {
    const response = await projectsApi.get(projectId.value)
    project.value = response.data
  } catch (err) {
    error.value = 'Failed to load project details'
    console.error(err)
  } finally {
    isLoading.value = false
  }
}
const refreshProject = (): Promise<void> => fetchProject()

// --- WORKFLOW & TAB LOGIC ---
function handleStepChange(stepId: string): void {
  if (!validSteps.includes(stepId)) return // Ignore invalid steps
  // currentStep is a computed (read-only); update via the URL query param.
  router.replace({ query: { ...route.query, tab: stepId } })
  // Refresh aggregate counts so per-step check marks reflect changes made
  // in other tabs (schema/prompt/trial/evaluation create/delete) since the
  // last fetch. Fire-and-forget — only FilesAndProcessing emits a dedicated
  // refresh event, so this keeps the other steps' progression cues current.
  void refreshProject()
}

// --- PROJECT EDIT LOGIC ---
const saveProjectEdits = async (payload: ProjectUpdate): Promise<void> => {
  isSaving.value = true
  try {
    const response = await projectsApi.update(projectId.value, payload)
    project.value = response.data
    toast.success('Project updated')
    showSettingsModal.value = false
  } catch {
    error.value = 'Failed to update project'
    toast.error('Failed to update project')
  } finally {
    isSaving.value = false
  }
}

// --- DELETE LOGIC ---
const deleteProject = async (): Promise<void> => {
  try {
    await projectsApi.delete(projectId.value)
    toast.success('Project deleted')
    router.push('/projects')
  } catch {
    toast.error('Failed to delete project')
  } finally {
    showDeleteConfirmation.value = false
  }
}

// --- PROVIDE CONTEXT ---
provide('projectId', projectId)
provide(
  'availableModels',
  ref(['Llama-4-Maverick-17B-128E-Instruct-FP8', 'GPT-4o', 'Claude-3-Opus']),
)
</script>

<style scoped>
/* Modern motion for transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
