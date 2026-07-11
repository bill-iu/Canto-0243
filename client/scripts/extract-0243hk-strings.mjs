import fs from 'node:fs';

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const js = fs.readFileSync(path.join(repo, '.tmp-0243hk-main.js'), 'utf8');
const urls = [...js.matchAll(/https?:\/\/[^"'`]+/g)].map((m) => m[0]);
const paths = [...js.matchAll(/\/api\/[a-zA-Z0-9_/?=&.-]+/g)].map((m) => m[0]);
const nums = [...js.matchAll(/\b(limit|pageSize|perPage|offset|PAGE)[^,;]{0,60}/gi)].map((m) => m[0]);

console.log('urls', [...new Set(urls)].slice(0, 20));
console.log('paths', [...new Set(paths)].slice(0, 30));
console.log('pagination hints', [...new Set(nums)].slice(0, 30));
const bigNums = [...js.matchAll(/\b(1[0-9]{3}|[5-9][0-9]{2})\b/g)].map((m) => m[0]);
const freq = {};
for (const n of bigNums) freq[n] = (freq[n] || 0) + 1;
console.log('frequent big nums', Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 15));