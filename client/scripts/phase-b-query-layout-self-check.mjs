/** Phase B PR2 layout — plain node, no tsx. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const db = path.join(root, 'src', 'db');
const queryDir = path.join(db, 'query');
const required = ['parse.ts', 'mode-dispatch.ts', 'dispatch.ts', 'engine.ts'];

function fail(msg) {
  console.error(`phase-b-query-layout: ${msg}`);
  process.exit(1);
}

if (!fs.existsSync(queryDir)) fail('missing client/src/db/query/');
for (const name of required) {
  if (!fs.existsSync(path.join(queryDir, name))) fail(`missing query/${name}`);
}
const facade = fs.readFileSync(path.join(db, 'query-engine.ts'), 'utf8');
if (!facade.includes('./query/')) fail('query-engine.ts must re-export from ./query/*');
if (!facade.includes('searchWords')) fail('facade must export searchWords');
const modeSrc = fs.readFileSync(path.join(queryDir, 'mode-dispatch.ts'), 'utf8');
if (!modeSrc.includes('dispatchParsed')) fail('mode-dispatch must call dispatchParsed');
if (modeSrc.includes('._dispatch')) fail('mode-dispatch must not call private _dispatch');
console.log('phase-b-query-layout: OK');
