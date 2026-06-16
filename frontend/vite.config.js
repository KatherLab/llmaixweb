// vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const frontendDir = path.resolve(__dirname)
  const env = loadEnv(mode, frontendDir, '')

  // Backend URL - can be overridden via env var VITE_BACKEND_URL
  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8000'
  const backendHost = backendUrl.replace('https://', '').replace('http://', '')

  return {
    plugins: [vue(), tailwindcss()],
    resolve: {
      alias: {
        '@': frontendDir,
      },
    },
    root: frontendDir,
    server: {
      port: 3000,
      proxy: {
        // Proxy API requests to backend
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
        // Proxy WebSocket requests to backend
        '/ws': {
          target: backendUrl,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
