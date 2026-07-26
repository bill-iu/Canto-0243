/** Canonical legacy adapter parity against contracts/match-spec-cases.json. */
import fs from 'node:fs';
import path from 'node:path';

import { normalizeAndParse } from '../src/db/query-engine.ts';
import { canonicalMatchSpecToJson } from '../src/db/position-match/canonical.ts';
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

console.log(`canonical MatchSpec self-check: ok (${doc.cases.length} cases)`);
