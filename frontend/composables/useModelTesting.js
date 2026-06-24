/**
 * Composable for the LLM model-test flow used by CreateTrialModal.
 *
 * Extracted verbatim from CreateTrialModal.vue to keep behavior identical:
 *  - `testAndLoadModels(apiKey, baseUrl)` — connection test + model list load
 *  - `loadModels(apiKey, baseUrl)` — list available models
 *  - `resetModelTest()` — clear model-test state (called on prompt/schema/model/option change)
 *  - `testSelectedModel()` — run model+schema compatibility test
 *  - all connection/model state + the `configStatus` / `modelTestStatus` computeds
 *
 * The composable takes the shared reactive `trialData` and the advanced-option
 * refs as dependencies (they live in the parent / form), so there is a single
 * source of truth and no behavior drift.
 *
 * Usage:
 *   const {
 *     availableModels, isLoadingModels, isTestingConnection, isTestingModel,
 *     connectionTested, connectionValid, modelTested, modelValid,
 *     systemConfigError, customConfigError, modelTestError, hasSystemConfig,
 *     hasCustomApiSettings, hasValidSystemConfig, hasValidCustomConfig,
 *     hasValidConfig, configStatus, modelTestStatus, currentError,
 *     testAndLoadModels, loadModels, resetModelTest, testSelectedModel,
 *   } = useModelTesting({ trialData, projectId, maxCompletionTokens, temperature, reasoningEffort })
 */
import { ref, computed } from 'vue'
import { useToast } from 'vue-toastification'
import { llmApi } from '@/services/llmApi'

