import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { applyRuntimeDbPatches } from '../src/db/db-patch.ts';
import { injectDatabaseForTests, resetDatabase } from '../src/db/init.ts';
import { openSqlJsDatabase } from '../src/db/sqljs-backend.ts';
import { queryFirst, queryRows } from '../src/db/database-backend.ts';
import { warmGuideProbeReadiness } from '../src/probe-readiness.node.ts';
import { getWordText, getWordParts } from '../src/db/position-match/word-row.ts';
import { rhymeFinalsFromJyutping } from '../src/db/jyutping-codec.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dbPath = path.join(repoRoot, 'lyrics.db');
resetDatabase();
const db = await openSqlJsDatabase(new Uint8Array(fs.readFileSync(dbPath)));
injectDatabaseForTests(db);
await applyRuntimeDbPatches(db);
await warmGuideProbeReadiness(repoRoot);

const lit = '困潦倒';
const exact = await queryRows(db, 'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ? LIMIT 5', [lit]);
console.log('exact', exact);
const like = await queryRows(db, 'SELECT char, jyutping, finals, length FROM words WHERE char LIKE ? LIMIT 20', ['%'+lit]);
console.log('like count', like.length, like.slice(0,10).map(r => ({c:r.char, f:r.finals, j:r.jyutping})));

// sample 4-char words ending with something related
const sample = await queryRows(db, \"SELECT char, jyutping, finals FROM words WHERE length=4 AND char LIKE '%潦倒' LIMIT 10\", []);
console.log('len4 *潦倒', sample);

// Check finals column format
const row = await queryFirst(db, 'SELECT char, jyutping, initials, finals FROM words WHERE char LIKE ? LIMIT 1', ['%困潦倒']);
console.log('sample row', row);

await db.close();
