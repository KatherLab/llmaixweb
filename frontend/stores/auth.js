api.js// src/stores/auth.js

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token'))
  const isInitialized = ref(false)

  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function initialize() {
    console.log("Auth store initializing");

    if (isInitialized.value) {
      console.log("Already initialized");
      return true;
    }

    if (token.value) {
      console.log("Token found:", token.value);
      console.log("Token expiration:", JSON.parse(atob(token.value.split('.')[1])).exp);
      console.log("Fetching user data...");
      try {
        await fetchUser();
        console.log("User fetched successfully:", user.value);
      } catch (error) {
        console.log("Error fetching user:", error);
        await logout();
        return false;
      }
    } else {
      console.log("No token found");
    }

    isInitialized.value = true;
    console.log("Auth store initialization completed");
    return true;
  }
  async function setToken(newToken) {
    token.value = newToken;
    console.log("Setting token");
    localStorage.setItem('token', newToken);
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
  }

  async function fetchUser() {
    console.log("Starting fetchUser with Axios");
    try {
      console.log("Attempting to fetch user data...");
      const token = localStorage.getItem('token');
      if (!token) {
        console.error("No token found");
        await logout();
        return false;
      }

      // The 'api' instance is already configured with the baseURL and 'Content-Type' header
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      const response = await api.get('/user/me', {
        // Axios automatically includes cookies if withCredentials is set to true
        // You might need to configure this in the 'api' instance creation
        // withCredentials: true,
      });

      console.log("Response received with status:", response.status);
      user.value = response.data;
      console.log("User data retrieved and state updated:", user.value);
      return true;
    } catch (error) {
      console.error("Fetch failed:", error);
      if (error.response) {
        // The request was made and the server responded with a status code
        console.error("Error response status:", error.response.status);
        console.error("Error response data:", error.response.data);
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error("Error message:", error.message);
      }
      // Handle the error, perhaps log out the user
      await logout();
      return false;
    }
  }

  async function logout() {
    console.log("Starting logout")
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    isInitialized.value = false
    console.log("Logout completed")
  }

  return {
    user,
    token,
    isAuthenticated,
    isAdmin,
    setToken,
    fetchUser,
    logout,
    initialize
  }
})