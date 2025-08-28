<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="$emit('close')"
      style="backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); background: rgba(30,30,40,0.27);"
    >
      <div
        class="relative bg-white rounded-2xl shadow-2xl w-full max-w-3xl flex flex-col max-h-[90vh] border border-gray-200"
        tabindex="0"
        ref="modalRef"
        @keydown.esc="$emit('close')"
      >
        <div class="px-8 py-5 bg-gradient-to-r from-blue-50 to-blue-100 border-b rounded-t-2xl flex items-center justify-between">
          <h2 class="text-2xl font-bold text-blue-900 tracking-tight">Preprocessing Configurations</h2>
          <button
            @click="$emit('close')"
            class="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-8 pb-8 pt-4">
          <div class="mb-10">
            <div class="flex items-center gap-3 mb-3">
              <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-600 font-bold">1</span>
              <span class="text-lg font-semibold text-blue-900 tracking-tight">
                {{ editingConfig ? 'Edit Configuration' : 'Create New Configuration' }}
              </span>
              <span v-if="editingConfig" class="ml-2 px-2 py-0.5 rounded-xl bg-emerald-100 text-emerald-700 text-xs font-medium">Editing</span>
            </div>
            <transition name="fade-expand">
              <div v-show="showCreateForm" class="bg-white border border-blue-100 rounded-2xl shadow p-6 space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">Configuration Name</label>
                  <input
                    v-model="formConfig.name"
                    type="text"
                    :readonly="!!editingConfig && formConfigUsed"
                    placeholder="e.g., High Quality OCR for Scanned PDFs"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <span v-if="!!editingConfig && formConfigUsed" class="block text-xs text-gray-400 mt-1">Only the name can be changed as this configuration is already used in tasks.</span>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    v-model="formConfig.description"
                    rows="2"
                    :readonly="!!editingConfig && formConfigUsed"
                    placeholder="Describe when to use this configuration..."
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">Processing Mode</label>
                  <select
                    v-model="formConfig.additional_settings.mode"
                    :disabled="!!editingConfig && formConfigUsed"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="fast">Fast (PyMuPDF extraction)</option>
                    <option value="advanced">Advanced (Docling extraction)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">OCR Engine</label>
                  <select
                    v-model="formConfig.additional_settings.ocr_engine"
                    :disabled="!!editingConfig && formConfigUsed"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="ocrmypdf">OCRmyPDF (Tesseract)</option>
                    <option value="paddleocr">PaddleOCR</option>
                    <option value="marker">Marker</option>
                  </select>
                </div>
                <div v-if="formConfig.additional_settings.mode === 'advanced' && !formConfig.additional_settings.use_vlm">
                  <label class="block text-sm font-medium text-gray-700 mb-1">Docling OCR Engine</label>
                  <select
                    v-model="formConfig.additional_settings.docling_ocr_engine"
                    :disabled="!!editingConfig && formConfigUsed"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="rapidocr">RapidOCR</option>
                    <option value="easyocr">EasyOCR</option>
                    <option value="tesseract">Tesseract</option>
                  </select>
                </div>
                <div class="space-y-2">
                  <label class="flex items-center">
                    <input
                      v-model="formConfig.use_ocr"
                      type="checkbox"
                      :disabled="!!editingConfig && formConfigUsed"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span class="ml-2 text-sm text-gray-700">Enable OCR</span>
                  </label>
                  <label class="flex items-center">
                    <input
                      v-model="formConfig.force_ocr"
                      type="checkbox"
                      :disabled="(!formConfig.use_ocr) || (!!editingConfig && formConfigUsed)"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span class="ml-2 text-sm text-gray-700">Force OCR (ignore existing text)</span>
                  </label>
                </div>
                <div v-if="formConfig.use_ocr && (formConfig.additional_settings.ocr_engine === 'ocrmypdf' || formConfig.additional_settings.docling_ocr_engine === 'tesseract')">
                  <label class="block text-sm font-medium text-gray-700 mb-1">OCR Languages</label>
                  <Multiselect
                    v-model="formConfig.ocr_languages"
                    :options="ocrLanguagesForSelect"
                    mode="tags"
                    :searchable="true"
                    :close-on-select="false"
                    :clear-on-select="false"
                    :preserve-search="true"
                    :preselect-first="false"
                    :create-option="false"
                    :can-clear="true"
                    :can-deselect="true"
                    :hide-selected="true"
                    :object="true"
                    placeholder="Select languages"
                    label="label"
                    valueProp="value"
                    track-by="value"
                    class="multiselect-custom"
                  >
                    <template #tag="{ option, handleTagRemove, disabled }">
                      <div class="multiselect-tag">
                        {{ option.label }}
                        <span
                          v-if="!disabled"
                          @click.stop="handleTagRemove(option, $event)"
                          class="multiselect-tag-remove"
                        >
                          <span class="multiselect-tag-remove-icon"></span>
                        </span>
                      </div>
                    </template>
                  </Multiselect>
                </div>
                <div v-if="formConfig.additional_settings.mode === 'advanced' && !formConfig.additional_settings.use_vlm" class="space-y-2">
                  <label class="flex items-center">
                    <input
                      v-model="formConfig.additional_settings.enable_picture_description"
                      type="checkbox"
                      :disabled="!!editingConfig && formConfigUsed"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span class="ml-2 text-sm text-gray-700">Extract picture descriptions</span>
                  </label>
                  <label class="flex items-center">
                    <input
                      v-model="formConfig.additional_settings.enable_formula"
                      type="checkbox"
                      :disabled="!!editingConfig && formConfigUsed"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span class="ml-2 text-sm text-gray-700">Extract formulas</span>
                  </label>
                  <label class="flex items-center">
                    <input
                      v-model="formConfig.additional_settings.enable_code"
                      type="checkbox"
                      :disabled="!!editingConfig && formConfigUsed"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span class="ml-2 text-sm text-gray-700">Extract code blocks</span>
                  </label>
                </div>
                <div v-if="formConfig.additional_settings.mode === 'advanced'" class="space-y-2">
                  <label class="flex items-center">
                    <input
                      v-model="formConfig.additional_settings.use_vlm"
                      type="checkbox"
                      :disabled="!!editingConfig && formConfigUsed"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span class="ml-2 text-sm text-gray-700">Use Vision Language Model (VLM)</span>
                  </label>
                  <div v-if="formConfig.additional_settings.use_vlm" class="ml-6 space-y-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">VLM Model</label>
                      <input
                        v-model="formConfig.additional_settings.vlm_model"
                        type="text"
                        placeholder="e.g., gpt-4-vision-preview"
                        :disabled="!!editingConfig && formConfigUsed"
                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">VLM Prompt</label>
                      <textarea
                        v-model="formConfig.additional_settings.vlm_prompt"
                        rows="2"
                        :disabled="!!editingConfig && formConfigUsed"
                        placeholder="Custom prompt for VLM processing..."
                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">Max Image Dimension</label>
                      <input
                        v-model.number="formConfig.additional_settings.max_image_dim"
                        type="number"
                        min="400"
                        max="2048"
                        step="100"
                        :disabled="!!editingConfig && formConfigUsed"
                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                </div>
                <div v-if="formError" class="mt-2 text-sm text-red-600">
                  {{ formError }}
                </div>
                <div class="flex justify-end space-x-3 mt-4">
                  <button
                    @click="resetForm"
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                    :disabled="isSaving"
                  >
                    Cancel
                  </button>
                  <button
                    v-if="!editingConfig"
                    @click="createConfiguration"
                    :disabled="!formConfig.name || isSaving"
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span v-if="isSaving" class="flex items-center">
                      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                      </svg>
                      Creating...
                    </span>
                    <span v-else>Create Configuration</span>
                  </button>
                  <button
                    v-else
                    @click="saveEdit"
                    :disabled="!formConfig.name || isSaving"
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span v-if="isSaving" class="flex items-center">
                      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                      </svg>
                      Saving...
                    </span>
                    <span v-else>Save Changes</span>
                  </button>
                </div>
              </div>
            </transition>
            <button
              @click="toggleCreateOrEdit"
              class="w-full flex items-center justify-between px-4 py-3 mt-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <span class="font-medium">{{ editingConfig ? 'Cancel Editing' : (showCreateForm ? 'Cancel' : 'Create New Configuration') }}</span>
              <svg
                :class="['h-5 w-5 transition-transform', showCreateForm ? 'rotate-180' : '']"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          <div>
            <div class="flex items-center gap-3 mb-3">
              <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-600 font-bold">2</span>
              <span class="text-lg font-semibold text-blue-900 tracking-tight">Saved Configurations</span>
            </div>
            <div v-if="isLoading" class="flex justify-center py-8">
              <svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
            </div>
            <div v-else-if="configurations.length === 0" class="text-center py-8 text-gray-600">
              <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <p class="mt-2 text-sm">No saved configurations yet</p>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="config in configurations"
                :key="config.id"
                class="border rounded-xl p-4 hover:border-blue-400 transition-colors bg-white flex justify-between items-center"
              >
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">{{ config.name }}</h4>
                  <p v-if="config.description" class="text-sm text-gray-500 mt-1">{{ config.description }}</p>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                      {{ config.additional_settings?.mode || 'fast' }} mode
                    </span>
                    <span v-if="config.use_ocr" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                      OCR: {{ config.additional_settings?.ocr_engine || config.ocr_backend }}
                    </span>
                    <span v-if="config.additional_settings?.use_vlm" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                      VLM: {{ config.additional_settings?.vlm_model || 'Enabled' }}
                    </span>
                    <span v-if="config.additional_settings?.enable_picture_description || config.additional_settings?.enable_formula || config.additional_settings?.enable_code"
                          class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      Advanced extraction
                    </span>
                  </div>
                </div>
                <div class="ml-4 flex items-center space-x-2">
                  <button
                    @click="$emit('config-selected', config)"
                    class="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Use
                  </button>
                  <button
                    @click="editConfiguration(config)"
                    class="text-sm text-gray-600 hover:text-gray-800"
                  >
                    Edit
                  </button>
                  <button
                    @click="deleteConfiguration(config)"
                    class="text-sm text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div v-if="deleteError" class="mt-2 text-sm text-red-600">{{ deleteError }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import Multiselect from '@vueform/multiselect';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});
