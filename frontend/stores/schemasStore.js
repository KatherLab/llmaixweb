import { defineStore } from 'pinia';
import { ref } from 'vue';
import axios from 'axios';

export const useSchemasStore = defineStore('schemas', () => {
  const schemas = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  // Get all schemas for a project
  const fetchSchemas = async (projectId) => {
    if (!projectId) return;

    isLoading.value = true;
    error.value = null;

    try {
      // This endpoint doesn't exist in the OpenAPI spec
      // In a real implementation, you might need to create a custom endpoint
      const response = await axios.get(`/api/v1/project/${projectId}/schemas`);
      schemas.value = response.data;
    } catch (err) {
      console.error('Error fetching schemas:', err);
      error.value = err.response?.data?.detail || err.message || 'Failed to load schemas';
      schemas.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  // Get a specific schema
  const fetchSchema = async (projectId, schemaId) => {
    if (!projectId || !schemaId) return null;

    try {
      const response = await axios.get(`/api/v1/project/${projectId}/schema/${schemaId}`);
      return response.data;
    } catch (err) {
      console.error(`Error fetching schema ${schemaId}:`, err);
      throw err;
    }
  };

  // Create a new schema
  const createSchema = async (projectId, schemaData) => {
    if (!projectId) throw new Error('Project ID is required');

    try {
      const response = await axios.post(`/api/v1/project/${projectId}/schema`, schemaData);
      schemas.value.push(response.data);
      return response.data;
    } catch (err) {
      console.error('Error creating schema:', err);
      throw err;
    }
  };

  // Delete a schema
  const deleteSchema = async (projectId, schemaId) => {
    if (!projectId || !schemaId) throw new Error('Project ID and Schema ID are required');

    try {
      await axios.delete(`/api/v1/project/${projectId}/schema/${schemaId}`);
      schemas.value = schemas.value.filter(schema => schema.id !== schemaId);
      return true;
    } catch (err) {
      console.error('Error deleting schema:', err);
      throw err;
    }
  };

  return {
    schemas,
    isLoading,
    error,
    fetchSchemas,
    fetchSchema,
    createSchema,
    deleteSchema
  };
});
