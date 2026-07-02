// Reactive store for OCR engine display names
// Populated from GET /auth/settings
import type { PublicAuthSettings } from '@/types'

interface OcrEngineEntry {
  name: string
  subtitle: string
}

const ocrEngineLabels: Record<string, OcrEngineEntry> = {
  ocrmypdf: { name: 'Quick (Local OCR)', subtitle: 'Legacy: OCRmyPDF' },
  docling_tesseract: { name: 'Quick (Local OCR)', subtitle: 'Docling / Tesseract' },
  mistral_ocr: { name: 'Mistral OCR API', subtitle: 'Best for complex layouts' },
  llm_vision: { name: 'Vision LLM API', subtitle: 'Best for complex documents' },
}

export function getEngineLabel(engineKey: string | null | undefined): string {
  if (!engineKey) return 'Default'
  const entry = ocrEngineLabels[engineKey]
  if (!entry) return engineKey
  return entry.name
}

// Shows both display name and internal key: "DeepSeek-OCR (mistral_ocr)"
export function getEngineLabelWithKey(engineKey: string | null | undefined): string {
  if (!engineKey) return 'Default'
  const entry = ocrEngineLabels[engineKey]
  if (!entry) return engineKey
  return `${entry.name} (${engineKey})`
}

export function getEngineSubtitle(engineKey: string | null | undefined): string {
  const entry = engineKey ? ocrEngineLabels[engineKey] : undefined
  return entry?.subtitle || ''
}

export function setEngineLabels(settings: Partial<PublicAuthSettings>): void {
  if (settings.mistral_ocr_display_name) {
    const entry = ocrEngineLabels.mistral_ocr
    if (entry) {
      entry.name = settings.mistral_ocr_display_name
      entry.subtitle = settings.mistral_ocr_display_subtitle || entry.subtitle
    }
  }
  if (settings.vision_ocr_display_name) {
    const entry = ocrEngineLabels.llm_vision
    if (entry) {
      entry.name = settings.vision_ocr_display_name
      entry.subtitle = settings.vision_ocr_display_subtitle || entry.subtitle
    }
  }
  if (settings.docling_serve_display_name) {
    const entry = ocrEngineLabels.docling_tesseract
    if (entry) {
      entry.name = settings.docling_serve_display_name
      entry.subtitle = settings.docling_serve_display_subtitle || entry.subtitle
    }
  }
}
