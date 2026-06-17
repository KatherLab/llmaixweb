<template>
  <div
    class="min-h-screen bg-gradient-to-br from-gray-100 via-white to-blue-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800"
  >
    <!-- Ultra-Compact Single-Row Header -->
    <header
      class="sticky top-0 z-30 bg-white/70 dark:bg-slate-900/70 shadow-md backdrop-blur-lg border-b border-gray-200/50 dark:border-slate-800/50 transition-all"
    >
      <div class="max-w-7xl mx-auto px-4 sm:px-6">
        <div class="flex items-center justify-between h-12">
          <!-- Left: Back + Project Name -->
          <div class="flex items-center gap-2.5 min-w-0 flex-shrink-0">
            <RouterLink
              to="/projects"
              class="flex-shrink-0 text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              aria-label="Back to projects"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </RouterLink>
            <h1
              class="text-lg font-semibold text-gray-900 dark:text-white truncate max-w-[180px] sm:max-w-[220px] md:max-w-[300px]"
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
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-slate-800 dark:hover:text-gray-200',
              ]"
              @click="handleStepChange(step.id)"
            >
              {{ step.name }}
            </button>
          </nav>

          <!-- Right: Settings button -->
          <button
            class="flex-shrink-0 p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-slate-800 rounded-lg transition-all"
            aria-label="Project Settings"
            @click="showSettingsModal = true"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-4">
      <!-- Loading, Error, Main Content -->
      <div v-if="isLoading" class="flex flex-col items-center py-24">
        <div class="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-500"></div>
        <span class="mt-4 text-gray-400 dark:text-gray-500 text-lg">Loading project...</span>
      </div>

      <div
        v-else-if="error"
        class="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 dark:border-red-400 p-4 mb-4 rounded-xl"
      >
        <div class="flex">
          <svg class="h-6 w-6 text-red-400 dark:text-red-300 mr-2" fill="none" viewBox="0 0 24 24">
            <path
              d="M12 9v2m0 4h.01M21 12A9 9 0 113 12a9 9 0 0118 0z"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <div class="text-red-700 dark:text-red-300">{{ error }}</div>
        </div>
      </div>

      <!-- Workspace with glassmorphism -->
      <div
        v-else
        class="relative bg-white/70 dark:bg-slate-900/70 rounded-3xl shadow-2xl p-6 sm:p-8 mb-20 transition-all"
        style="backdrop-filter: blur(12px)"
      >
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
      </div>
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
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import FilesAndProcessing from '@/components/FilesAndProcessing.vue'
import DocumentsManagement from '@/components/documents/DocumentsManagement.vue'
import TrialsManagement from '@/components/TrialsManagement.vue'
import SchemaManagement from '@/components/SchemaManagement.vue'
import EvaluationView from '@/components/EvaluationView.vue'
import ConfirmationDialog from '@/components/ConfirmationDialog.vue'
import ProjectSettingsModal from '@/components/ProjectSettingsModal.vue'
import { useToast } from 'vue-toastification'

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
    const response = await api.get(`/project/${projectId.value}`)
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
    const response = await api.put(`/project/${projectId.value}`, { name, description })
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
    await api.delete(`/project/${projectId.value}`)
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
