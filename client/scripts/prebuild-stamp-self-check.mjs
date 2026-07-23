/** Self-check: prebuild stamp skip / force (C5). */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import {
  forceRebuild,
  hashFiles,
  hashText,
  shouldSkip,
  writeStamp,
} from './prebuild-stamp.mjs';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'prebuild-stamp-'));
const a = path.join(tmp, 'a.txt');
const b = path.join(tmp, 'b.txt');
const out = path.join(tmp, 'out.json');
fs.writeFileSync(a, 'one');
fs.writeFileSync(b, 'two');
fs.writeFileSync(out, '{}');

const fp1 = hashFiles([a, b]);
const fp2 = hashFiles([a, b]);
assert.equal(fp1, fp2);
fs.writeFileSync(a, 'changed');
assert.notEqual(fp1, hashFiles([a, b]));

const cache = path.join(tmp, 'cache');
writeStamp(cache, 'demo', fp1);
// fingerprint mismatch → no skip
assert.equal(shouldSkip(cache, 'demo', hashText('other'), [out]), false);
// restore matching stamp
writeStamp(cache, 'demo', hashFiles([a, b]));
assert.equal(shouldSkip(cache, 'demo', hashFiles([a, b]), [out]), true);
assert.equal(shouldSkip(cache, 'demo', hashFiles([a, b]), [path.join(tmp, 'missing')]), false);

if (!forceRebuild()) {
  console.log('✓ prebuild-stamp self-check');
} else {
  console.log('✓ prebuild-stamp self-check (force env set — skip path not asserted)');
}

fs.rmSync(tmp, { recursive: true, force: true });
