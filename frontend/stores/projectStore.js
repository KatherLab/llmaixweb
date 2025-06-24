import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/services/api'

export const useProjectStore = defineStore('project', () => {
  const projects = ref([]);
  const currentProject = ref(null);
  const isLoading = ref(false);
  const error = ref(null);

  // Get all projects
  const fetchProjects = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.get('/project');
      projects.value = response.data;
    } catch (err) {
      console.error('Error fetching projects:', err);
      error.value = err.response?.data?.detail || err.message || 'Failed to load projects';
      projects.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  // Get a specific project
  const fetchProject = async (projectId) => {
    if (!projectId) return;

    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.get(`/project/${projectId}`);
      currentProject.value = response.data;
    } catch (err) {
      console.error(`Error fetching project ${projectId}:`, err);
      error.value = err.response?.data?.detail || err.message || 'Failed to load project';
      currentProject.value = null;
    } finally {
      isLoading.value = false;
    }
  };

  // Create a new project
  const createProject = async (projectData) => {
    try {
      const response = await api.post('/project/', projectData);
      projects.value.push(response.data);
      return response.data;
    } catch (err) {
      console.error('Error creating project:', err);
      throw err;
    }
  };

  // Update a project
  const updateProject = async (projectId, projectData) => {
    if (!projectId) throw new Error('Project ID is required');

    try {
      const response = await api.put(`/project/${projectId}`, projectData);

      // Update in projects list if present
      const index = projects.value.findIndex(p => p.id === projectId);
      if (index !== -1) {
        projects.value[index] = response.data;
      }

      // Update current project if it's the same
      if (currentProject.value && currentProject.value.id === projectId) {
        currentProject.value = response.data;
      }

      return response.data;
    } catch (err) {
      console.error('Error updating project:', err);
      throw err;
    }
  };

  // Delete a project
  const deleteProject = async (projectId) => {
    if (!projectId) throw new Error('Project ID is required');

    try {
      await api.delete(`/project/${projectId}`);
      projects.value = projects.value.filter(project => project.id !== projectId);

      if (currentProject.value && currentProject.value.id === projectId) {
        currentProject.value = null;
      }

      return true;
    } catch (err) {
      console.error('Error deleting project:', err);
      throw err;
    }
  };

  return {
    projects,
    currentProject,
    isLoading,
    error,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject
  };
});
