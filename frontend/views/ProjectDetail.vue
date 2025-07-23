<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-100 via-white to-blue-100">
    <!-- Glassy App Bar -->
    <header class="sticky top-0 z-30 bg-white/70 shadow-lg backdrop-blur-lg transition-all">
      <div class="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row items-center justify-between space-y-3 sm:space-y-0">
        <div class="flex items-center">
          <RouterLink to="/projects" class="text-blue-500 hover:text-blue-700 mr-4 rounded-lg transition-all">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24"><path d="M15 19l-7-7 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </RouterLink>
          <div>
            <div class="flex items-center space-x-2">
              <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 drop-shadow-sm">{{ project.name }}</h1>
              <button @click="showEditModal = true" class="p-1 rounded-full hover:bg-blue-100 transition" aria-label="Edit Project">
                <svg class="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 20 20"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" fill="currentColor"/></svg>
              </button>
            </div>
            <div v-if="project.description" class="text-gray-600 mt-1">{{ project.description }}</div>
          </div>
        </div>
        <div class="flex items-center space-x-3">
          <span class="px-4 py-1.5 text-xs font-bold rounded-full bg-green-50 text-green-700 border border-green-200 shadow-sm">{{ project.status || 'Active' }}</span>
          <button @click="showDeleteConfirmation = true"
                  class="px-4 py-2 rounded-xl bg-red-600 text-white font-semibold hover:bg-red-700 transition shadow">
            Delete
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-4">
      <!-- Modern Workflow Tabs -->
      <div class="mb-4">
        <ProjectWorkflow
          :currentStep="currentStep"
          :openTabs="openTabs"
          @change-step="handleStepChange"
          @update-open-tabs="updateOpenTabs"
        />
      </div>

      <!-- Loading, Error, Main Content -->
      <div v-if="isLoading" class="flex flex-col items-center py-24">
        <div class="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-500"></div>
        <span class="mt-4 text-gray-400 text-lg">Loading project...</span>
      </div>

      <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 mb-4 rounded-xl">
        <div class="flex">
          <svg class="h-6 w-6 text-red-400 mr-2" fill="none" viewBox="0 0 24 24">
            <path d="M12 9v2m0 4h.01M21 12A9 9 0 113 12a9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <div class="text-red-700">{{ error }}</div>
        </div>
      </div>

      <!-- Workspace with glassmorphism -->
      <div v-else class="relative bg-white/70 rounded-3xl shadow-2xl p-6 sm:p-8 mb-20 transition-all"
           style="backdrop-filter: blur(12px);">
        <transition name="fade" mode="out-in">
          <!-- Show each tab as content, but only if it's currentStep -->
          <FilesManagement
            v-if="currentStep === 'files'"
            :projectId="projectId"
            @files-uploaded="refreshProject"
            key="files"
          />
          <PreprocessingManagement
            v-else-if="currentStep === 'preprocessing'"
            :projectId="projectId"
            :files="project.files || []"
            key="preprocessing"
          />
          <DocumentsManagement
            v-else-if="currentStep === 'documents'"
            :projectId="projectId"
            key="documents"
          />
          <SchemaManagement
            v-else-if="currentStep === 'schemas'"
            :projectId="projectId"
            key="schemas"
          />
          <TrialsManagement
            v-else-if="currentStep === 'trials'"
            :projectId="projectId"
            key="trials"
          />
          <EvaluationView
            v-else-if="currentStep === 'evaluation'"
            :projectId="projectId"
            key="evaluation"
          />
        </transition>
      </div>
    </main>

    <!-- Edit Modal -->
    <ProjectEditModal
      v-if="showEditModal"
      :open="showEditModal"
      :initialName="project.name"
      :initialDescription="project.description"
      :isSaving="isSaving"
      @save="saveProjectEdits"
      @close="showEditModal = false"
    />

    <!-- Delete Confirmation Modal -->
    <ConfirmationDialog
      v-if="showDeleteConfirmation"
      :open="showDeleteConfirmation"
      title="Delete Project"
      message="Are you sure you want to delete this project? This action cannot be undone and all associated files and data will be lost."
      confirmText="Delete Project"
      confirmVariant="danger"
      @confirm="deleteProject"
      @cancel="showDeleteConfirmation = false"
    />

    <!-- Mobile: Workspace Tab Bar (at bottom) -->
    <div
      v-if="openTabs.length > 1"
      class="fixed bottom-0 left-0 right-0 z-40 sm:hidden flex bg-white/80 backdrop-blur-lg border-t border-gray-200 rounded-t-2xl px-2 py-2 shadow-2xl"
    >
      <div class="flex-1 flex justify-between">
        <button
          v-for="tab in openTabs"
          :key="tab"
          class="flex flex-col items-center px-1"
          :class="currentStep === tab ? 'text-blue-600 font-bold' : 'text-gray-400'"
          @click="handleStepChange(tab)"
        >
          <span class="text-xs">{{ stepsMap[tab]?.name.split(' ')[0] }}</span>
          <span v-if="openTabs.length > 1" @click.stop="closeTab(tab)" class="text-[10px] text-gray-300">×</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, provide } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '@/services/api';