export function useModelTesting({
  trialData,
  projectId,
  maxCompletionTokens,
  temperature,
  reasoningEffort,
}) {
  const toast = useToast()

  const availableModels = ref([])
  const isLoadingModels = ref(false)
  const isTestingConnection = ref(false)
  const isTestingModel = ref(false)
  const connectionTested = ref(false)
  const connectionValid = ref(false)
  const modelTested = ref(false)
  const modelValid = ref(false)
  const systemConfigError = ref(null)
  const customConfigError = ref(null)
  const modelTestError = ref(null)
  const hasSystemConfig = ref(true)

  const hasCustomApiSettings = computed(() => {
    return (trialData.value.api_key || '').trim() || (trialData.value.base_url || '').trim()
  })
  const hasValidSystemConfig = computed(
    () => hasSystemConfig.value && !systemConfigError.value && !hasCustomApiSettings.value,
  )
  const hasValidCustomConfig = computed(
    () =>
      hasCustomApiSettings.value &&
      connectionTested.value &&
      connectionValid.value &&
      !customConfigError.value,
  )
  const hasValidConfig = computed(() => hasValidSystemConfig.value || hasValidCustomConfig.value)

  const currentError = computed(() =>
    hasCustomApiSettings.value ? customConfigError.value : systemConfigError.value,
  )

  const configStatus = computed(() => {
    if (isTestingConnection.value || isLoadingModels.value) {
      return { type: 'loading', message: 'Testing configuration...' }
    }

    if (hasCustomApiSettings.value) {
      if (!connectionTested.value)
        return { type: 'warning', message: 'Custom API settings need to be tested' }
      if (!connectionValid.value)
        return { type: 'error', message: customConfigError.value || 'Custom API connection failed' }
      if (availableModels.value.length === 0)
        return { type: 'error', message: 'No models available with current settings' }
      return {
        type: 'success',
        message: `Custom API connected - ${availableModels.value.length} models available`,
      }
    } else {
      if (!hasSystemConfig.value)
        return {
          type: 'error',
          message:
            'System configuration incomplete - please contact administrator or use custom settings',
        }
      if (systemConfigError.value)
        return {
          type: 'error',
          message: `System configuration error - please contact administrator: ${systemConfigError.value}`,
        }
      if (availableModels.value.length === 0)
        return { type: 'error', message: 'No models available - please contact administrator' }
      return {
        type: 'success',
        message: `System configuration active - ${availableModels.value.length} models available`,
      }
    }
  })

  const modelTestStatus = computed(() => {
    if (!trialData.value.llm_model || !trialData.value.schema_id) {
      return { type: 'none', message: 'Select a model and schema first' }
    }
    if (isTestingModel.value) return { type: 'loading', message: 'Testing model with schema...' }
    if (!modelTested.value)
      return { type: 'warning', message: 'Model must be tested with schema before creating trial' }
    if (!modelValid.value)
      return { type: 'error', message: modelTestError.value || 'Model test failed' }
    return {
      type: 'success',
      message: `Model '${trialData.value.llm_model}' supports the selected schema`,
    }
  })

  const resetModelTest = () => {
    modelTested.value = false
    modelValid.value = false
    modelTestError.value = null
  }

  const loadModels = async (apiKey = '', baseUrl = '') => {
    isLoadingModels.value = true
    try {
      const params = {}
      if ((apiKey || '').trim()) params.api_key = apiKey.trim()
      if ((baseUrl || '').trim()) params.base_url = baseUrl.trim()

      const response = await llmApi.models(params)

      if (response.data.success) {
        availableModels.value = response.data.models || []

        // Clear previous model selection when models change
        if (
          trialData.value.llm_model &&
          !availableModels.value.includes(trialData.value.llm_model)
        ) {
          trialData.value.llm_model = ''
          resetModelTest()
        }
      } else {
        availableModels.value = []
        throw new Error(response.data.message || 'Failed to load models')
      }
    } catch (error) {
      availableModels.value = []
      throw error
    } finally {
      isLoadingModels.value = false
    }
  }

  const testAndLoadModels = async (apiKey = '', baseUrl = '') => {
    isTestingConnection.value = true
    connectionTested.value = false
    connectionValid.value = false
    availableModels.value = []
    systemConfigError.value = null
    customConfigError.value = null

    resetModelTest()

    try {
      const params = {}
      if ((apiKey || '').trim()) params.api_key = apiKey.trim()
      if ((baseUrl || '').trim()) params.base_url = baseUrl.trim()

      const testResponse = await llmApi.testConnection(params)

      if (testResponse.data.success) {
        connectionValid.value = true
        connectionTested.value = true

        await loadModels(apiKey, baseUrl)

        if (availableModels.value.length === 0) {
          const errorMsg = 'Connection successful but no models available'
          if (hasCustomApiSettings.value) {
            customConfigError.value = errorMsg
            toast.error(errorMsg)
          } else {
            systemConfigError.value = errorMsg
            toast.error('No models available. Please contact your administrator.')
          }
        } else {
          toast.success(`Connection successful. Loaded ${availableModels.value.length} models.`)
        }
      } else {
        connectionValid.value = false
        connectionTested.value = true
        const errorMsg = testResponse.data.message || 'Connection test failed'

        if (hasCustomApiSettings.value) {
          customConfigError.value = errorMsg
          toast.error(errorMsg)
        } else {
          systemConfigError.value = errorMsg
          hasSystemConfig.value = false

          if (testResponse.data.error_type === 'incomplete_config') {
            toast.error(
              'System LLM configuration is incomplete. Please contact your administrator or provide custom API settings.',
            )
          } else {
            toast.error(
              `System LLM configuration error: ${errorMsg}. Please contact your administrator.`,
            )
          }
        }
      }
    } catch (error) {
      connectionValid.value = false
      connectionTested.value = true
      const errorMsg =
        error?.response?.data?.message || error?.response?.data?.detail || error?.message
      if (hasCustomApiSettings.value) {
        customConfigError.value = errorMsg
        toast.error(`Connection failed: ${errorMsg}`)
      } else {
        systemConfigError.value = errorMsg
        hasSystemConfig.value = false
        toast.error(`System configuration error: ${errorMsg}. Please contact your administrator.`)
      }
    } finally {
      isTestingConnection.value = false
    }
  }

  const testSelectedModel = async () => {
    if (!trialData.value.llm_model) {
      toast.error('Please select a model first')
      return
    }
    if (!trialData.value.schema_id) {
      toast.error('Please select a schema first')
      return
    }

    isTestingModel.value = true
    modelTested.value = false
    modelValid.value = false
    modelTestError.value = null

    try {
      const params = {
        // project_id is required by the backend (LLMModelSchemaTestRequest)
        // to scope the schema lookup to the caller's project.
        project_id: parseInt(projectId.value),
        llm_model: trialData.value.llm_model,
        schema_id: parseInt(trialData.value.schema_id),
      }

      if ((trialData.value.api_key || '').trim()) params.api_key = trialData.value.api_key.trim()
      if ((trialData.value.base_url || '').trim()) params.base_url = trialData.value.base_url.trim()

      if (maxCompletionTokens.value && parseInt(maxCompletionTokens.value) > 0) {
        params.max_completion_tokens = parseInt(maxCompletionTokens.value)
      }
      if (temperature.value !== '' && !isNaN(Number(temperature.value))) {
        params.temperature = Number(temperature.value)
      }
      if (reasoningEffort.value) {
        params.reasoning_effort = reasoningEffort.value
      }

      const response = await llmApi.testModelSchema(params)

      modelTested.value = true

      if (response.data.success) {
        modelValid.value = true
        toast.success(
          `Model '${trialData.value.llm_model}' supports structured output with the selected schema!`,
        )
      } else {
        modelValid.value = false
        modelTestError.value = response.data.message || 'Model test failed'

        if (response.data.error_type === 'structured_output_not_supported') {
          toast.error(
            `Model '${trialData.value.llm_model}' does not support structured output. Please select a different model.`,
          )
        } else if (response.data.error_type === 'schema_validation_error') {
          toast.error(`Schema validation failed: ${response.data.message}`)
        } else {
          toast.error(response.data.message || 'Model test failed')
        }
      }
    } catch (error) {
      modelTested.value = true
      modelValid.value = false
      const errorMsg =
        error?.response?.data?.message || error?.response?.data?.detail || error?.message
      modelTestError.value = errorMsg
      toast.error(`Model test failed: ${errorMsg}`)
    } finally {
      isTestingModel.value = false
    }
  }

  return {
    availableModels,
    isLoadingModels,
    isTestingConnection,
    isTestingModel,
    connectionTested,
    connectionValid,
    modelTested,
    modelValid,
    systemConfigError,
    customConfigError,
    modelTestError,
    hasSystemConfig,
    hasCustomApiSettings,
    hasValidSystemConfig,
    hasValidCustomConfig,
    hasValidConfig,
    configStatus,
    modelTestStatus,
    currentError,
    testAndLoadModels,
    loadModels,
    resetModelTest,
    testSelectedModel,
  }
}
