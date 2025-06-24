<!-- src/components/CreateProjectButton.vue -->
<template>
  <button
    @click="isModalOpen = true"
    class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md flex items-center"
  >
    <svg class="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clip-rule="evenodd" />
    </svg>
    Create Project
  </button>
  <Teleport to="body">
    <div
      v-if="isModalOpen"
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="closeModal"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6" @click.stop>
        <form @submit.prevent="createProject">
          <h3 class="text-lg font-medium leading-6 text-gray-900">Create New Project</h3>
          <div class="mt-4 space-y-4">
            <div>
              <label for="projectName" class="block text-sm font-medium text-gray-700">Project Name</label>
              <input
                type="text"
                id="projectName"
                v-model="projectData.name"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label for="projectDescription" class="block text-sm font-medium text-gray-700">Description (optional)</label>
              <textarea
                id="projectDescription"
                v-model="projectData.description"
                rows="3"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              ></textarea>
            </div>
            <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
          </div>
          <div class="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              class="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              @click="closeModal"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="inline-flex justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              :disabled="isLoading"
            >
              <svg v-if="isLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ isLoading ? 'Creating...' : 'Create Project' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { api } from '@/services/api';

const router = useRouter();
const isModalOpen = ref(false);
const isLoading = ref(false);
const error = ref('');
const projectData = ref({
  name: '',
  description: ''
});

const createProject = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    const response = await api.post('/project', projectData.value);
    isModalOpen.value = false;
    // Navigate to the project detail page
    router.push(`/projects/${response.data.id}`);
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to create project';
  } finally {
    isLoading.value = false;
  }
};

const closeModal = () => {
  if (!isLoading.value) {
    isModalOpen.value = false;
  }
};
</script>