import ProjectWorkflow from '@/components/ProjectWorkflow.vue';
import FilesManagement from '@/components/FilesManagement.vue';
import PreprocessingManagement from '@/components/PreprocessingManagement.vue';
import DocumentsManagement from '@/components/documents/DocumentsManagement.vue';
import TrialsManagement from '@/components/TrialsManagement.vue';
import SchemaManagement from '@/components/SchemaManagement.vue';
import EvaluationView from '@/components/EvaluationView.vue';
import ConfirmationDialog from '@/components/ConfirmationDialog.vue';
import ProjectEditModal from '@/components/ProjectEditModal.vue';
import { useToast } from 'vue-toastification';

// --- DATA ---
const route = useRoute();
const router = useRouter();
const toast = useToast();

const projectId = computed(() => route.params.projectId);
const project = ref({});
const isLoading = ref(true);
const error = ref('');
const isSaving = ref(false);
const showEditModal = ref(false);
const showDeleteConfirmation = ref(false);

// Workflow step management with tab workspace
const steps = [
  { id: 'files', name: 'Upload Files' },
  { id: 'preprocessing', name: 'Preprocess Files' },
  { id: 'documents', name: 'Documents' },
  { id: 'schemas', name: 'Schemas & Prompts' },
  { id: 'trials', name: 'Run Trials' },
  { id: 'evaluation', name: 'Evaluation' }
];
const stepsMap = Object.fromEntries(steps.map(s => [s.id, s]));
const defaultStep = 'files';

// Tabs (persisted in localStorage for true SaaS "workspace" vibes)
const currentStep = ref(defaultStep);
const openTabs = ref([defaultStep]);
const openTabsStorageKey = `project-${projectId.value}-open-tabs`;
const currentStepStorageKey = `project-${projectId.value}-current-step`;

function persistWorkspace() {
  localStorage.setItem(openTabsStorageKey, JSON.stringify(openTabs.value));
  localStorage.setItem(currentStepStorageKey, currentStep.value);
}
function restoreWorkspace() {
  try {
    const open = JSON.parse(localStorage.getItem(openTabsStorageKey));
    const curr = localStorage.getItem(currentStepStorageKey);
    if (Array.isArray(open) && open.length) openTabs.value = open;
    if (curr && openTabs.value.includes(curr)) currentStep.value = curr;
  } catch {}
}

// --- LIFECYCLE ---
onMounted(() => {
  fetchProject();
  restoreWorkspace();
});

// --- API ---
const fetchProject = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${projectId.value}`);
    project.value = response.data;
  } catch (err) {
    error.value = 'Failed to load project details';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};
const refreshProject = () => fetchProject();

// --- WORKFLOW & TAB LOGIC ---
function handleStepChange(stepId) {
  if (!openTabs.value.includes(stepId)) openTabs.value.push(stepId);
  currentStep.value = stepId;
  persistWorkspace();
}
function updateOpenTabs(tabs) {
  openTabs.value = tabs;
  if (!openTabs.value.includes(currentStep.value)) {
    currentStep.value = openTabs.value[0] || defaultStep;
  }
  persistWorkspace();
}
function closeTab(tabId) {
  if (openTabs.value.length <= 1) return;
  const idx = openTabs.value.indexOf(tabId);
  openTabs.value.splice(idx, 1);
  if (currentStep.value === tabId) {
    currentStep.value = openTabs.value[idx - 1] || openTabs.value[0];
  }
  persistWorkspace();
}

// --- PROJECT EDIT LOGIC ---
const saveProjectEdits = async ({ name, description }) => {
  isSaving.value = true;
  try {
    const response = await api.put(`/project/${projectId.value}`, { name, description });
    project.value = response.data;
    toast.success('Project updated successfully');
    showEditModal.value = false;
  } catch (err) {
    error.value = 'Failed to update project';
    toast.error('Failed to update project');
  } finally {
    isSaving.value = false;
  }
};

// --- DELETE LOGIC ---
const deleteProject = async () => {
  try {
    await api.delete(`/project/${projectId.value}`);
    toast.success('Project deleted successfully');
    router.push('/projects');
  } catch (err) {
    toast.error('Failed to delete project');
  } finally {
    showDeleteConfirmation.value = false;
  }
};

// --- PROVIDE CONTEXT ---
provide('projectId', projectId);
provide('availableModels', ref([
  'Llama-4-Maverick-17B-128E-Instruct-FP8',
  'GPT-4o',
  'Claude-3-Opus'
]));
</script>

<style scoped>
/* Modern motion for transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
