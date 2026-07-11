import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const file = process.argv[2] || '.tmp-c22.js';
const js = fs.readFileSync(path.join(repo, file), 'utf8');

const patterns = process.argv.slice(3).length ? process.argv.slice(3) : ['page_size', 'pageSize', 'cls', 'mode=m', 'limit', 'words', 'gap', 'margin', 'flexWrap', 'chip', 'result'];
for (const pat of patterns) {
  let idx = 0;
  let n = 0;
  while ((idx = js.indexOf(pat, idx)) >= 0 && n < 3) {
    console.log(`${pat}@${idx}:`, js.slice(Math.max(0, idx - 30), idx + 100).replace(/\s+/g, ' '));
    idx += pat.length;
    n++;
  }
  if (n === 0) console.log(pat, '—');
}