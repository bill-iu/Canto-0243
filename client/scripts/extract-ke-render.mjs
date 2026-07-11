import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const js = fs.readFileSync(path.join(repo, '.tmp-c10.js'), 'utf8');
const start = js.indexOf('function ke(');
console.log(js.slice(start, start + 2500));