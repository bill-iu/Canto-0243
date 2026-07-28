/** Guard the canonical compiler seam from accidental registry/fallback drift. */
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();

function read(relative: string): string {
  return fs.readFileSync(path.join(root, relative), 'utf8');
}

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`canonical architecture self-check: ${message}`);
}

assert(
  !read('src/db/position-match/compiler.ts').includes('match-spec-registry'),
  'compiler must not fall back to the legacy registry',
);
for (const relative of [
  'src/db/query/dispatch.ts',
  'src/db/query/mask-family-executor.ts',
  'src/db/query-explain-ir.ts',
  'src/db/query-explain.ts',
]) {
  assert(!read(relative).includes('match-spec-registry'), `${relative} still imports registry`);
}
for (const relative of ['src/workbench/plan-replacements.ts']) {
  assert(!read(relative).includes('workbench_full_bucket_scan'), `${relative} mutates legacy scope flag`);
}
const engine = read('src/db/position-match/engine.ts');
assert(!engine.includes('canonicalMatchSpecToLegacy'), 'canonical execution converts back to legacy');
const canonicalEntry = engine.slice(engine.indexOf('export async function executeCanonicalMatchSpecPage'));
assert(!canonicalEntry.includes('executeMatchSpecPage('), 'canonical entry delegates to legacy execution');

console.log('canonical architecture self-check: ok');