const emit = defineEmits(['close', 'config-selected']);
const toast = useToast();

const configurations = ref([]);
const isLoading = ref(true);
const showCreateForm = ref(false);
const isSaving = ref(false);
const editingConfig = ref(null);
const formConfig = ref(getDefaultForm());
const formError = ref('');
const deleteError = ref('');
const modalRef = ref(null);

const ocrLanguagesForSelect = ref([
  { value: 'eng', label: 'English' },
  { value: 'spa', label: 'Spanish' },
  { value: 'fra', label: 'French' },
  { value: 'deu', label: 'German' },
  { value: 'ita', label: 'Italian' },
  { value: 'por', label: 'Portuguese' },
  { value: 'rus', label: 'Russian' },
  { value: 'jpn', label: 'Japanese' },
  { value: 'chi_sim', label: 'Chinese (Simplified)' },
  { value: 'chi_tra', label: 'Chinese (Traditional)' },
  { value: 'ara', label: 'Arabic' },
  { value: 'hin', label: 'Hindi' },
  { value: 'kor', label: 'Korean' },
  { value: 'nld', label: 'Dutch' },
  { value: 'pol', label: 'Polish' },
  { value: 'tur', label: 'Turkish' },
  { value: 'vie', label: 'Vietnamese' },
  { value: 'ces', label: 'Czech' },
  { value: 'dan', label: 'Danish' },
  { value: 'fin', label: 'Finnish' },
  { value: 'gre', label: 'Greek' },
  { value: 'heb', label: 'Hebrew' },
  { value: 'hun', label: 'Hungarian' },
  { value: 'nor', label: 'Norwegian' },
  { value: 'swe', label: 'Swedish' },
  { value: 'tha', label: 'Thai' },
  { value: 'ukr', label: 'Ukrainian' },
]);

