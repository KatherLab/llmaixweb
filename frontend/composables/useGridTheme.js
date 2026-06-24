/**
 * Composable for the shared ag-grid `themeMaterial` theme with dark-mode support.
 *
 * Collapses the near-identical isDarkMode() / getGridTheme() / MutationObserver
 * blocks that were duplicated across ProjectGrid, InvitationGrid and UserGrid.
 *
 * Dark mode is derived from the same `localStorage['darkMode']` flag (plus the
 * `prefers-color-scheme` media query as a fallback) that AppLayout's toggle
 * writes. Because AppLayout toggles the `dark` class on `<html>`, a
 * MutationObserver on that class rebuilds the theme reactively — so grids
 * re-theme immediately when the user flips dark mode, without a reload.
 *
 * Usage:
 *   const { gridTheme } = useGridTheme();
 *   const { gridTheme } = useGridTheme({ rowHeight: 40 });
 *
 * @param {object}  options
 * @param {number}  [options.rowHeight=56]
 * @param {number}  [options.listItemHeight]
 * @param {number}  [options.controlBorderRadius]
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { themeMaterial } from 'ag-grid-community'

const isDarkMode = () => {
  if (typeof window === 'undefined') return false
  return (
    localStorage.getItem('darkMode') === '1' ||
    (!localStorage.getItem('darkMode') && window.matchMedia('(prefers-color-scheme: dark)').matches)
  )
}

export function useGridTheme(options = {}) {
  const { rowHeight = 56, listItemHeight, controlBorderRadius } = options

  const buildTheme = () => {
    const darkMode = isDarkMode()
    const params = {
      spacing: 12,
      borderRadius: 8,
      rowHeight,
      headerHeight: 48,
      accentColor: '#3b82f6',
      rowHoverColor: darkMode ? '#1e293b' : '#f3f4f6',
      headerBackgroundColor: darkMode ? '#1e293b' : '#f9fafb',
      headerTextColor: darkMode ? '#e2e8f0' : '#111827',
      headerCellHoverBackgroundColor: darkMode ? '#334155' : '#e0e7ff',
      // Dark mode colors
      backgroundColor: darkMode ? '#0f172a' : '#ffffff',
      foregroundColor: darkMode ? '#f1f5f9' : '#111827',
      rowBackgroundColor: darkMode ? '#0f172a' : '#ffffff',
      rowForegroundColor: darkMode ? '#e2e8f0' : '#111827',
      borderColor: darkMode ? '#334155' : '#e5e7eb',
    }
    if (listItemHeight !== undefined) params.listItemHeight = listItemHeight
    if (controlBorderRadius !== undefined) params.controlBorderRadius = controlBorderRadius
    return themeMaterial.withParams(params)
  }

  const gridTheme = ref(buildTheme())

  let observer
  onMounted(() => {
    if (typeof window === 'undefined') return
    observer = new MutationObserver(() => {
      gridTheme.value = buildTheme()
    })
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })
  })
  onUnmounted(() => {
    observer?.disconnect()
  })

  return { gridTheme }
}
