import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { injectDatabaseForTests } from '../src/db/init.ts';
import { queryEngine } from '../src/db/query-engine.ts';
import { runQueryBenchmark } from '../src/db/query-benchmark.ts';
import { warmGuideProbeReadiness } from '../src/probe-readiness.node.ts';
import { queryFirst } from '../src/db/database-backend.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.resolve(process.argv[2] ?? path.join(root, 'tests/fixtures/lyrics.db'));
const output = process.argv[3];
const start = performance.now();
const bytes = fs.readFileSync(dbPath);
const db = await openSqlJsDatabase(bytes);
injectDatabaseForTests(db);
const openMs = performance.now() - start;
try {
  const auxiliaryStart = performance.now();
  await warmGuideProbeReadiness(root);
  const auxiliaryMs = performance.now() - auxiliaryStart;
  const count = await queryFirst(db, 'SELECT COUNT(*) AS n FROM words');
  const samples = await runQueryBenchmark(db, (context) => queryEngine.execute(context), () => process.memoryUsage().heapUsed);
  const result = {
    schemaVersion: 1,
    measuredAt: new Date().toISOString(),
    commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
    workingTreeDirty: Boolean(execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }).trim()),
    environment: { runtime: process.version, platform: process.platform, arch: process.arch,
      cpu: os.cpus()[0]?.model, backend: 'sqljs-node' },
    dataset: { file: path.basename(dbPath), bytes: bytes.length, rows: Number(count?.n ?? 0),
      fixture: dbPath === path.join(root, 'tests/fixtures/lyrics.db') },
    // These are process-local timings; no browser network/cache/OPFS claims.
    openMs, auxiliaryMs, samples,
  };
  const json = JSON.stringify(result, null, 2) + '\n';
  if (output) {
    fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
    fs.writeFileSync(output, json);
  }
  else process.stdout.write(json);
} finally {
  await db.close();
}