const formConfigUsed = computed(() => !!editingConfig.value?.used_in_tasks);

function getDefaultForm() {
  return {
    name: '',
    description: '',
    file_type: 'pdf',
    pdf_backend: 'pymupdf4llm',
    ocr_backend: 'ocrmypdf',
    use_ocr: true,
    force_ocr: false,
    ocr_languages: [{ value: 'eng', label: 'English' }],
    additional_settings: {
      mode: 'fast',
      ocr_engine: 'ocrmypdf',
      docling_ocr_engine: 'rapidocr',
      enable_picture_description: false,
      enable_formula: false,
      enable_code: false,
      max_image_dim: 800,
      use_vlm: false,
      use_local_vlm: false,
      local_vlm_repo_id: 'HuggingFaceTB/SmolVLM-256M-Instruct',
      vlm_model: '',
      vlm_base_url: '',
      vlm_prompt: 'Please perform OCR! Please extract the full text from the document and describe images and figures!'
    }
  };
}

function resetForm() {
  showCreateForm.value = false;
  formConfig.value = getDefaultForm();
  editingConfig.value = null;
  formError.value = '';
}

function toggleCreateOrEdit() {
  if (editingConfig.value || showCreateForm.value) {
    resetForm();
  } else {
    showCreateForm.value = true;
  }
}

