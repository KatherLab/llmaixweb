<!-- src/components/CreateProjectButton.vue -->
<template>
  <!-- Compact button matching Invite User style -->
  <BaseButton size="sm" data-testid="create-project-open" @click="isModalOpen = true">{{
    $t('projects.create.open')
  }}</BaseButton>

  <BaseModal
    :open="isModalOpen"
    :closeable="false"
    size="sm"
    body-class="p-6 flex flex-col gap-6"
    @close="closeModal"
  >
    <h3 class="text-lg font-semibold text-content flex items-center gap-2 mb-2">
      <CirclePlus class="w-5 h-5 text-primary" />
      {{ $t('projects.create.title') }}
    </h3>
    <form class="flex flex-col gap-4" @submit.prevent="createProject">
      <div>
        <label for="projectName" :class="labelClass">{{ $t('projects.create.name_label') }}</label>
        <input
          id="projectName"
          v-model="projectData.name"
          type="text"
          :class="inputClass"
          required
          autocomplete="off"
          maxlength="100"
          :placeholder="$t('projects.create.name_placeholder')"
        />
      </div>
      <div>
        <label for="projectDescription" :class="labelClass"
          >{{ $t('projects.create.description_label') }}
          <span class="text-content-subtle text-xs">{{
            $t('projects.create.optional')
          }}</span></label
        >
        <textarea
          id="projectDescription"
          v-model="projectData.description"
          rows="3"
          :class="textareaClass"
          maxlength="500"
          :placeholder="$t('projects.create.description_placeholder')"
        ></textarea>
      </div>
      <transition name="fade">
        <p v-if="error" class="text-sm text-red-600 dark:text-red-400 mt-1">{{ error }}</p>
      </transition>
      <div class="flex justify-end gap-2 pt-2">
        <BaseButton variant="secondary" @click="closeModal">
          {{ $t('projects.actions.cancel') }}
        </BaseButton>
        <BaseButton
          type="submit"
          :loading="isLoading"
          :disabled="isLoading"
          data-testid="create-project-submit"
        >
          {{ isLoading ? $t('projects.create.creating') : $t('projects.create.submit') }}
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { CirclePlus } from '@lucide/vue'
import { projectsApi } from '@/services/projectsApi'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, textareaClass, labelClass } from '@/utils/formStyles'

const router = useRouter()
const { t } = useI18n({ useScope: 'global' })
const isModalOpen = ref(false)
const isLoading = ref(false)
const error = ref('')
const projectData = ref<{ name: string; description: string }>({
  name: '',
  description: '',
})

const createProject = async (): Promise<void> => {
  isLoading.value = true
  error.value = ''
  try {
    const response = await projectsApi.create(projectData.value)
    isModalOpen.value = false
    router.push(`/projects/${response.data.id}`)
  } catch (err) {
    error.value = extractErrorMessage(err, t('projects.create.error'))
  } finally {
    isLoading.value = false
  }
}

const closeModal = (): void => {
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
