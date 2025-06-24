<!-- src/views/Login.vue -->
<template>
  <div class="max-w-lg mx-auto px-4 py-10">
    <h1 class="text-4xl font-bold text-gray-900 text-center mb-1">LLMAIx-v2</h1>
    <p class="text-lg text-gray-600 text-center mb-10">Extract information from Documents using LLMs.</p>

    <form @submit.prevent="handleSubmit" class="bg-white rounded-lg shadow-md p-8">
      <div class="mb-6">
        <label for="email" class="block text-sm font-medium text-gray-700 mb-2">Email address</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Email address"
        />
      </div>

      <div class="mb-6">
        <label for="password" class="block text-sm font-medium text-gray-700 mb-2">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Password"
        />
      </div>

      <button
        type="submit"
        class="w-full flex items-center justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-gray-700 bg-gray-100 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-70 disabled:cursor-not-allowed"
        :disabled="isLoading"
      >
        <svg v-if="!isLoading" class="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
        </svg>
        {{ isLoading ? 'Signing in...' : 'Sign in' }}
      </button>

      <div v-if="error" class="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-md text-center">
        {{ error }}
      </div>

      <router-link to="/register" class="block mt-6 text-center text-blue-600 hover:underline text-sm">
        Don't have an account? Register here
      </router-link>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from "@/services/api.js";

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref(null)

async function handleSubmit() {
  if (isLoading.value) return;
  isLoading.value = true;
  error.value = null;

  try {
    const formData = new URLSearchParams();
    formData.append('username', email.value);
    formData.append('password', password.value);

    const response = await api.post('/auth/login', formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    await authStore.setToken(response.data.access_token);
    await authStore.fetchUser();
    router.push(authStore.isAdmin ? '/' : '/');
  } catch (err) {
    error.value = 'Invalid email or password';
    console.error('Login error:', err);
  } finally {
    isLoading.value = false;
  }
}
</script>