// Watch for conflicts between VLM and advanced features
watch(() => formConfig.value.additional_settings.use_vlm, (useVlm) => {
  if (useVlm) {
    formConfig.value.additional_settings.enable_picture_description = false;
    formConfig.value.additional_settings.enable_formula = false;
    formConfig.value.additional_settings.enable_code = false;
  }
});

// Watch for advanced features to disable VLM
watch([
  () => formConfig.value.additional_settings.enable_picture_description,
  () => formConfig.value.additional_settings.enable_formula,
  () => formConfig.value.additional_settings.enable_code
], ([picture, formula, code]) => {
  if (picture || formula || code) {
    formConfig.value.additional_settings.use_vlm = false;
  }
});

// Watch for advanced features to switch to advanced mode
watch([
  () => formConfig.value.additional_settings.enable_picture_description,
  () => formConfig.value.additional_settings.enable_formula,
  () => formConfig.value.additional_settings.enable_code
], ([picture, formula, code]) => {
  if ((picture || formula || code) && formConfig.value.additional_settings.mode === 'fast') {
    formConfig.value.additional_settings.mode = 'advanced';
  }
});

onMounted(() => {
  document.body.style.overflow = 'hidden';
  fetchConfigurations();
  nextTick(() => {
    if (modalRef.value) modalRef.value.focus();
  });
});

onUnmounted(() => {
  document.body.style.overflow = '';
});

function getOcrLangLabels(codeList) {
  if (!codeList) return '';
  const lookup = Object.fromEntries(ocrLanguagesForSelect.value.map(o => [o.value, o.label]));
  if (typeof codeList[0] === 'object' && codeList[0] !== null) {
    return codeList.map(o => o.label || lookup[o.value] || o.value).join(', ');
  }
  return codeList.map(c => lookup[c] || c).join(', ');
}

