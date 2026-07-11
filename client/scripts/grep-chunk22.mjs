import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const js = fs.readFileSync(path.join(repo, '.tmp-c22.js'), 'utf8');

for (const pat of ['page_size', 'pageSize', 'limit', 'offset', 'cls/', '/api/', 'gap', 'margin', 'flexWrap', 'RESULT', '1000', '500', '300', '200', '150', '100']) {
  const idx = js.indexOf(pat);
  console.log(pat, idx >= 0 ? js.slice(Math.max(0, idx - 40), idx + 80).replace(/\s+/g, ' ') : '—');
}