// update-version.js
import fs from 'fs/promises'
import path from 'path'
import packageJson from '../package.json' with { type: 'json' }

const versionJs = `// Frontend version - update this on each release
// Note: Also bump version in pyproject.toml for backend
export const frontendVersion = '${packageJson.version}';
// Git commit hash - injected at build time via VITE_GIT_COMMIT_HASH
export const frontendGitCommit = import.meta.env.VITE_GIT_COMMIT_HASH || 'unknown';
`
const versionJsPath = path.join(process.cwd(), 'frontend', 'version.js')

try {
  await fs.writeFile(versionJsPath, versionJs)
  console.log(`Updated frontendVersion to ${packageJson.version} in ${versionJsPath}`)
} catch (error) {
  console.error(`Error updating frontendVersion: ${error}`)
}
