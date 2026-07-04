/**
 * Runtime lexicon patches — parity with app/startup/offline_preload + compound_connect seeds.
 * ponytail: in-memory sql.js only; shipped .db should still be refreshed via copy-db.
 */
import type { DatabaseBackend } from './database-backend.ts';
import { splitJyutping } from './jyutping-codec.ts';

const WRONG_LIU_TAIL = /liu[25] dou2$/;

type WordSeed = {
  char: string;
  jyutping: string;
  code: string;
};

/** 與 Python CONNECTIVE_LITERAL_SEEDS + compose/admission */
const CONNECTIVE_SEEDS: WordSeed[] = [
  { char: '生與死', jyutping: 'saang1 jyu5 sei2', code: '349' },
  { char: '天與地', jyutping: 'tin1 jyu5 dei6', code: '342' },
  { char: '男與女', jyutping: 'naam4 jyu5 neoi5', code: '044' },
  { char: '父與子', jyutping: 'fu6 jyu5 zi2', code: '249' },
];

/** 潦多讀音：public 舊庫可能只得 liu 系，缺 lou 系韻錨 */
const LIAO_EXTRA_READINGS: WordSeed[] = [
  { char: '潦', jyutping: 'lou5', code: '4' },
  { char: '潦', jyutping: 'lou6', code: '2' },
];

function nextWordId(db: DatabaseBackend): number {
  const stmt = db.prepare('SELECT COALESCE(MAX(id), 0) + 1 AS n FROM words');
  stmt.bind([]);
  const ok = stmt.step();
  const n = ok ? Number(stmt.getAsObject().n ?? 1) : 1;
  stmt.free();
  return Number.isFinite(n) ? n : 1;
}

function charHasFinal(db: DatabaseBackend, char: string, final: string): boolean {
  const stmt = db.prepare('SELECT finals FROM words WHERE char = ?');
  stmt.bind([char]);
  while (stmt.step()) {
    const raw = String(stmt.getAsObject().finals ?? '');
    if (raw.includes(`"${final}"`) || raw.includes(final)) {
      stmt.free();
      return true;
    }
  }
  stmt.free();
  return false;
}

function insertWordRow(db: DatabaseBackend, seed: WordSeed): void {
  const exists = db.prepare('SELECT 1 FROM words WHERE char = ? AND jyutping = ? LIMIT 1');
  exists.bind([seed.char, seed.jyutping]);
  const found = exists.step();
  exists.free();
  if (found) {
    return;
  }
  const [initials, finals, tones] = splitJyutping(seed.jyutping);
  const id = nextWordId(db);
  const ins = db.prepare(
    'INSERT INTO words (id, char, code, jyutping, initials, finals, tones, length) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
  );
  ins.bind([
    id,
    seed.char,
    seed.code,
    seed.jyutping,
    JSON.stringify(initials),
    JSON.stringify(finals),
    JSON.stringify(tones),
    [...seed.char].length,
  ]);
  ins.step();
  ins.free();
}

/** Port of scripts/patch_lou_dou_readings.py */
export function patchLouDouReadings(db: DatabaseBackend): number {
  const sel = db.prepare(
    "SELECT id, char, code, jyutping FROM words WHERE char LIKE '%潦倒' AND length(char) >= 3",
  );
  sel.bind([]);
  const updates: Array<{ id: number; jyutping: string; code: string; initials: string; finals: string; tones: string }> =
    [];
  while (sel.step()) {
    const row = sel.getAsObject();
    const jyut = String(row.jyutping ?? '').trim();
    if (!WRONG_LIU_TAIL.test(jyut)) {
      continue;
    }
    const fixed = jyut.replace(WRONG_LIU_TAIL, 'lou5 dou2');
    const [initials, finals, tones] = splitJyutping(fixed);
    const codeDigits = tones.map((t) => (t == null ? '0' : String(t))).join('');
    updates.push({
      id: Number(row.id),
      jyutping: fixed,
      code: codeDigits || String(row.code ?? ''),
      initials: JSON.stringify(initials),
      finals: JSON.stringify(finals),
      tones: JSON.stringify(tones),
    });
  }
  sel.free();
  const upd = db.prepare(
    'UPDATE words SET jyutping = ?, code = ?, initials = ?, finals = ?, tones = ? WHERE id = ?',
  );
  for (const u of updates) {
    upd.bind([u.jyutping, u.code, u.initials, u.finals, u.tones, u.id]);
    upd.step();
    upd.reset();
  }
  upd.free();
  return updates.length;
}

function ensureLiaoLouReadings(db: DatabaseBackend): void {
  if (charHasFinal(db, '潦', 'ou')) {
    return;
  }
  for (const seed of LIAO_EXTRA_READINGS) {
    insertWordRow(db, seed);
  }
}

export function ensureConnectiveCompoundRows(db: DatabaseBackend): void {
  for (const seed of CONNECTIVE_SEEDS) {
    insertWordRow(db, seed);
  }
}

/** Call once after opening lexicon (browser + parity runners). */
export function applyRuntimeDbPatches(db: DatabaseBackend): { louDou: number } {
  const louDou = patchLouDouReadings(db);
  ensureLiaoLouReadings(db);
  ensureConnectiveCompoundRows(db);
  return { louDou };
}

/** ponytail: runnable self-check — bundled in guide-examples-self-check */
export function dbPatchSelfCheck(db: DatabaseBackend): void {
  applyRuntimeDbPatches(db);
  if (!charHasFinal(db, '潦', 'ou')) {
    throw new Error('dbPatchSelfCheck: 潦 missing ou final');
  }
  const stmt = db.prepare('SELECT 1 FROM words WHERE char = ? LIMIT 1');
  stmt.bind(['生與死']);
  const ok = stmt.step();
  stmt.free();
  if (!ok) {
    throw new Error('dbPatchSelfCheck: 生與死 missing');
  }
}