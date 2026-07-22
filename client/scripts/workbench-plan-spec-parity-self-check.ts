/**
 * L1 MatchSpec + L3 relaxation ids + L2 group literals vs contracts/workbench-plan-spec-cases.json
 */
import fs from 'node:fs';
import path from 'node:path';

import { buildMatchSpec, matchSpecToCanonical } from '../src/workbench/build-match-spec.ts';
import { parseReplacementPlanV1 } from '../src/workbench/contracts.ts';
import { groupCandidates, groupLiterals } from '../src/workbench/group-candidates.ts';
import { relaxationIds } from '../src/workbench/relaxation-advisor.ts';

function findCasesPath(): string {
  let dir = process.cwd();
  for (let i = 0; i < 6; i += 1) {
    const candidate = path.join(dir, 'contracts', 'workbench-plan-spec-cases.json');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error('contracts/workbench-plan-spec-cases.json not found from cwd');
}

const casesPath = findCasesPath();

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench plan-spec parity: ${message}`);
}

function deepEqual(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

const doc = JSON.parse(fs.readFileSync(casesPath, 'utf8')) as {
  cases: Array<{
    id: string;
    plan: unknown;
    matchSpec: unknown;
    relaxationIds: string[];
  }>;
  groupCases: Array<{
    id: string;
    plan: unknown;
    rows: Array<{ char: string; jyutping: string; code: string }>;
    pool: { syns: Array<{ char: string; source?: string }>; semantic: Array<{ char: string; source?: string }> };
    literals: Record<string, string[]>;
  }>;
};

for (const item of doc.cases) {
  const plan = parseReplacementPlanV1(item.plan);
  const got = matchSpecToCanonical(buildMatchSpec(plan));
  assert(deepEqual(got, item.matchSpec), `${item.id} MatchSpec\n got ${JSON.stringify(got)}\n exp ${JSON.stringify(item.matchSpec)}`);
  const ids = relaxationIds(plan);
  assert(deepEqual(ids, item.relaxationIds), `${item.id} relaxationIds got ${JSON.stringify(ids)}`);
}

for (const item of doc.groupCases) {
  const plan = parseReplacementPlanV1(item.plan);
  const rows = item.rows.map((r) => ({ char: r.char, jyutping: r.jyutping, code: r.code }));
  const pool = {
    syns: item.pool.syns.map((r) => ({ char: r.char, source: r.source })),
    semantic: item.pool.semantic.map((r) => ({ char: r.char, source: r.source })),
    antonyms: [] as Array<{ char: string }>,
  };
  // RelationPoolSnapshot may need more fields — cast via groupCandidates null-safe path
  const groups = groupCandidates(plan, rows as any, pool as any);
  const got = groupLiterals(groups);
  assert(deepEqual(got, item.literals), `${item.id} group literals got ${JSON.stringify(got)}`);
}

console.log(`workbench-plan-spec-parity-self-check: ok (${doc.cases.length} L1/L3, ${doc.groupCases.length} L2)`);
