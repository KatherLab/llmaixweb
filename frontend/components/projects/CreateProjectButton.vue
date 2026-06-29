<!-- src/components/CreateProjectButton.vue -->
<template>
  <!-- Compact button matching Invite User style -->
  <button
    class="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-lg shadow transition"
    @click="isModalOpen = true"
  >
    + Create Project
  </button>

  <BaseModal
    :open="isModalOpen"
    :closeable="false"
    size="sm"
    panel-class="dark:bg-slate-900 dark:border-slate-700 rounded-xl shadow-sm"
    body-class="p-6 flex flex-col gap-6"
    @close="closeModal"
  >
    <h3 class="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
      <CirclePlus class="w-5 h-5 text-blue-600 dark:text-blue-400" />
      Create New Project
    </h3>
    <form class="flex flex-col gap-4" @submit.prevent="createProject">
      <div>
        <label
          for="projectName"
          class="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >Project Name</label
        >
        <input
          id="projectName"
          v-model="projectData.name"
          type="text"
          class="mt-1 block w-full rounded-md border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white shadow-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          required
          autocomplete="off"
          placeholder="e.g. Medical Document IE"
        />
      </div>
      <div>
        <label
          for="projectDescription"
          class="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >Description
          <span class="text-slate-400 dark:text-slate-500 text-xs">(optional)</span></label
        >
        <textarea
          id="projectDescription"
          v-model="projectData.description"
          rows="3"
          class="mt-1 block w-full rounded-md border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white shadow-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition resize-none"
          placeholder="Briefly describe your project"
        ></textarea>
      </div>
      <transition name="fade">
        <p v-if="error" class="text-sm text-red-600 dark:text-red-400 mt-1">{{ error }}</p>
      </transition>
      <div class="flex justify-end gap-2 pt-2">
        <BaseButton variant="secondary" @click="closeModal"> Cancel </BaseButton>
        <BaseButton type="submit" :loading="isLoading" :disabled="isLoading">
          {{ isLoading ? 'Creating...' : 'Create Project' }}
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { CirclePlus } from '@lucide/vue'
import { projectsApi } from '@/services/projectsApi'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { extractErrorMessage } from '@/utils/errors'

const router = useRouter()
const isModalOpen = ref(false)
const isLoading = ref(false)
const error = ref('')
const projectData = ref({
  name: '',
  description: '',
})

const createProject = async () => {
  isLoading.value = true
  error.value = ''
  try {
    const response = await projectsApi.create(projectData.value)
    isModalOpen.value = false
    router.push(`/projects/${response.data.id}`)
  } catch (err) {
    error.value = extractErrorMessage(err, 'Failed to create project')
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
