#!/usr/bin/env node
// i18n Phase 3 error-catalog merge.
//
// Each per-domain migration agent writes a fragment to `.i18n-phase3/<domain>.json`
// shaped as `{ en: { <domain>: {...} }, de: {...}, fr: {...}, es: {...} }` (the
// object under each locale is merged beneath the top-level `errors` namespace).
// This script deep-merges every fragment into `frontend/locales/<locale>.json`
// under `errors`. Existing keys win, so the already-committed `errors.auth.*` /
// `errors.http.*` / etc. are never clobbered by a fragment.
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const fragDir = join(root, '.i18n-phase3')
const localesDir = join(root, 'frontend', 'locales')
const LOCALES = ['en', 'de', 'fr', 'es']

if (!existsSync(fragDir)) {
  console.error(`✖ ${fragDir} does not exist — no fragments to merge.`)
  process.exit(1)
}

/** Deep-merge `src` into `dst`; existing leaf values in `dst` are kept. */
function mergeKeep(dst, src) {
  for (const [k, v] of Object.entries(src)) {
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      if (!dst[k] || typeof dst[k] !== 'object') dst[k] = {}
      mergeKeep(dst[k], v)
    } else if (!(k in dst)) {
      dst[k] = v
    }
  }
}

const fragments = readdirSync(fragDir).filter((f) => f.endsWith('.json'))
console.log(`Merging ${fragments.length} fragment(s): ${fragments.join(', ')}`)

const perLocale = Object.fromEntries(LOCALES.map((l) => [l, {}]))
for (const file of fragments) {
  const frag = JSON.parse(readFileSync(join(fragDir, file), 'utf8'))
  for (const loc of LOCALES) {
    if (frag[loc]) mergeKeep(perLocale[loc], frag[loc])
  }
}

for (const loc of LOCALES) {
  const path = join(localesDir, `${loc}.json`)
  const cat = JSON.parse(readFileSync(path, 'utf8'))
  cat.errors = cat.errors || {}
  mergeKeep(cat.errors, perLocale[loc])
  writeFileSync(path, JSON.stringify(cat, null, 2) + '\n', 'utf8')
  console.log(`✓ ${loc}.json updated`)
}
console.log('Done. Run `node scripts/i18n-check.mjs` to verify parity.')
