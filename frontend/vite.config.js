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

  return {
    plugins: [vue(), tailwindcss()],
    // vue-i18n feature flags: strip legacy/devtools code and silence the
    // "runtime-only build" warnings. We alias to the full (esm-bundler) build
    // below so message strings can be compiled at runtime.
    define: {
      __VUE_I18N_FULL_INSTALL__: true,
      __VUE_I18N_LEGACY_API__: false,
      __INTLIFY_PROD_DEVTOOLS__: false,
    },
    resolve: {
      alias: {
        '@': frontendDir,
        'vue-i18n': 'vue-i18n/dist/vue-i18n.esm-bundler.js',
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
