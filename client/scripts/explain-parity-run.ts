/**
 * PWA query-explain runner for golden parity (stdin JSON → stdout JSON).
 */
import fs from 'node:fs';

import { explainQuery } from '../src/db/query-explain.ts';

type ExplainCase = { id: number; query: string };

const casesPath = process.argv[2];
if (!casesPath) {
  console.error('usage: explain-parity-run.ts <cases.json>');
  process.exit(2);
}

const cases: ExplainCase[] = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
const out: Array<{
  id: number;
  summary: string | null;
  warning: string | null;
  kind: string | null;
  error: string | null;
}> = [];

for (const c of cases) {
  try {
    const result = explainQuery(c.query);
    out.push({
      id: c.id,
      summary: result.summary,
      warning: result.warning,
      kind: result.kind,
      error: null,
    });
  } catch (e) {
    out.push({
      id: c.id,
      summary: null,
      warning: null,
      kind: null,
      error: e instanceof Error ? e.message : String(e),
    });
  }
}

process.stdout.write(JSON.stringify(out));
