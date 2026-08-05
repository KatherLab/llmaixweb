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
//
// The `disabled:` variants matter: without them a read-only field (e.g. the
// email in Account settings) is pixel-identical to an editable one, so the user
// only discovers it can't be changed by clicking it.
export const inputClass =
  'w-full px-4 py-2 text-sm rounded-card border border-default-border bg-surface text-content placeholder-content-subtle outline-none transition focus:border-primary focus:ring-2 focus:ring-ring/50 disabled:bg-surface-sunken disabled:text-content-muted disabled:cursor-not-allowed'

// Textarea — same base, vertical resize only.
export const textareaClass = inputClass + ' resize-y'

// Select — same base (native arrow kept).
export const selectClass = inputClass

// Required-but-empty field. Marks the input that is actually blocking the form
// so it doesn't look identical to the ones already answered. Amber (not red):
// nothing is wrong yet, it just still needs an answer.
export const pendingFieldClass = 'ring-1 ring-amber-400/70 dark:ring-amber-500/50'

// Same idea for a bordered *container* (a panel rather than an input). Recolors
// the existing border instead of adding a ring: a ring paints outside the box,
// so any scrolling or overflow-hidden ancestor clips it — which showed up as an
// outline visible only on the corners and one side.
export const pendingPanelClass = 'border-amber-400/70 dark:border-amber-500/50'

// Label — single convention (replaces the ~8 per-component label variants).
export const labelClass = 'block text-sm font-medium text-content-muted mb-1.5'

// Checkbox — native control, accent token-backed, dark-mode automatic.
// Replaces the ~5 incompatible checkbox class variants across modals.
export const checkboxClass =
  'h-4 w-4 rounded border-default-border text-primary focus:ring-ring/50 dark:border-slate-600 dark:bg-slate-700'

// Radio — same shape as checkbox (native radio uses square accent color).
export const radioClass = checkboxClass
