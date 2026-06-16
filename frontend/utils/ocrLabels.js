// Reactive store for OCR engine display names
// Populated from GET /auth/settings
const ocrEngineLabels = {
  ocrmypdf: { name: 'Quick (Local OCR)', subtitle: 'Legacy: OCRmyPDF' },
  docling_tesseract: { name: 'Quick (Local OCR)', subtitle: 'Docling / Tesseract' },
  mistral_ocr: { name: 'Mistral OCR API', subtitle: 'Best for complex layouts' },
  llm_vision: { name: 'Vision LLM API', subtitle: 'Best for complex documents' },
}

// Track which OCR engines are enabled
const ocrEngineEnabled = {
  docling_tesseract: true,
  mistral_ocr: true,
  llm_vision: true,
}

export function getEngineLabel(engineKey) {
  const entry = ocrEngineLabels[engineKey]
  if (!entry) return engineKey || 'Default'
  return entry.name
}

// Shows both display name and internal key: "DeepSeek-OCR (mistral_ocr)"
export function getEngineLabelWithKey(engineKey) {
  const entry = ocrEngineLabels[engineKey]
  if (!entry) return engineKey || 'Default'
  return `${entry.name} (${engineKey})`
}

export function getEngineSubtitle(engineKey) {
  const entry = ocrEngineLabels[engineKey]
  return entry?.subtitle || ''
}

export function isEngineEnabled(engineKey) {
  return ocrEngineEnabled[engineKey] ?? true
}

export function setEngineLabels(settings) {
  if (settings.mistral_ocr_display_name) {
    ocrEngineLabels.mistral_ocr.name = settings.mistral_ocr_display_name
    ocrEngineLabels.mistral_ocr.subtitle =
      settings.mistral_ocr_display_subtitle || ocrEngineLabels.mistral_ocr.subtitle
  }
  if (settings.vision_ocr_display_name) {
    ocrEngineLabels.llm_vision.name = settings.vision_ocr_display_name
    ocrEngineLabels.llm_vision.subtitle =
      settings.vision_ocr_display_subtitle || ocrEngineLabels.llm_vision.subtitle
  }
  if (settings.docling_serve_display_name) {
    ocrEngineLabels.docling_tesseract.name = settings.docling_serve_display_name
    ocrEngineLabels.docling_tesseract.subtitle =
      settings.docling_serve_display_subtitle || ocrEngineLabels.docling_tesseract.subtitle
  }
  // Update enabled status
  if (settings.docling_serve_enabled !== undefined) {
    ocrEngineEnabled.docling_tesseract = settings.docling_serve_enabled
  }
  if (settings.mistral_ocr_enabled !== undefined) {
    ocrEngineEnabled.mistral_ocr = settings.mistral_ocr_enabled
  }
  if (settings.vision_ocr_enabled !== undefined) {
    ocrEngineEnabled.llm_vision = settings.vision_ocr_enabled
  }
}
