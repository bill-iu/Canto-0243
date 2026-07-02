/**
 * PWA query-engine runner for golden parity (stdin JSON → stdout JSON).
 * ponytail: probe-only; uses injectDatabaseForTests — not for production UI.
 *
 * Bundled before run (see scripts/pwa_golden_parity.py).
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadStaticRelationData } from '../src/db/thesaurus-loader.node.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';

type ParityCase = { id: number; query: string; mode: string };

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);
loadStaticRelationData(repoRoot);
loadRhymeLetterData(repoRoot);

const dbPath = process.argv[2];
const casesPath = process.argv[3];
if (!dbPath || !casesPath) {
  console.error('usage: golden-parity-run.ts <db-path> <cases.json>');
  process.exit(2);
}

const cases: ParityCase[] = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
const buf = fs.readFileSync(dbPath);

const initSqlJs = (await import('../src/db/sqljs.ts')).initSqlJs;
const SQL = await initSqlJs();
const db = new SQL.Database(buf);

const { injectDatabaseForTests } = await import('../src/db/init.ts');
injectDatabaseForTests(db);

const { queryEngine, normalizeAndParse } = await import('../src/db/query-engine.ts');

const out: Array<{
  id: number;
  kind: string;
  chars: string[];
  hint: string | null;
  error: string | null;
}> = [];

for (const c of cases) {
  try {
    const parsed = normalizeAndParse(c.query);
    const result = await queryEngine.execute({
      q: c.query,
      mode: c.mode as 'm1' | 'm2' | 'syn',
      limit: 10,
      offset: 0,
    });
    const chars = result.items
      .map((r) => r.word)
      .filter((w): w is string => Boolean(w));
    out.push({
      id: c.id,
      kind: String(parsed.kind),
      chars,
      hint: result.hint ?? null,
      error: null,
    });
  } catch (e) {
    out.push({
      id: c.id,
      kind: '',
      chars: [],
      hint: null,
      error: e instanceof Error ? e.message : String(e),
    });
  }
}

process.stdout.write(JSON.stringify(out));
