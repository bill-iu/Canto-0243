/**
 * ponytail: PWA must keep PWA_VIEWS = search/guide/about only.
 * Run: npx tsx client/scripts/pwa-maintainer-views-self-check.ts
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const src = fs.readFileSync(path.join(root, 'src/query-tabs/useQueryTabs.ts'), 'utf8');

const match = src.match(/const PWA_VIEWS = new Set\(\[([^\]]+)\]\)/);
if (!match) {
  console.error('pwa-maintainer-views-self-check: PWA_VIEWS not found');
  process.exit(1);
}

const members = match[1];
for (const forbidden of ['RELATION', 'CORRECTIONS']) {
  if (members.includes(`VIEW.${forbidden}`)) {
    console.error(`pwa-maintainer-views-self-check: PWA_VIEWS must not include VIEW.${forbidden}`);
    process.exit(1);
  }
}
for (const required of ['SEARCH', 'GUIDE', 'ABOUT']) {
  if (!members.includes(`VIEW.${required}`)) {
    console.error(`pwa-maintainer-views-self-check: PWA_VIEWS missing VIEW.${required}`);
    process.exit(1);
  }
}

if (!src.includes('if (isPortableHost()) return state')) {
  console.error('pwa-maintainer-views-self-check: sanitize must skip filter on portable host');
  process.exit(1);
}

console.log('pwa-maintainer-views-self-check: ok');
