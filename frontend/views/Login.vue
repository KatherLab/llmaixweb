<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-gray-900 tracking-tight">LLMAIx-v2</h1>
      <p class="text-base text-gray-500 mt-2">Extract information from documents using LLMs.</p>
    </div>
    <form
      @submit.prevent="handleSubmit"
      class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm flex flex-col gap-5"
      autocomplete="on"
    >
      <div>
        <label for="email" class="block text-sm font-semibold text-gray-700 mb-2">Email address</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="e.g. your@email.com"
          autocomplete="email"
          spellcheck="false"
        />
      </div>
      <div>
        <label for="password" class="block text-sm font-semibold text-gray-700 mb-2">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Password"
          autocomplete="current-password"
        />
      </div>
      <button
        type="submit"
        class="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 disabled:opacity-70 disabled:cursor-not-allowed"
        :disabled="isLoading"
      >
        <svg v-if="isLoading" class="animate-spin h-5 w-5 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
        </svg>
        <svg v-else class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 20" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"/>
        </svg>
        <span>{{ isLoading ? 'Signing in...' : 'Sign in' }}</span>
      </button>
      <transition name="fade">
        <div
          v-if="error"
          class="mt-2 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md text-center"
        >
          {{ error }}
        </div>
      </transition>
      <router-link
        to="/register"
        class="block mt-3 text-center text-blue-600 hover:underline text-sm transition"
      >
        Don’t have an account? <span class="font-semibold">Register here</span>
      </router-link>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from "@/services/api.js";
import { useToast } from 'vue-toastification'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

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
    toast.error('Invalid email or password', {
      timeout: 3500,
      position: 'top-right',
      closeButton: true,
      hideProgressBar: false,
      icon: true,
      draggable: true,
    });
    console.error('Login error:', err);
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
