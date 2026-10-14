import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const timestamp = new Date().toISOString().replace(/[-:.]/g, '').slice(0, 12);
const projectName = process.argv[2] || 'app';
const version = `${projectName}-${timestamp}`;
const swPath = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public', 'sw.js');

function replaceAssignment(source, name) {
  const regex = new RegExp(`const ${name} = ['"][^'"]+['"];`);
  if (!regex.test(source)) return null;
  return source.replace(regex, `const ${name} = '${version}';`);
}

let swContent = fs.readFileSync(swPath, 'utf8');
let updated = false;

for (const name of ['CACHE_NAME', 'SW_VERSION']) {
  const next = replaceAssignment(swContent, name);
  if (next) {
    swContent = next;
    updated = true;
  }
}

if (!updated) {
  console.error('Could not find CACHE_NAME or SW_VERSION in service worker');
  process.exit(1);
}

fs.writeFileSync(swPath, swContent);
console.log(`Updated service worker version to: ${version}`);
