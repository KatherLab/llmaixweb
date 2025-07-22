import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import Toast from 'vue-toastification';
import 'vue-toastification/dist/index.css';

const app = createApp(App);
app.use(createPinia());
app.use(router);
ModuleRegistry.registerModules([AllCommunityModule]);
app.mount('#app');
app.use(Toast);

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled Promise Rejection:', event.reason);
});