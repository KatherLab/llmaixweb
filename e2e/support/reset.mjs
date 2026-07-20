// Pre-run cleanup for the e2e smoke: start every run from a clean backend
// state so the first-admin flow and document/trial counts are deterministic.
// Runs BEFORE Playwright boots the webServers (see the `test:e2e` npm script),
// so the backend comes up against a fresh SQLite DB + empty local storage.
import { rmSync, mkdirSync, existsSync } from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const db = path.join(root, 'e2e_test.db')
const storage = path.join(root, 'e2e_local_storage')

for (const f of [db, `${db}-wal`, `${db}-shm`]) {
  if (existsSync(f)) rmSync(f)
}
rmSync(storage, { recursive: true, force: true })
mkdirSync(storage, { recursive: true }) // LOCAL_DIRECTORY must exist at boot

console.log('[e2e reset] cleared e2e_test.db + e2e_local_storage')
