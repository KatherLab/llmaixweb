import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { themeBalham } from 'ag-grid-community';

const app = createApp(App)
app.use(createPinia())
app.use(router)
ModuleRegistry.registerModules([AllCommunityModule]);
app.mount('#app')

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled Promise Rejection:', event.reason);
});