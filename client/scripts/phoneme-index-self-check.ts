/**
 * P1: phoneme inverted index — parity with unlimited SQL + rebuild-once.
 * Run: node --import tsx client/scripts/phoneme-index-self-check.ts
 * (or npx tsx from client/)
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import {
  ensurePhonemeIndex,
  getPhonemeAnchorCandidates,
  isPhonemeIndexReady,
} from '../src/db/position-match/phoneme-index.ts';
import { getCandidatesForLength } from '../src/db/position-match/sources.ts';
import { getWordText } from '../src/db/position-match/word-row.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { initSqlJs } from '../src/db/sqljs.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRhymeLetterData(repoRoot);

const fixture = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (!fs.existsSync(fixture)) {
  throw new Error(`phoneme-index-self-check: missing ${fixture}`);
}

const SQL = await initSqlJs();
const native = new SQL.Database(fs.readFileSync(fixture));
const db = createSqlJsBackend(native);
injectDatabaseForTests(db);

function charSet(rows: { char?: unknown }[]): Set<string> {
  return new Set(rows.map((r) => getWordText(r)).filter(Boolean));
}

const [unlimitedRows] = await getCandidatesForLength(db, 2, { unlimited: true });
const width2 = unlimitedRows.filter((r) => getWordText(r).length === 2);
if (!width2.length) {
  throw new Error('phoneme-index-self-check: no width-2 rows in fixture');
}

// Prefer an anchor with non-empty final options (e.g. 不 may rank-filter to empty).
let anchorChar = '';
let anchorPos = 0;
let indexed: Awaited<ReturnType<typeof getPhonemeAnchorCandidates>> = null;
for (const sample of width2) {
  const text = getWordText(sample);
  for (let pos = 0; pos < text.length; pos++) {
    const ch = text[pos]!;
    const hit = await getPhonemeAnchorCandidates(db, 2, pos, ch, 'final');
    if (hit && hit.length > 0) {
      anchorChar = ch;
      anchorPos = pos;
      indexed = hit;
      break;
    }
  }
  if (indexed?.length) break;
}
if (!indexed?.length || !anchorChar) {
  throw new Error('phoneme-index-self-check: no non-empty final-anchor hits in fixture');
}

await ensurePhonemeIndex(db);
if (!isPhonemeIndexReady(db)) {
  throw new Error('phoneme-index-self-check: index not ready after ensure');
}

for (const row of indexed) {
  if (getWordText(row).length !== 2) {
    throw new Error(`phoneme-index-self-check: bad width ${getWordText(row)}`);
  }
}

// Rebuild-once: second ensure stays ready
await ensurePhonemeIndex(db);
if (!isPhonemeIndexReady(db)) {
  throw new Error('phoneme-index-self-check: lost ready on second ensure');
}

// Invalidate on inject
injectDatabaseForTests(db);
if (isPhonemeIndexReady(db)) {
  throw new Error('phoneme-index-self-check: expected invalidate after inject');
}

await ensurePhonemeIndex(db);
const indexed2 = await getPhonemeAnchorCandidates(db, 2, anchorPos, anchorChar, 'final');
const a = [...charSet(indexed)].sort().join(',');
const b = [...charSet(indexed2 ?? [])].sort().join(',');
if (a !== b) {
  throw new Error(`phoneme-index-self-check: rebuild drift ${a} vs ${b}`);
}

// Indexed length-2 universe size must not exceed unlimited length-2 scan
if (indexed.length > unlimitedRows.length + 5) {
  throw new Error(
    `phoneme-index-self-check: indexed ${indexed.length} > unlimited ${unlimitedRows.length}`,
  );
}

// Every indexed char must be a length-2 word present in unlimited scan
const unlimitedSet = charSet(unlimitedRows);
for (const ch of charSet(indexed)) {
  if (!unlimitedSet.has(ch)) {
    throw new Error(`phoneme-index-self-check: ${ch} not in unlimited bucket`);
  }
}

if (indexed.length < 1) {
  throw new Error('phoneme-index-self-check: expected non-empty indexed set');
}

resetDatabase();
console.log(
  `phoneme-index-self-check ok (anchor=${anchorChar}@${anchorPos}, indexed=${indexed.length}, unlimited=${unlimitedRows.length})`,
);
