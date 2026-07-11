import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const js = fs.readFileSync(path.join(repo, '.tmp-c10.js'), 'utf8');

// Extract context around /api/cls
for (const needle of ['/api/cls/', 'cls_filter', 'page_size', 'limit', 'offset', 'm2', 'm1', 'm3', 'm4', 'gap', 'margin', 'Chip', 'chip', 'flexWrap', 'wrap']) {
  let idx = 0;
  let count = 0;
  while ((idx = js.indexOf(needle, idx)) !== -1 && count < 8) {
    const start = Math.max(0, idx - 120);
    const end = Math.min(js.length, idx + 200);
    console.log(`\n--- ${needle} @${idx} ---`);
    console.log(js.slice(start, end).replace(/\n/g, ' '));
    idx += needle.length;
    count++;
  }
}