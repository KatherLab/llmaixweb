/**
 * Markdown helpers shared across result/document viewers.
 *
 * `renderMarkdown` renders markdown to HTML via `marked` and sanitizes the
 * result with DOMPurify. The inputs (LLM reasoning output, extracted document
 * text) are untrusted, so sanitization is mandatory before feeding the output
 * to `v-html`.
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

/**
 * Render a markdown string to sanitized HTML.
 * @param {string} text - Markdown source
 * @returns {string} Sanitized HTML (or sanitized plain text on failure)
 */
export const renderMarkdown = (text: string | null | undefined): string => {
  if (!text) return ''
  try {
    return DOMPurify.sanitize(marked.parse(text) as string)
  } catch {
    // Never return the raw string: every caller feeds this to v-html, so an
    // unsanitized fallback would be an XSS escape hatch around DOMPurify
    // whenever marked throws on adversarial LLM/OCR content.
    return DOMPurify.sanitize(text)
  }
}

/**
 * Heuristic: does `text` look like markdown?
 * @param {string} text - Text to inspect
 * @returns {boolean}
 */
export const isMarkdown = (text: string | null | undefined): boolean => {
  if (!text) return false
  try {
    return (
      text.includes('#') ||
      text.includes('**') ||
      text.includes('*') ||
      text.includes('[') ||
      text.includes('```') ||
      /\n\s*-\s/.test(text) ||
      /\n\s*\d+\.\s/.test(text)
    )
  } catch {
    return false
  }
}
