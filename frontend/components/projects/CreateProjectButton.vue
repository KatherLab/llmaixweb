<!-- src/components/CreateProjectButton.vue -->
<template>
  <!-- Compact button matching Invite User style -->
  <button
    class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-lg shadow transition"
    @click="isModalOpen = true"
  >
    + Create Project
  </button>

  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="isModalOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 dark:bg-black/60 backdrop-blur-[1px] p-4"
        @click="closeModal"
      >
        <div
          class="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm w-full max-w-md p-6 flex flex-col gap-6 overflow-y-auto max-h-[90vh]"
          @click.stop
        >
          <h3
            class="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-2"
          >
            <svg
              class="w-5 h-5 text-blue-600 dark:text-blue-400"
              fill="none"
              viewBox="0 0 20 20"
              stroke="currentColor"
            >
              <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5" />
              <path
                d="M10 6v8M6 10h8"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
              />
            </svg>
            Create New Project
          </h3>
          <form class="flex flex-col gap-4" @submit.prevent="createProject">
            <div>
              <label
                for="projectName"
                class="block text-sm font-medium text-gray-700 dark:text-slate-300"
                >Project Name</label
              >
              <input
                id="projectName"
                v-model="projectData.name"
                type="text"
                class="mt-1 block w-full rounded-md border border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 text-gray-900 dark:text-white shadow-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
                required
                autocomplete="off"
                placeholder="e.g. Medical Document IE"
              />
            </div>
            <div>
              <label
                for="projectDescription"
                class="block text-sm font-medium text-gray-700 dark:text-slate-300"
                >Description
                <span class="text-gray-400 dark:text-slate-500 text-xs">(optional)</span></label
              >
              <textarea
                id="projectDescription"
                v-model="projectData.description"
                rows="3"
                class="mt-1 block w-full rounded-md border border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 text-gray-900 dark:text-white shadow-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition resize-none"
                placeholder="Briefly describe your project"
              ></textarea>
            </div>
            <transition name="fade">
              <p v-if="error" class="text-sm text-red-600 dark:text-red-400 mt-1">{{ error }}</p>
            </transition>
            <div class="flex justify-end gap-2 pt-2">
              <button
                type="button"
                class="rounded-md px-4 py-2 text-sm text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 transition"
                @click="closeModal"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="inline-flex items-center rounded-md px-4 py-2 text-sm font-medium bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 disabled:opacity-50"
                :disabled="isLoading"
              >
                <svg
                  v-if="isLoading"
                  class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
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
import { ref, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { projectsApi } from '@/services/projectsApi'

const router = useRouter()
const isModalOpen = ref(false)
const isLoading = ref(false)
const error = ref('')
const projectData = ref({
  name: '',
  description: '',
})

// Disable background scrolling when modal is open
const stop = watch(isModalOpen, (open) => {
  document.body.classList.toggle('overflow-hidden', open)
})
onUnmounted(() => {
  document.body.classList.remove('overflow-hidden')
  stop()
})

const createProject = async () => {
  isLoading.value = true
  error.value = ''
  try {
    const response = await projectsApi.create(projectData.value)
    isModalOpen.value = false
    router.push(`/projects/${response.data.id}`)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to create project'
  } finally {
    isLoading.value = false
  }
}

const closeModal = () => {
  if (!isLoading.value) {
    isModalOpen.value = false
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
