/** Self-check: warmGuideProbeReadiness on fixture db (CONTEXT § 探針暖機). */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import {
  resetGuideProbeReadinessForTests,
  warmGuideProbeReadiness,
} from '../src/probe-readiness.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'tests/fixtures/lyrics.db');
if (!fs.existsSync(dbPath)) {
  throw new Error(`missing fixture db: ${dbPath}`);
}

resetGuideProbeReadinessForTests();
resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);
await db.close();
console.log('guide-probe-readiness-self-check: ok');