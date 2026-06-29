/**
 * Shared JSON-schema property type icons + metadata.
 * Previously duplicated byte-for-byte across VisualSchemaEditor, SchemaBlock,
 * TreeNode, and PropertyDetailsEditor.
 *
 * Icons are sourced from `@lucide/vue` (the single icon set used app-wide).
 * The exported names are kept stable so callers don't change.
 */
import { Hash, List, SquarePen, ToggleLeft, Braces } from '@lucide/vue'
import { getPillClass } from '@/utils/statusStyles'

/** Icon component for the `string` schema type (pencil — "editable text"). */
export const StringIcon = SquarePen

/** Icon component for the `number` schema type (hash — `#`). */
export const NumberIcon = Hash

/** Icon component for the `boolean` schema type (toggle). */
export const BooleanIcon = ToggleLeft

/** Icon component for the `object` schema type (braces — `{}`). */
export const ObjectIcon = Braces

/** Icon component for the `array` schema type (list rows). */
export const ArrayIcon = List

/** Map of schema type -> icon component. */
export const TYPE_ICONS = {
  string: StringIcon,
  number: NumberIcon,
  boolean: BooleanIcon,
  object: ObjectIcon,
  array: ArrayIcon,
}

/** Map of schema type -> Tailwind background color class (solid, for icon badges). */
export const TYPE_COLORS = {
  string: 'bg-green-500',
  number: 'bg-blue-500',
  boolean: 'bg-purple-500',
  object: 'bg-orange-500',
  array: 'bg-pink-500',
}

/** Map of schema type -> pill color name (resolves via getPillClass, with dark mode). */
export const TYPE_PILL_COLORS = {
  string: 'green',
  number: 'blue',
  boolean: 'purple',
  object: 'orange',
  array: 'pink',
}

/**
 * Get the icon component for a schema type (falls back to StringIcon).
 * @param {string} type - JSON schema type ('string' | 'number' | 'boolean' | 'object' | 'array')
 * @returns {object} icon component
 */
export function getTypeIcon(type) {
  return TYPE_ICONS[type] || StringIcon
}

/**
 * Get the solid background color class for a schema type.
 * @param {string} type - JSON schema type
 * @returns {string} Tailwind class
 */
export function getTypeColor(type) {
  return TYPE_COLORS[type] || 'bg-slate-500'
}

/**
 * Get the pill (bg-*-100 text-*-700, dark-mode-aware) class for a schema type.
 * Replaces the per-component type→badge-class maps in SchemaBlock / FieldTree.
 * @param {string} type - JSON schema type
 * @returns {string} Tailwind class
 */
export function getTypePillClass(type) {
  return getPillClass(TYPE_PILL_COLORS[type] || 'gray')
}
