<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between">
          <!-- Project title and description -->
          <div v-if="!isEditing">
            <div class="flex items-center">
              <RouterLink to="/projects" class="text-blue-600 hover:text-blue-800 mr-2">
                <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
                </svg>
              </RouterLink>
              <h1 class="text-2xl font-bold text-gray-900">{{ project.name }}</h1>
              <button @click="isEditing = true" class="ml-2 text-gray-500 hover:text-gray-700">
                <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </button>
            </div>
            <p v-if="project.description" class="mt-1 text-sm text-gray-600">{{ project.description }}</p>
          </div>

          <!-- Edit mode -->
          <div v-else class="flex-1 mr-4">
            <input
              v-model="editedProject.name"
              class="block w-full text-2xl font-bold border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Project Name"
            />
            <textarea
              v-model="editedProject.description"
              class="mt-2 block w-full text-sm border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Project Description (optional)"
              rows="2"
            ></textarea>
            <div class="mt-2 flex space-x-2">
              <button
                @click="saveProjectEdits"
                class="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                :disabled="isSaving"
              >
                <svg v-if="isSaving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Save
              </button>
              <button
                @click="cancelEditing"
                class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>

          <!-- Status indicator and Delete button -->
          <div class="flex items-center space-x-3">
            <span class="px-3 py-1.5 text-xs font-semibold rounded-full bg-green-100 text-green-800">
              {{ project.status || 'Active' }}
            </span>
            <button
              @click="confirmDelete"
              class="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <!-- Project Workflow Tabs -->
      <div class="mb-6">
        <ProjectWorkflow
          :currentStep="currentStep"
          @change-step="currentStep = $event"
        />
      </div>

      <div v-if="isLoading" class="text-center py-12">
        <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        <p class="mt-2 text-gray-500">Loading project...</p>
      </div>

      <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <p class="text-sm text-red-700">{{ error }}</p>
          </div>
        </div>
      </div>

      <!-- Content based on current step -->
      <div v-else class="bg-white shadow rounded-lg overflow-hidden">
        <!-- Files Management -->
        <FilesManagement v-if="currentStep === 'files'" :projectId="projectId" @files-uploaded="refreshProject" />

        <!-- Preprocessing Management -->
        <PreprocessingManagement v-else-if="currentStep === 'preprocessing'" :projectId="projectId" :files="project.files || []" />

        <!-- Documents Management -->
        <DocumentsManagement v-else-if="currentStep === 'documents'" :projectId="projectId" />

        <!-- Trials Management -->
        <TrialsManagement v-else-if="currentStep === 'trials'" :projectId="projectId" />

        <!-- Schema Management -->
        <SchemaManagement v-else-if="currentStep === 'schemas'" :projectId="projectId" />

        <!-- Results View -->
        <EvaluationView v-else-if="currentStep === 'evaluation'" :projectId="projectId" />
      </div>
    </main>

    <!-- Confirmation Dialog for Delete Project -->
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
import { useToast } from 'vue-toastification';

const route = useRoute();
const router = useRouter();
const toast = useToast();
const projectId = computed(() => route.params.projectId);
const project = ref({});
const isLoading = ref(true);
const isEditing = ref(false);
const isSaving = ref(false);
const editedProject = ref({});
const error = ref('');
const showDeleteConfirmation = ref(false);

// Workflow step
const currentStep = ref('files');

// Provide project ID to child components
provide('projectId', projectId);

// Available LLM Models to provide to children
const availableModels = ref([
  'Llama-4-Maverick-17B-128E-Instruct-FP8',
  'GPT-4o',
  'Claude-3-Opus'
]);
provide('availableModels', availableModels);

// Fetch project details
const fetchProject = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${projectId.value}`);
    project.value = response.data;
    editedProject.value = {
      name: response.data.name,
      description: response.data.description
    };
  } catch (err) {
    error.value = 'Failed to load project details';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Save project edits
const saveProjectEdits = async () => {
  isSaving.value = true;
  try {
    const response = await api.put(`/project/${projectId.value}`, editedProject.value);
    project.value = response.data;
    isEditing.value = false;
    toast.success('Project updated successfully');
  } catch (err) {
    error.value = 'Failed to update project';
    toast.error('Failed to update project');
    console.error(err);
  } finally {
    isSaving.value = false;
  }
};

// Cancel editing
const cancelEditing = () => {
  editedProject.value = {
    name: project.value.name,
    description: project.value.description
  };
  isEditing.value = false;
};

// Show delete confirmation
const confirmDelete = () => {
  showDeleteConfirmation.value = true;
};

// Delete project
const deleteProject = async () => {
  try {
    await api.delete(`/project/${projectId.value}`);
    toast.success('Project deleted successfully');
    router.push('/projects');
  } catch (err) {
    toast.error('Failed to delete project');
    console.error(err);
  } finally {
    showDeleteConfirmation.value = false;
  }
};

// Refresh project data
const refreshProject = () => {
  fetchProject();
};

onMounted(() => {
  fetchProject();
});
</script>
