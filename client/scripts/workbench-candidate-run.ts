import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { loadRankingData } from '../src/db/ranking-loader.node.ts';
import { loadRhymeLetterData } from '../src/db/rime-index-loader.node.ts';
import { parseReplacementPlanV1 } from '../src/workbench/contracts.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(repoRoot);
loadRhymeLetterData(repoRoot);

const dbPath = process.argv[2];
const casesPath = process.argv[3];
if (!dbPath || !casesPath) throw new Error('usage: workbench-candidate-run <db> <cases.json>');

const initSqlJs = (await import('../src/db/sqljs.ts')).initSqlJs;
const { createSqlJsBackend } = await import('../src/db/sqljs-backend.ts');
const { planPwaReplacements } = await import('../src/workbench/pwa-replacement-planner.ts');
const SQL = await initSqlJs();
const db = createSqlJsBackend(new SQL.Database(fs.readFileSync(dbPath)));
const cases = JSON.parse(fs.readFileSync(casesPath, 'utf8')) as Array<{ id: number; plan: unknown }>;
const output = [];
for (const item of cases) {
  output.push({ id: item.id, response: await planPwaReplacements(parseReplacementPlanV1(item.plan), db) });
}
console.log(JSON.stringify(output));
