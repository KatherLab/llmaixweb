// vite.config.js
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const frontendDir = path.resolve(__dirname); // absolute path to frontend/
  const env = loadEnv(mode, frontendDir, '');
  const expectedEnvPath = path.join(frontendDir, `.env${mode !== 'development' ? `.${mode}` : ''}`);

  if (!env.VITE_API_BACKEND_URL) {
    throw new Error(
      `❌ Missing VITE_API_BACKEND_URL in environment variables.\n\n` +
      `Expected to find it in:\n  ${expectedEnvPath}\n\n` +
      `Make sure the file exists and contains a line like:\n  VITE_API_BACKEND_URL=https://your-api.url`
    );
  }

  return {
    plugins: [
      vue(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': frontendDir //path.join(frontendDir, 'src'), // Update the alias to point to the src directory
      },
    },
    root: frontendDir, // Update the root directory to the project root
    server: {
      port: 3000,
    },
  };
});