// vite.config.js
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const frontendDir = path.resolve(__dirname); // absolute path to frontend/
  const env = loadEnv(mode, frontendDir, '');

  return {
    plugins: [
      vue(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': frontendDir,
      },
    },
    root: frontendDir,
    server: {
      port: 3000,
    },
    // Define placeholder for runtime substitution
    // VITE_API_BACKEND_URL is now injected at runtime via config.js
    define: {
      'import.meta.env.VITE_API_BACKEND_URL': env.VITE_API_BACKEND_URL || '__VITE_API_BACKEND_URL__',
    },
  };
});