import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const files = fs.readdirSync(repo).filter((f) => f.startsWith('.tmp-') && f.endsWith('.js'));

const patterns = [
  /\/api\/[a-zA-Z0-9_/?=&.-]+/g,
  /\/cls\/[a-zA-Z0-9_/?=&.-]+/g,
  /mode=m[0-9]/g,
  /page_size[=:][^,;]{0,20}/g,
  /pageSize[=:][^,;]{0,20}/g,
  /limit[=:][^,;]{0,20}/g,
  /gap[=:][^,;]{0,30}/g,
  /flexWrap/g,
  /spacing\([^)]+\)/g,
];

for (const file of files.sort()) {
  const js = fs.readFileSync(path.join(repo, file), 'utf8');
  const hits = new Set();
  for (const pat of patterns) {
    for (const m of js.matchAll(pat)) hits.add(m[0]);
  }
  if (hits.size) {
    console.log(`\n=== ${file} (${(js.length / 1024).toFixed(0)}kb) ===`);
    console.log([...hits].sort().join('\n'));
  }
}