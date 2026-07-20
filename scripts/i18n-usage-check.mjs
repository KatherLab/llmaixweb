#!/usr/bin/env node
// i18n usage check.
//
// Statically scans the frontend for `$t('key')` / `t('key')` / `i18n.global.t('key')`
// calls with a *literal* key and asserts every such key exists in the
// source-of-truth `en.json`. Catches the classic i18n bug where a component
// references a message key that was never added to the catalog (which renders
// the raw key at runtime — invisible to type-check and to the parity check).
//
// Dynamic keys (template literals / variables, e.g. `$t(`language.${loc}`)`)
// can't be verified statically and are skipped.
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const frontendDir = join(root, 'frontend')
const enCatalog = JSON.parse(readFileSync(join(frontendDir, 'locales', 'en.json'), 'utf8'))

function flattenKeys(obj, prefix = '') {
  const keys = new Set()
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      for (const k of flattenKeys(value, path)) keys.add(k)
    } else {
      keys.add(path)
    }
  }
  return keys
}

const known = flattenKeys(enCatalog)

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry === 'dist' || entry === 'locales') continue
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...walk(full))
    else if (/\.(vue|ts)$/.test(entry) && !/\.(test|spec)\.ts$/.test(entry)) out.push(full)
  }
  return out
}

// Match $t('x'), t('x'), .t('x') with a literal single/double-quoted key.
// The lookbehind excludes identifiers ending in "t" (format(, select(, count(…).
const CALL = /(?<![A-Za-z0-9_$])\$?t\(\s*(['"])([^'"]+)\1/g

const missing = []
for (const file of walk(frontendDir)) {
  const src = readFileSync(file, 'utf8')
  for (const m of src.matchAll(CALL)) {
    const key = m[2]
    if (!known.has(key)) {
      missing.push({ file: relative(root, file), key })
    }
  }
}

if (missing.length) {
  console.error(`✖ ${missing.length} i18n key(s) used but missing from en.json:\n`)
  for (const { file, key } of missing) console.error(`  ${key}  (${file})`)
  console.error('\ni18n usage check failed.')
  process.exit(1)
}
console.log(`✓ All statically-resolvable i18n keys exist in en.json.`)
