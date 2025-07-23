<!-- DocumentGroups.vue -->
<template>
  <div class="space-y-6">
    <!-- Actions Bar -->
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-4">
        <button
          @click="showCreateModal = true"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Create Group
        </button>

        <div class="relative">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search groups..."
            class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <svg class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <span class="text-sm text-gray-500">View:</span>
        <button
          @click="viewMode = 'grid'"
          :class="[
            'p-2 rounded-lg',
            viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'
          ]"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
        </button>
        <button
          @click="viewMode = 'list'"
          :class="[
            'p-2 rounded-lg',
            viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'
          ]"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Document Groups Grid/List -->
    <div v-if="filteredGroups.length === 0" class="bg-gray-50 rounded-lg p-12 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No document groups</h3>
      <p class="mt-1 text-sm text-gray-500">Create your first group to organize documents</p>
    </div>

    <!-- Grid View -->
    <div v-else-if="viewMode === 'grid'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <DocumentGroupCard
        v-for="group in filteredGroups"
        :key="group.id"
        :group="group"
        @edit="editGroup"
        @delete="deleteGroup"
        @view="viewGroup"
      />
    </div>

    <!-- List View -->
    <div v-else class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Group Name
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Documents
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Configuration
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Tags
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Created
            </th>
            <th class="relative px-6 py-3">
              <span class="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="group in filteredGroups" :key="group.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
              <div>
                <div class="text-sm font-medium text-gray-900">{{ group.name }}</div>
                <div v-if="group.description" class="text-xs text-gray-500 truncate max-w-xs">
                  {{ group.description }}
                </div>
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="text-sm text-gray-900">{{ group.documents.length }}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span v-if="group.preprocessing_config" class="text-sm text-gray-900">
                {{ group.preprocessing_config.name }}
              </span>
              <span v-else class="text-sm text-gray-500">Mixed</span>
            </td>
            <td class="px-6 py-4">
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="tag in group.tags"
                  :key="tag"
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {{ tag }}
                </span>
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ formatDate(group.created_at) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <div class="flex items-center justify-end space-x-2">
                <button
                  @click="viewGroup(group)"
                  class="text-blue-600 hover:text-blue-900"
                  title="View"
                >
                  <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
                <button
                  @click="editGroup(group)"
                  class="text-gray-600 hover:text-gray-900"
                  title="Edit"
                >
                  <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  @click="deleteGroup(group)"
                  class="text-red-600 hover:text-red-900"
                  title="Delete"
                >
                  <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create/Edit Group Modal -->
    <CreateDocumentGroupModal
      v-if="showCreateModal || editingGroup"
      :group="editingGroup"
      :documents="documents"
      :project-id="projectId"
      @close="closeModal"
      @save="handleSaveGroup"
    />

    <!-- View Group Modal -->
    <ViewDocumentGroupModal
      v-if="viewingGroup"
      :group="viewingGroup"
      :project-id="projectId"
      @close="viewingGroup = null"
      @edit="editGroup"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import { formatDate } from '@/utils/formatters';
import DocumentGroupCard from './DocumentGroupCard.vue';
import CreateDocumentGroupModal from './CreateDocumentGroupModal.vue';
import ViewDocumentGroupModal from './ViewDocumentGroupModal.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  documents: {
    type: Array,
    required: true
  },
  documentSets: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(['refresh']);

const toast = useToast();

// State
const searchQuery = ref('');
const viewMode = ref('grid');
const showCreateModal = ref(false);
const editingGroup = ref(null);
const viewingGroup = ref(null);

// Computed
const filteredGroups = computed(() => {
  if (!searchQuery.value) {
    return props.documentSets;
  }

  const query = searchQuery.value.toLowerCase();
  return props.documentSets.filter(group =>
    group.name.toLowerCase().includes(query) ||
    group.description?.toLowerCase().includes(query) ||
    group.tags?.some(tag => tag.toLowerCase().includes(query))
  );
});

// Methods
const editGroup = (group) => {
  editingGroup.value = group;
  showCreateModal.value = false;
};

const viewGroup = (group) => {
  viewingGroup.value = group;
};

const deleteGroup = async (group) => {
  if (!confirm(`Are you sure you want to delete "${group.name}"? The documents will not be deleted.`)) {
    return;
  }

  try {
    await api.delete(`/project/${props.projectId}/document-set/${group.id}`);
    toast.success('Document group deleted successfully');
    emit('refresh');
  } catch (error) {
    toast.error('Failed to delete document group');
    console.error(error);
  }
};

const closeModal = () => {
  showCreateModal.value = false;
  editingGroup.value = null;
};

const handleSaveGroup = async (groupData) => {
  try {
    if (editingGroup.value) {
      await api.patch(`/project/${props.projectId}/document-set/${editingGroup.value.id}`, groupData);
      toast.success('Document group updated successfully');
    } else {
      await api.post(`/project/${props.projectId}/document-set`, groupData);
      toast.success('Document group created successfully');
    }
    closeModal();
    emit('refresh');
  } catch (error) {
    toast.error('Failed to save document group');
    console.error(error);
  }
};
</script>
