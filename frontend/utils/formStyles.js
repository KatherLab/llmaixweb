/**
 * Shared form-field class strings (text input / textarea / select / label).
 *
 * One modern, token-backed look for every boxed form field in the app — the
 * "Invite New User" style routed through the semantic design tokens in
 * `assets/main.css` (`bg-surface`, `border-default-border`, `text-content`,
 * `ring`, `rounded-card`, …). Tokens auto-handle dark mode, so callers need no
 * `dark:` variants.
 *
 * Use with a static `:class` bind (e.g. `:class="inputClass"`) or inline the
 * literal — the strings are complete so the Tailwind v4 scanner detects them.
 * Append extra classes (e.g. `pl-10` for a leading icon, `resize-none`) as
 * needed; they merge cleanly.
 */

// Boxed text input — modern, token-backed, dark-mode automatic.
export const inputClass =
  'w-full px-4 py-2 text-sm rounded-card border border-default-border bg-surface text-content placeholder-content-subtle outline-none transition focus:border-primary focus:ring-2 focus:ring-ring/50'

// Textarea — same base, vertical resize only.
export const textareaClass = inputClass + ' resize-y'

// Select — same base (native arrow kept).
export const selectClass = inputClass

// Label — single convention (replaces the ~8 per-component label variants).
export const labelClass = 'block text-sm font-medium text-content-muted mb-1.5'
