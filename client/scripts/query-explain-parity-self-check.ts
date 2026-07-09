/**
 * Phase D: load contracts/query-explain-parity.json and assert local explainQuery.
 * Run: npx tsx scripts/query-explain-parity-self-check.ts  (cwd: client/)
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { explainQuery } from '../src/db/query-explain.ts';

type ParityCase = {
  q: string;
  kind?: string | null;
  summary_contains?: string[];
  summary_not_contains?: string[];
  warning_contains?: string[];
  summary_eq?: string;
  warning_eq?: string | null;
};

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const contractPath = path.join(repoRoot, 'contracts/query-explain-parity.json');
if (!fs.existsSync(contractPath)) {
  throw new Error(`query-explain-parity: missing ${contractPath}`);
}

const data = JSON.parse(fs.readFileSync(contractPath, 'utf8')) as { cases?: ParityCase[] };
const cases = data.cases ?? [];
if (!cases.length) {
  throw new Error('query-explain-parity: empty cases');
}

for (const c of cases) {
  const r = explainQuery(c.q);
  const summary = r.summary ?? '';
  const warning = r.warning ?? '';
  if (c.kind != null && r.kind !== c.kind) {
    throw new Error(`query-explain-parity: ${c.q} kind ${r.kind} != ${c.kind}`);
  }
  for (const needle of c.summary_contains ?? []) {
    if (!summary.includes(needle)) {
      throw new Error(`query-explain-parity: ${c.q} summary missing ${needle}: ${summary}`);
    }
  }
  for (const needle of c.summary_not_contains ?? []) {
    if (summary.includes(needle)) {
      throw new Error(`query-explain-parity: ${c.q} summary must not contain ${needle}: ${summary}`);
    }
  }
  for (const needle of c.warning_contains ?? []) {
    if (!warning.includes(needle)) {
      throw new Error(`query-explain-parity: ${c.q} warning missing ${needle}: ${warning}`);
    }
  }
  if (c.summary_eq !== undefined && summary !== c.summary_eq) {
    throw new Error(`query-explain-parity: ${c.q} summary_eq`);
  }
  if (c.warning_eq !== undefined && warning !== (c.warning_eq ?? '')) {
    throw new Error(`query-explain-parity: ${c.q} warning_eq`);
  }
}

console.log(`query-explain-parity ok (${cases.length} cases)`);
