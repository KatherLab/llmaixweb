// vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const frontendDir = path.resolve(__dirname)
  const env = loadEnv(mode, frontendDir, '')

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
    },
  }
})
