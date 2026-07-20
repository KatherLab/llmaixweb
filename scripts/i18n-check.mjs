#!/usr/bin/env node
// i18n catalog parity check.
//
// Asserts every non-source locale under frontend/locales/ has exactly the same
// set of (deeply-flattened) message keys as the source-of-truth `en.json` —
// no missing keys, no extras. Run in `npm run check` / CI so translations can
// never silently drift out of sync with the English catalog.
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const SOURCE_LOCALE = 'en'
const localesDir = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'frontend', 'locales')

/** Flatten a nested message object into dotted key paths. */
function flattenKeys(obj, prefix = '') {
  const keys = []
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      keys.push(...flattenKeys(value, path))
    } else {
      keys.push(path)
    }
  }
  return keys
}

function loadCatalog(locale) {
  return JSON.parse(readFileSync(join(localesDir, `${locale}.json`), 'utf8'))
}

const localeFiles = readdirSync(localesDir).filter((f) => f.endsWith('.json'))
const sourceKeys = new Set(flattenKeys(loadCatalog(SOURCE_LOCALE)))

let failed = false
for (const file of localeFiles) {
  const locale = file.replace(/\.json$/, '')
  if (locale === SOURCE_LOCALE) continue

  const keys = new Set(flattenKeys(loadCatalog(locale)))
  const missing = [...sourceKeys].filter((k) => !keys.has(k))
  const extra = [...keys].filter((k) => !sourceKeys.has(k))

  if (missing.length || extra.length) {
    failed = true
    console.error(`\n✖ ${locale}.json is out of sync with ${SOURCE_LOCALE}.json`)
    if (missing.length) console.error(`  Missing keys (${missing.length}):\n    ${missing.join('\n    ')}`)
    if (extra.length) console.error(`  Extra keys (${extra.length}):\n    ${extra.join('\n    ')}`)
  } else {
    console.log(`✓ ${locale}.json (${keys.size} keys)`)
  }
}

if (failed) {
  console.error('\ni18n catalog parity check failed.')
  process.exit(1)
}
console.log('\nAll locale catalogs are in sync.')
