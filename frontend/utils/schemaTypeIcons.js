/**
 * Shared JSON-schema property type icons + metadata.
 * Previously duplicated byte-for-byte across VisualSchemaEditor, SchemaBlock,
 * TreeNode, and PropertyDetailsEditor.
 */
import { h } from 'vue'

export const StringIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
      }),
    ])
  },
}

export const NumberIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M7 20l4-16m2 16l4-16M6 9h14M4 15h14',
      }),
    ])
  },
}

export const BooleanIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
      }),
    ])
  },
}

export const ObjectIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
      }),
    ])
  },
}

export const ArrayIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M4 6h16M4 10h16M4 14h16M4 18h16',
      }),
    ])
  },
}

/** Map of schema type -> icon component. */
export const TYPE_ICONS = {
  string: StringIcon,
  number: NumberIcon,
  boolean: BooleanIcon,
  object: ObjectIcon,
  array: ArrayIcon,
}

/** Map of schema type -> Tailwind background color class. */
export const TYPE_COLORS = {
  string: 'bg-green-500',
  number: 'bg-blue-500',
  boolean: 'bg-purple-500',
  object: 'bg-orange-500',
  array: 'bg-pink-500',
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
 * Get the color class for a schema type.
 * @param {string} type - JSON schema type
 * @returns {string} Tailwind class
 */
export function getTypeColor(type) {
  return TYPE_COLORS[type] || 'bg-gray-500'
}
