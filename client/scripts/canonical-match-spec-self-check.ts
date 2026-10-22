/** Canonical legacy adapter parity against contracts/match-spec-cases.json. */
import fs from 'node:fs';
import path from 'node:path';

import { normalizeAndParse, queryEngine } from '../src/db/query-engine.ts';
import { injectDatabaseForTests } from '../src/db/init.ts';
import { encodePhonemeList } from '../src/db/phoneme-codec.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import {
  canonicalMatchSpecToJson,
  finalizeCanonicalMatchSpec,
} from '../src/db/position-match/canonical.ts';
import { compileParsedQuery } from '../src/db/position-match/compiler.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';

function findCasesPath(): string {
  let dir = process.cwd();
  for (let i = 0; i < 6; i += 1) {
    const candidate = path.join(dir, 'contracts', 'match-spec-cases.json');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error('contracts/match-spec-cases.json not found from cwd');
}

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`canonical MatchSpec self-check: ${message}`);
}

function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

const doc = JSON.parse(fs.readFileSync(findCasesPath(), 'utf8')) as {
  cases: Array<{ id: string; query: string; mode: string; expected: unknown }>;
};

const repoRoot = path.resolve(path.dirname(findCasesPath()), '..');
loadRhymeLetterData(repoRoot);

for (const item of doc.cases) {
  const parsed = normalizeAndParse(item.query, { mode: item.mode });
  const got = canonicalMatchSpecToJson(compileParsedQuery(parsed));
  assert(
    deepEqual(got, item.expected),
    `${item.id}: got ${JSON.stringify(got)} expected ${JSON.stringify(item.expected)}`,
  );
}

let lookupRejected = false;
try {
  compileParsedQuery(normalizeAndParse('香港'));
} catch {
  lookupRejected = true;
}
assert(lookupRejected, 'pure Han lookup must not enter MatchSpec compiler');

let conflictingSlotRejected = false;
try {
  finalizeCanonicalMatchSpec({
    width: 1,
    slots: [
      { pos: 0, kind: 'code_digit', value: '2' },
      { pos: 0, kind: 'code_digit', value: '3' },
    ],
  });
} catch {
  conflictingSlotRejected = true;
}
assert(conflictingSlotRejected, 'same-position same-kind conflicting slots must be rejected');

const projected = finalizeCanonicalMatchSpec({
  width: 2,
  slots: [{ pos: 1, kind: 'code_digit', value: '0' }],
  mask: '門0',
});
assert(projected.mask === '門0', 'mask projection must preserve owned tokens');
assert(
  projected.slots.some(
    (slot) => slot.kind === 'literal_char' && slot.value === '門' && slot.mask_token === '門',
  ),
  'literal mask token must be owned by a canonical slot',
);

let unownedMaskDigitRejected = false;
try {
  finalizeCanonicalMatchSpec({
    width: 1,
    slots: [{ pos: 0, kind: 'code_digit', value: '2' }],
    mask: '3',
  });
} catch {
  unownedMaskDigitRejected = true;
}
assert(unownedMaskDigitRejected, 'mask digit without a matching slot must be rejected');

const SQL = await initSqlJs();
const native = new SQL.Database();
native.run('CREATE TABLE words (char TEXT, jyutping TEXT, code TEXT, initials TEXT, finals TEXT, length INTEGER)');
for (const [char, jyutping, code, initials, finals] of [
  ['墨', 'mak6', '2', ['m'], ['ak']],
  ['黑客', 'hak1 haak3', '34', ['h', 'h'], ['ak', 'aak']],
  ['麥片', 'mak6 pin3', '24', ['m', 'p'], ['ak', 'in']],
  ['黑雨', 'hak1 jyu5', '35', ['h', 'j'], ['ak', 'yu']],
  ['麥粉', 'mak6 fan2', '29', ['m', 'f'], ['ak', 'an']],
  ['拍攝', 'paak3 sip3', '44', ['p', 's'], ['aak', 'ip']],
] as const) {
  native.run('INSERT INTO words VALUES (?, ?, ?, ?, ?, ?)', [
    char, jyutping, code, encodePhonemeList([...initials], 'initial'),
    encodePhonemeList([...finals], 'final'), [...char].length,
  ]);
}
const db = createSqlJsBackend(native);
injectDatabaseForTests(db);
try {
  for (const mode of ['m1', 'm2', 'm3']) {
    const result = await queryEngine.execute({ q: '墨=4', mode, limit: 100, offset: 0 });
    const expected = ['黑客', '麥片', ...(mode === 'm3' ? [] : ['黑雨'])].sort();
    assert(
      deepEqual(result.items.map((row) => row.word).sort(), expected),
      `墨=4 (${mode}): must ignore anchor tone and enforce the second-position code`,
    );
  }
} finally {
  injectDatabaseForTests(null);
  await db.close();
}

console.log(`canonical MatchSpec self-check: ok (${doc.cases.length} cases)`);