const fetchConfigurations = async () => {
  isLoading.value = true;
  deleteError.value = '';
  try {
    const response = await api.get(`/project/${props.projectId}/preprocessing-config`);
    configurations.value = response.data;
  } catch (error) {
    toast.error('Failed to load configurations');
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

const createConfiguration = async () => {
  if (!formConfig.value.name) return;
  formError.value = '';
  isSaving.value = true;
  deleteError.value = '';
  try {
    const payload = {
      ...formConfig.value,
      ocr_languages: (formConfig.value.ocr_languages || []).map(lang =>
        typeof lang === 'string' ? lang : lang.value
      ),
      // Ensure additional_settings is included
      additional_settings: formConfig.value.additional_settings
    };

    const response = await api.post(`/project/${props.projectId}/preprocessing-config`, payload);
    configurations.value.unshift(response.data);
    toast.success('Configuration created successfully');
    resetForm();
    showCreateForm.value = false;
  } catch (error) {
    const msg = error.response?.data?.detail || 'Failed to create configuration';
    toast.error(msg);
    formError.value = msg;
  } finally {
    isSaving.value = false;
  }
};

function editConfiguration(config) {
  editingConfig.value = { ...config };
  showCreateForm.value = true;
  formError.value = '';
  let langs = config.ocr_languages || [];
  if (!Array.isArray(langs)) langs = [];

  // Merge existing settings with defaults
  const defaultSettings = getDefaultForm().additional_settings;
  const configSettings = config.additional_settings || {};

  formConfig.value = {
    ...config,
    ocr_languages: langs.map(code => {
      const found = ocrLanguagesForSelect.value.find(l => l.value === code || l.value === code?.value);
      return found ? { ...found } : (typeof code === 'string' ? { value: code, label: code } : code);
    }),
    additional_settings: {
      ...defaultSettings,
      ...configSettings
    }
  };
}

const saveEdit = async () => {
  if (!editingConfig.value) return;
  formError.value = '';
  isSaving.value = true;
  try {
    const id = editingConfig.value.id;
    let toSend;
    if (formConfigUsed.value) {
      toSend = { name: formConfig.value.name };
    } else {
      toSend = {
        ...formConfig.value,
        ocr_languages: (formConfig.value.ocr_languages || []).map(lang =>
          typeof lang === 'string' ? lang : lang.value
        ),
        // Ensure additional_settings is included
        additional_settings: formConfig.value.additional_settings
      };
    }
    await api.put(`/project/${props.projectId}/preprocessing-config/${id}`, toSend);
    toast.success('Configuration updated');
    resetForm();
    showCreateForm.value = false;
    editingConfig.value = null;
    fetchConfigurations();
  } catch (error) {
    const msg = error.response?.data?.detail || 'Failed to update configuration';
    toast.error(msg);
    formError.value = msg;
  } finally {
    isSaving.value = false;
  }
};

const deleteConfiguration = async (config) => {
  if (!confirm(`Delete configuration "${config.name}"?`)) return;
  deleteError.value = '';
  try {
    await api.delete(`/project/${props.projectId}/preprocessing-config/${config.id}`);
    configurations.value = configurations.value.filter(c => c.id !== config.id);
    toast.success('Configuration deleted');
  } catch (error) {
    const msg = error.response?.data?.detail || 'Failed to delete configuration';
    toast.error(msg);
    deleteError.value = msg;
  }
};
</script>


<style>
/* Multiselect Custom Styles - matches your main app */
.multiselect-custom {
  --ms-bg: #ffffff;
  --ms-border-color: #d1d5db;
  --ms-border-color-active: #3b82f6;
  --ms-radius: 0.375rem;
  --ms-py: 0.375rem;
  --ms-px: 0.75rem;
  --ms-font-size: 0.875rem;
  --ms-line-height: 1.25rem;
  --ms-option-bg-selected: #eff6ff;
  --ms-option-color-selected: #1e40af;
  --ms-tag-bg: #3b82f6;
  --ms-tag-color: #ffffff;
  --ms-dropdown-bg: #ffffff;
  --ms-dropdown-border-color: #e5e7eb;
  --ms-group-label-bg: #f9fafb;
  --ms-option-bg-pointed: #eff6ff;
  --ms-option-color-pointed: #1e40af;
  --ms-dropdown-radius: 0.375rem;
  --ms-spinner-color: #3b82f6;
  --ms-max-height: 15rem;
  --ms-tag-font-size: 0.75rem;
  --ms-tag-line-height: 1rem;
  --ms-tag-font-weight: 500;
  --ms-tag-py: 0.125rem;
  --ms-tag-px: 0.5rem;
  --ms-tag-radius: 0.25rem;
  --ms-tag-margin: 0.25rem;
}
.multiselect-custom .multiselect-dropdown {
  position: absolute !important;
  top: 100% !important;
  left: 0 !important;
  right: 0 !important;
  margin-top: 0.25rem !important;
  background-color: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 0.375rem !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
  z-index: 50 !important;
  max-height: 15rem !important;
  overflow-y: auto !important;
  display: none !important;
}
.multiselect-custom.is-open .multiselect-dropdown {
  display: block !important;
}
.multiselect-custom.multiselect {
  position: relative !important;
}
.multiselect-custom .multiselect-wrapper {
  background-color: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-radius: 0.375rem !important;
  min-height: 2.5rem !important;
  cursor: pointer !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  flex-wrap: wrap !important;
}
.multiselect-custom.is-active .multiselect-wrapper {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}
.multiselect-custom .multiselect-option {
  display: block !important;
  padding: 0.5rem 0.75rem !important;
  cursor: pointer !important;
  background-color: transparent !important;
}
.multiselect-custom .multiselect-option.is-pointed {
  background-color: #eff6ff !important;
  color: #1e40af !important;
}
.multiselect-custom .multiselect-option.is-selected {
  background-color: #dbeafe !important;
  color: #1e40af !important;
  font-weight: 500 !important;
}
.multiselect-custom .multiselect-option.is-selected.is-hidden {
  display: none !important;
}
.multiselect-custom .multiselect-tag {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  padding: 0.125rem 0.5rem !important;
  border-radius: 0.25rem !important;
  margin: 0.25rem !important;
  display: inline-flex !important;
  align-items: center !important;
}
.multiselect-custom .multiselect-tags {
  padding: 0.25rem !important;
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 0 !important;
  margin: 0 !important;
}
.multiselect-custom .multiselect-tag-remove {
  margin-left: 0.25rem !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 1rem !important;
  height: 1rem !important;
  border-radius: 9999px !important;
  background-color: rgba(255, 255, 255, 0.2) !important;
  transition: background-color 0.2s !important;
}
.multiselect-custom .multiselect-tag-remove:hover {
  background-color: rgba(255, 255, 255, 0.3) !important;
}
.multiselect-custom .multiselect-tag-remove-icon {
  width: 0.75rem !important;
  height: 0.75rem !important;
  display: block !important;
  background-image: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'%3E%3Cpath stroke='%23ffffff' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M6 18L18 6M6 6l12 12'/%3E%3C/svg%3E\") !important;
  background-size: contain !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
}
</style>
