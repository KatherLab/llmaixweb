// src/services/api.js

import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add request interceptor
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add simplified response interceptor
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API request failed:', error);
    // Simply reject with the error, no retries
    return Promise.reject(error);
  }
);