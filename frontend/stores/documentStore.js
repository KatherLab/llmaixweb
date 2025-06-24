import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useDocumentsStore = defineStore('documents', () => {
  const documents = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  // Get all documents for a project
  const fetchDocuments = async (projectId) => {
    if (!projectId) return;

    isLoading.value = true;
    error.value = null;

    try {
      // This endpoint doesn't exist in the OpenAPI spec
      // In a real implementation, you might need to create a custom endpoint
      const response = await axios.get(`/api/v1/project/${projectId}/documents`);
      documents.value = response.data;
    } catch (err) {
      console.error('Error fetching documents:', err);
      error.value = err.response?.data?.detail || err.message || 'Failed to load documents';
      documents.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  // Get a specific document
  const fetchDocument = async (projectId, documentId) => {
    if (!projectId || !documentId) return null;

    try {
      const response = await axios.get(`/api/v1/project/${projectId}/document/${documentId}`);
      return response.data;
    } catch (err) {
      console.error(`Error fetching document ${documentId}:`, err);
      throw err;
    }
  };

  // Get documents by preprocessing task
  const getDocumentsByTask = computed(() => {
    return (taskId) => {
      if (!taskId) return [];
      return documents.value.filter(doc => doc.preprocessing_task_id === taskId);
    };
  });

  return {
    documents,
    isLoading,
    error,
    fetchDocuments,
    fetchDocument,
    getDocumentsByTask
  };
});
