// Reactive store for OCR engine display names
// Populated from GET /auth/settings
const ocrEngineLabels = {
  ocrmypdf: { name: 'Quick (Local OCR)', subtitle: 'OCRmyPDF / Tesseract' },
  mistral_ocr: { name: 'Mistral OCR API', subtitle: 'Best for complex layouts' },
  llm_vision: { name: 'Vision LLM API', subtitle: 'Best for complex documents' },
};

export function getEngineLabel(engineKey) {
  const entry = ocrEngineLabels[engineKey];
  if (!entry) return engineKey || 'Default';
  return entry.name;
}

// Shows both display name and internal key: "DeepSeek-OCR (mistral_ocr)"
export function getEngineLabelWithKey(engineKey) {
  const entry = ocrEngineLabels[engineKey];
  if (!entry) return engineKey || 'Default';
  return `${entry.name} (${engineKey})`;
}

export function getEngineSubtitle(engineKey) {
  const entry = ocrEngineLabels[engineKey];
  return entry?.subtitle || '';
}

export function setEngineLabels(settings) {
  if (settings.mistral_ocr_display_name) {
    ocrEngineLabels.mistral_ocr.name = settings.mistral_ocr_display_name;
    ocrEngineLabels.mistral_ocr.subtitle = settings.mistral_ocr_display_subtitle || ocrEngineLabels.mistral_ocr.subtitle;
  }
  if (settings.vision_ocr_display_name) {
    ocrEngineLabels.llm_vision.name = settings.vision_ocr_display_name;
    ocrEngineLabels.llm_vision.subtitle = settings.vision_ocr_display_subtitle || ocrEngineLabels.llm_vision.subtitle;
  }
}
