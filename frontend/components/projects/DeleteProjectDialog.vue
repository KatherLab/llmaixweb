<!-- src/components/projects/DeleteProjectDialog.vue -->
<!--
  Type-the-project-name delete confirmation. Deleting a project destroys all
  of its files, documents, trials and evaluations, so a generic yes/no confirm
  is not enough friction — the user must type the exact project name, and the
  dialog summarizes what will be destroyed (from the aggregate counts already
  present on the Project payload).
-->
<template>
  <BaseModal :open="open" size="md" @close="onClose">
    <template #header>
      <h3 class="text-lg font-semibold text-content">Delete Project</h3>
    </template>

    <div class="space-y-4">
      <Callout variant="danger" title="This action cannot be undone">
        <p class="mt-1 text-sm">
          Deleting <strong>{{ projectName }}</strong> permanently removes the project and everything
          in it{{ impactItems.length > 0 ? ', including:' : '.' }}
        </p>
        <ul v-if="impactItems.length > 0" class="mt-2 text-sm list-disc list-inside space-y-0.5">
          <li v-for="item in impactItems" :key="item">{{ item }}</li>
        </ul>
      </Callout>

      <div>
        <label :class="labelClass" for="delete-project-confirm-input">
          Type <span class="font-semibold select-all">{{ projectName }}</span> to confirm
        </label>
        <input
          id="delete-project-confirm-input"
          v-model="confirmText"
          type="text"
          :class="inputClass"
          autocomplete="off"
          spellcheck="false"
          :placeholder="projectName"
          @keydown.enter="canConfirm && !deleting ? $emit('confirm') : undefined"
        />
      </div>
    </div>

    <template #footer>
      <BaseButton variant="secondary" :disabled="deleting" @click="onClose"> Cancel </BaseButton>
      <BaseButton
        variant="danger"
        :disabled="!canConfirm || deleting"
        :loading="deleting"
        @click="$emit('confirm')"
      >
        Delete Project
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { inputClass, labelClass } from '@/utils/formStyles'
import type { Project } from '@/types'

interface Props {
  open: boolean
  project: Project
  deleting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  deleting: false,
})

const emit = defineEmits<{
  confirm: []
  close: []
}>()

const confirmText = ref('')

const projectName = computed(() => props.project.name || 'this project')

// Fresh input on every open — a previously typed name must not stay armed.
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) confirmText.value = ''
  },
)

const canConfirm = computed(
  () => !!props.project.name && confirmText.value.trim() === props.project.name,
)

// Impact summary from the aggregate counts on the Project payload (cheap —
// already fetched for the workflow progression cues). Only non-zero entries.
const impactItems = computed<string[]>(() => {
  const p = props.project
  const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`
  const items: string[] = []
  if ((p.document_count ?? 0) > 0) items.push(plural(p.document_count, 'document'))
  if ((p.schema_count ?? 0) > 0) items.push(plural(p.schema_count, 'schema'))
  if ((p.prompt_count ?? 0) > 0) items.push(plural(p.prompt_count, 'prompt'))
  if ((p.trial_count ?? 0) > 0) items.push(plural(p.trial_count, 'trial'))
  if ((p.evaluation_count ?? 0) > 0) items.push(plural(p.evaluation_count, 'evaluation'))
  return items
})

const onClose = (): void => {
  if (props.deleting) return
  confirmText.value = ''
  emit('close')
}
</script>
