// update-version.js
import fs from 'fs/promises';
import path from 'path';
import packageJson from '../package.json' with { type: 'json' };

const versionJs = `export const frontendVersion = '${packageJson.version}';`;
const versionJsPath = path.join(process.cwd(), 'frontend', 'version.js');

try {
  await fs.writeFile(versionJsPath, versionJs);
  console.log(`Updated frontendVersion to ${packageJson.version} in ${versionJsPath}`);
} catch (error) {
  console.error(`Error updating frontendVersion: ${error}`);
}