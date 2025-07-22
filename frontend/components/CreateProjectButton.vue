<!-- src/components/CreateProjectButton.vue -->
<template>
  <!-- Flat Modern Button -->
  <button
    @click="isModalOpen = true"
    class="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
  >
    <svg class="w-5 h-5 opacity-80" fill="none" viewBox="0 0 20 20" stroke="currentColor">
      <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5" />
      <path d="M10 6v8M6 10h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    <span>Create Project</span>
  </button>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="isModalOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-[1px] p-4"
        @click="closeModal"
      >
        <div
          class="bg-white rounded-xl border border-gray-200 shadow-sm w-full max-w-md p-6 flex flex-col gap-6"
          @click.stop
        >
          <h3 class="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-2">
            <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 20 20" stroke="currentColor">
              <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5" />
              <path d="M10 6v8M6 10h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            Create New Project
          </h3>
          <form @submit.prevent="createProject" class="flex flex-col gap-4">
            <div>
              <label for="projectName" class="block text-sm font-medium text-gray-700">Project Name</label>
              <input
                type="text"
                id="projectName"
                v-model="projectData.name"
                class="mt-1 block w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-gray-900 shadow-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
                required
                autocomplete="off"
                placeholder="e.g. MyApp Redesign"
              />
            </div>
            <div>
              <label for="projectDescription" class="block text-sm font-medium text-gray-700">Description <span class="text-gray-400 text-xs">(optional)</span></label>
              <textarea
                id="projectDescription"
                v-model="projectData.description"
                rows="3"
                class="mt-1 block w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-gray-900 shadow-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition resize-none"
                placeholder="Briefly describe your project"
              ></textarea>
            </div>
            <transition name="fade">
              <p v-if="error" class="text-sm text-red-600 mt-1">{{ error }}</p>
            </transition>
            <div class="flex justify-end gap-2 pt-2">
              <button
                type="button"
                class="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 transition"
                @click="closeModal"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="inline-flex items-center rounded-md px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
                :disabled="isLoading"
              >
                <svg v-if="isLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                {{ isLoading ? 'Creating...' : 'Create Project' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>
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

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.18s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
