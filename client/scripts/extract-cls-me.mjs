import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const js = fs.readFileSync(path.join(repo, '.tmp-c10.js'), 'utf8');

const needles = [
  'function me(',
  'function he(',
  'function ke(',
  'function ye(',
  'resultsCount',
  'shuffleResults',
  'Promise.all([me',
  'nums:',
  'results:',
  'flexWrap',
  'gap:',
  'gridGap',
  'Chip',
  'wordChip',
  'resultChip',
];

for (const needle of needles) {
  let idx = 0;
  let count = 0;
  while ((idx = js.indexOf(needle, idx)) !== -1 && count < 3) {
    const start = Math.max(0, idx - 80);
    const end = Math.min(js.length, idx + 400);
    console.log(`\n--- ${needle} @${idx} ---`);
    console.log(js.slice(start, end).replace(/\n/g, ' '));
    idx += needle.length;
    count++;
  }
}