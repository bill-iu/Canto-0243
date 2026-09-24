import assert from 'node:assert/strict';
import { initSqlJs } from '../src/db/sqljs.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests } from '../src/db/init.ts';
import { queryEngine } from '../src/db/query-engine.ts';
import { initRhymeLetterIndex } from '../src/db/rime-index.ts';
import { encodePhonemeList } from '../src/db/phoneme-codec.ts';
import { invalidatePhonemeIndex } from '../src/db/position-match/phoneme-index.ts';
import { clearAnchorPhonemeOptionsCache } from '../src/db/position-match/filters/f2-phoneme-anchor.ts';
import { executeCanonicalMatchSpecPage } from '../src/db/position-match/engine.ts';
import { finalizeCanonicalMatchSpec } from '../src/db/position-match/canonical.ts';
import { buildReplacementSnapshot } from '../src/workbench/plan-replacements.ts';
import type { ReplacementPlanV1 } from '../src/workbench/contracts.ts';
import type { DatabaseBackend } from '../src/db/database-backend.ts';

const SQL = await initSqlJs();
const native = new SQL.Database();
native.run('CREATE TABLE words (char TEXT, jyutping TEXT, code TEXT, initials TEXT, finals TEXT, length INTEGER)');
for (const [char, jyutping, code, initials, finals] of [
  ['海', 'hoi2', '9', ['h'], ['oi']], ['開', 'hoi1', '3', ['h'], ['oi']],
  ['灰', 'fui1', '3', ['f'], ['ui']], ['海海', 'hoi2 hoi2', '99', ['h', 'h'], ['oi', 'oi']],
  ['灰灰', 'fui1 fui1', '33', ['f', 'f'], ['ui', 'ui']],
] as const) {
  native.run('INSERT INTO words VALUES (?, ?, ?, ?, ?, ?)',
    [char, jyutping, code, encodePhonemeList([...initials], 'initial'), encodePhonemeList([...finals], 'final'), [...char].length]);
}
const db = createSqlJsBackend(native);
initRhymeLetterIndex({ finalOptions: { oi: ['oi'] }, completeSyllables: ['hoi', 'fui'] });

// Async SQL forces requests to interleave while their execution is in flight. This
// fails with the old mutable profile even if obsolete UI results are discarded.
const delayed: DatabaseBackend = {
  ...db,
  async prepare(sql) {
    await new Promise((resolve) => setTimeout(resolve, 0));
    return db.prepare(sql);
  },
};
injectDatabaseForTests(delayed);
const run = (q: string, rhyme_profile: string) => queryEngine.execute({
  q, mode: 'm1', limit: 100, offset: 0, rhyme_profile,
});
for (const query of ['海=', '3oi']) {
  const exact = await run(query, 'exact');
  const loose = await run(query, 'tong');
  const exactWord = '開';
  const looseWord = '灰';
  assert(exact.items.some((row) => row.word === exactWord), `${query}: missing exact result`);
  assert(!exact.items.some((row) => row.word === looseWord));
  assert(loose.items.some((row) => row.word === looseWord), `${query} must have a loose-only result`);
  for (const profiles of [['exact', 'tong'], ['tong', 'exact']] as const) {
    invalidatePhonemeIndex();
    clearAnchorPhonemeOptionsCache();
    const pending = profiles.map((profile) => run(query, profile));
    const results = await Promise.all(pending);
    results.forEach((result, i) => assert.deepEqual(result, profiles[i] === 'exact' ? exact : loose));
  }
}

// Multi-anchor prefilter must expand too, before the final per-position checks.
const spec = finalizeCanonicalMatchSpec({ width: 2, slots: [
  { pos: 0, kind: 'final_anchor', value: '海' }, { pos: 1, kind: 'final_anchor', value: '海' },
] });
const context = { db: delayed, mode: 'm1', limit: 100, offset: 0 };
const exact = await executeCanonicalMatchSpecPage(spec, { ...context, rhymeProfile: 'exact' });
const loose = await executeCanonicalMatchSpecPage(spec, { ...context, rhymeProfile: 'tong' });
assert(!exact.rows.some((row) => row.char === '灰灰'));
assert(loose.rows.some((row) => row.char === '灰灰'));

const plan: ReplacementPlanV1 = { version: 1, selectionVersion: 1, width: 2, mode: 'm1',
  slots: [{ pos: 0, kind: 'final_anchor', ref: '海' }, { pos: 1, kind: 'final_anchor', ref: '海' }],
  semanticIntent: 'off', limit: 100 };
const [workExact, workLoose] = await Promise.all(['exact', 'tong'].map((rhymeProfile) =>
  buildReplacementSnapshot({ ...plan, rhymeProfile: rhymeProfile as 'exact' | 'tong' }, delayed)));
assert(!workExact!.candidates.some((item) => item.startsWith('灰灰\0')));
assert(workLoose!.candidates.some((item) => item.startsWith('灰灰\0')));
const beforeCancel = await run('海=', 'exact');
await assert.rejects(executeCanonicalMatchSpecPage(spec, {
  ...context, shouldCancel: () => true, rhymeProfile: 'tong',
}), { name: 'SearchCancelledError' });
assert.deepEqual(await run('海=', 'exact'), beforeCancel);
await db.close();
console.log('rhyme isolation: overlapping search/workbench, multi-anchor, cancellation ok');
