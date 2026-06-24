/**
 * Markdown helpers shared across result/document viewers.
 *
 * `renderMarkdown` renders markdown to HTML via `marked`. Note: this does NOT
 * sanitize with DOMPurify (unlike DocumentViewer.vue's local copy) — it
 * preserves the original TrialResults.vue behaviour verbatim. The eslint
 * `vue/no-v-html` warnings on callers are pre-existing and acceptable.
 */
import { marked } from 'marked'

/**
 * Render a markdown string to HTML.
 * @param {string} text - Markdown source
 * @returns {string} Rendered HTML (or the original text on failure)
 */
export const renderMarkdown = (text) => {
  try {
    return marked(text)
  } catch {
    return text
  }
}

/**
 * Heuristic: does `text` look like markdown?
 * @param {string} text - Text to inspect
 * @returns {boolean}
 */
export const isMarkdown = (text) => {
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
