#!/usr/bin/env node
// Merge per-domain i18n catalogs (written by the Phase-2 sub-agents into
// .i18n-phase2/*.json) into the canonical frontend/locales/{en,de,fr,es}.json.
//
// Each temp file looks like { en:{ns:{…}}, de:{…}, fr:{…}, es:{…} } where the
// top-level keys are the domain's namespace(s). Existing catalog keys WIN on
// conflict (so already-migrated strings like AppLayout's are never clobbered);
// temp files only fill in keys that don't exist yet.
import { readFileSync, readdirSync, writeFileSync, existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const localesDir = join(root, 'frontend', 'locales')
const tempDir = join(root, '.i18n-phase2')
const LOCALES = ['en', 'de', 'fr', 'es']

/** Deep-merge `add` into `base`, keeping existing `base` leaves on conflict. */
function mergeFill(base, add) {
  for (const [key, value] of Object.entries(add)) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      if (!base[key] || typeof base[key] !== 'object') base[key] = {}
      mergeFill(base[key], value)
    } else if (base[key] === undefined) {
      base[key] = value
    }
  }
  return base
}

if (!existsSync(tempDir)) {
  console.error(`No temp dir ${tempDir}; nothing to merge.`)
  process.exit(1)
}

const catalogs = Object.fromEntries(
  LOCALES.map((l) => [l, JSON.parse(readFileSync(join(localesDir, `${l}.json`), 'utf8'))]),
)

const tempFiles = readdirSync(tempDir).filter((f) => f.endsWith('.json'))
let merged = 0
for (const file of tempFiles) {
  const data = JSON.parse(readFileSync(join(tempDir, file), 'utf8'))
  for (const locale of LOCALES) {
    if (data[locale]) mergeFill(catalogs[locale], data[locale])
  }
  merged++
  console.log(`  merged ${file}`)
}

for (const locale of LOCALES) {
  writeFileSync(join(localesDir, `${locale}.json`), JSON.stringify(catalogs[locale], null, 2) + '\n')
}
console.log(`\nMerged ${merged} domain catalog(s) into ${LOCALES.length} locale files.`)
