import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useTrialsStore = defineStore('trials', () => {
  const trials = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  // Get all trials for a project
  const fetchTrials = async (projectId) => {
    if (!projectId) return;

    isLoading.value = true;
    error.value = null;

    try {
      // In a real implementation, you would fetch from an API endpoint
      // Since the API doesn't have a dedicated endpoint for all trials in a project,
      // this could be implemented as a custom endpoint
      const response = await axios.get(`/api/v1/project/${projectId}/trials`);
      trials.value = response.data;
    } catch (err) {
      console.error('Error fetching trials:', err);
      error.value = err.response?.data?.detail || err.message || 'Failed to load trials';
      trials.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  // Get a specific trial
  const fetchTrial = async (projectId, trialId) => {
    if (!projectId || !trialId) return null;

    try {
      const response = await axios.get(`/api/v1/project/${projectId}/trials/${trialId}`);

      // Update the trial in the trials array
      const index = trials.value.findIndex(t => t.id === trialId);
      if (index !== -1) {
        trials.value[index] = response.data;
      } else {
        trials.value.push(response.data);
      }

      return response.data;
    } catch (err) {
      console.error(`Error fetching trial ${trialId}:`, err);
      throw err;
    }
  };

  // Create a new trial
  const createTrial = async (projectId, trialData) => {
    if (!projectId) throw new Error('Project ID is required');

    try {
      const response = await axios.post(`/api/v1/project/${projectId}/trials`, trialData);
      trials.value.unshift(response.data); // Add to beginning of array
      return response.data;
    } catch (err) {
      console.error('Error creating trial:', err);
      throw err;
    }
  };

  // Delete a trial
  const deleteTrial = async (projectId, trialId) => {
    if (!projectId || !trialId) throw new Error('Project ID and Trial ID are required');

    try {
      // Mock implementation since the API doesn't have a delete trial endpoint
      // In a real implementation, you would use axios.delete
      // await axios.delete(`/api/v1/project/${projectId}/trials/${trialId}`);

      // Remove from local state
      trials.value = trials.value.filter(trial => trial.id !== trialId);
      return true;
    } catch (err) {
      console.error('Error deleting trial:', err);
      throw err;
    }
  };

  // Get a trial by ID
  const getTrialById = computed(() => {
    return (trialId) => trials.value.find(trial => trial.id === trialId);
  });

  return {
    trials,
    isLoading,
    error,
    fetchTrials,
    fetchTrial,
    createTrial,
    deleteTrial,
    getTrialById
  };
});
