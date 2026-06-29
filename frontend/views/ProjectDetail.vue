<template>
  <div
    class="min-h-screen bg-gradient-to-br from-slate-100 via-white to-blue-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800"
  >
    <!-- Ultra-Compact Single-Row Header -->
    <header
      class="sticky top-0 z-30 bg-white/70 dark:bg-slate-900/70 shadow-md backdrop-blur-lg border-b border-slate-200/50 dark:border-slate-800/50 transition-all"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6">
        <div class="flex items-center justify-between h-12">
          <!-- Left: Back + Project Name -->
          <div class="flex items-center gap-2.5 min-w-0 flex-shrink-0">
            <RouterLink
              to="/projects"
              class="flex-shrink-0 text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
              aria-label="Back to projects"
            >
              <ChevronLeft class="w-5 h-5" />
            </RouterLink>
            <h1
              class="text-lg font-semibold text-slate-900 dark:text-white truncate max-w-[180px] sm:max-w-[220px] md:max-w-[300px]"
            >
              {{ project.name }}
            </h1>
          </div>

          <!-- Center: Tab navigation (absolute centered) -->
          <nav class="flex items-center gap-1 overflow-x-auto absolute left-1/2 -translate-x-1/2">
            <button
              v-for="step in steps"
              :key="step.id"
              class="px-3 py-1.5 text-sm font-medium whitespace-nowrap rounded-md transition-all"
              :class="[
                currentStep === step.id
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200',
              ]"
              @click="handleStepChange(step.id)"
            >
              {{ step.name }}
            </button>
          </nav>

          <!-- Right: Settings button -->
          <button
            class="flex-shrink-0 p-2 text-slate-600 hover:text-slate-800 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800 rounded-lg transition-all"
            aria-label="Project Settings"
            @click="showSettingsModal = true"
          >
            <Settings class="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-4">
      <!-- Loading, Error, Main Content -->
      <div v-if="isLoading" class="flex flex-col items-center py-24">
        <LoadingSpinner size="large" />
        <span class="mt-4 text-slate-400 dark:text-slate-500 text-lg">Loading project...</span>
      </div>

      <ErrorBanner v-else-if="error" :message="error" class="mb-4 rounded-xl" />

      <!-- Workspace with glassmorphism -->
      <GlassCard v-else padding="lg" rounded="3xl" :blur="12" class="mb-20">
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
      :initial-name="project.name"
      :initial-description="project.description"
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

<script setup>
import { ref, computed, onMounted, provide, watch } from 'vue'
import { ChevronLeft, Settings } from '@lucide/vue'
import { useRoute, useRouter } from 'vue-router'
import { projectsApi } from '@/services/projectsApi'
import FilesAndProcessing from '@/components/files/FilesAndProcessing.vue'
import DocumentsManagement from '@/components/documents/DocumentsManagement.vue'
import TrialsManagement from '@/components/trials/TrialsManagement.vue'
import SchemaManagement from '@/components/schemas/SchemaManagement.vue'
import EvaluationView from '@/components/evaluation/EvaluationView.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import ProjectSettingsModal from '@/components/projects/ProjectSettingsModal.vue'
import { useToast } from 'vue-toastification'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import GlassCard from '@/components/common/GlassCard.vue'

// --- DATA ---
const route = useRoute()
const router = useRouter()
const toast = useToast()

const projectId = computed(() => route.params.projectId)
const project = ref({})
const isLoading = ref(true)
const error = ref('')
const isSaving = ref(false)
const showSettingsModal = ref(false)
const showDeleteConfirmation = ref(false)

// Workflow step management with tab workspace
const validSteps = ['files', 'documents', 'schemas', 'trials', 'evaluation']
const steps = [
  { id: 'files', name: 'Files & Preprocessing' },
  { id: 'documents', name: 'Documents' },
  { id: 'schemas', name: 'Schemas & Prompts' },
  { id: 'trials', name: 'Run Trials' },
  { id: 'evaluation', name: 'Evaluation' },
]
const defaultStep = 'files'

// Tabs (persisted in localStorage for true SaaS "workspace" vibes)
// Current step is managed via URL query param
const currentStep = computed(() => {
  const tab = route.query.tab
  return validSteps.includes(tab) ? tab : defaultStep
})

// --- LIFECYCLE ---
onMounted(() => {
  fetchProject()
  handleQueryParams()
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
function handleQueryParams() {
  const queryTab = route.query.tab
  const expandTask = route.query.expandTask
  const expandTrial = route.query.expandTrial

  // Handle tab switch from query
  if (queryTab && validSteps.includes(queryTab)) {
    handleStepChange(queryTab)
  }

  // Pass expand parameters to child components via custom events
  // Need to wait for tab change to render the component first
  if (expandTask) {
    // Ensure we're on the files tab
    if (currentStep.value !== 'files') {
      handleStepChange('files')
    }
    // Wait for component to render and then dispatch event
    setTimeout(() => {
      document.dispatchEvent(
        new CustomEvent('expand-preprocessing-task', { detail: { id: expandTask } }),
      )
      // Clean up query params after handling
      router.replace({ query: { ...route.query, expandTask: undefined } })
    }, 300)
  }

  if (expandTrial) {
    // Ensure we're on the trials tab
    if (currentStep.value !== 'trials') {
      handleStepChange('trials')
    }
    // Wait for component to render and then dispatch event
    setTimeout(() => {
      document.dispatchEvent(new CustomEvent('expand-trial', { detail: { id: expandTrial } }))
      // Clean up query params after handling
      router.replace({ query: { ...route.query, expandTrial: undefined } })
    }, 300)
  }
}

// --- API ---
const fetchProject = async () => {
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
const refreshProject = () => fetchProject()

// --- WORKFLOW & TAB LOGIC ---
function handleStepChange(stepId) {
  if (!validSteps.includes(stepId)) return // Ignore invalid steps
  currentStep.value = stepId
  // Update URL without adding history entry
  router.replace({ query: { ...route.query, tab: stepId } })
}

// --- PROJECT EDIT LOGIC ---
const saveProjectEdits = async ({ name, description }) => {
  isSaving.value = true
  try {
    const response = await projectsApi.update(projectId.value, { name, description })
    project.value = response.data
    toast.success('Project updated successfully')
    showSettingsModal.value = false
  } catch {
    error.value = 'Failed to update project'
    toast.error('Failed to update project')
  } finally {
    isSaving.value = false
  }
}

// --- DELETE LOGIC ---
const deleteProject = async () => {
  try {
    await projectsApi.delete(projectId.value)
    toast.success('Project deleted successfully')
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
