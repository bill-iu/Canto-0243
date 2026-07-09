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

async function nextWordId(db: DatabaseBackend): Promise<number> {
  const stmt = await db.prepare('SELECT COALESCE(MAX(id), 0) + 1 AS n FROM words');
  await stmt.bind([]);
  const ok = await stmt.step();
  const n = ok ? Number((await stmt.getAsObject()).n ?? 1) : 1;
  await stmt.free();
  return Number.isFinite(n) ? n : 1;
}

async function charHasFinal(db: DatabaseBackend, char: string, final: string): Promise<boolean> {
  const stmt = await db.prepare('SELECT finals FROM words WHERE char = ?');
  await stmt.bind([char]);
  while (await stmt.step()) {
    const raw = String((await stmt.getAsObject()).finals ?? '');
    if (raw.includes(`"${final}"`) || raw.includes(final)) {
      await stmt.free();
      return true;
    }
  }
  await stmt.free();
  return false;
}

async function hasColumn(db: DatabaseBackend, column: string): Promise<boolean> {
  const stmt = await db.prepare('PRAGMA table_info(words)');
  await stmt.bind([]);
  while (await stmt.step()) {
    const row = await stmt.getAsObject();
    if (String(row.name ?? '') === column) {
      await stmt.free();
      return true;
    }
  }
  await stmt.free();
  return false;
}

async function insertWordRow(db: DatabaseBackend, seed: WordSeed): Promise<void> {
  const exists = await db.prepare('SELECT 1 FROM words WHERE char = ? AND jyutping = ? LIMIT 1');
  await exists.bind([seed.char, seed.jyutping]);
  const found = await exists.step();
  await exists.free();
  if (found) {
    return;
  }
  const [initials, finals, tones] = splitJyutping(seed.jyutping);
  const id = await nextWordId(db);
  const hasTones = await hasColumn(db, 'tones');
  const sql =
    hasTones
      ? 'INSERT INTO words (id, char, code, jyutping, initials, finals, tones, length) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
      : 'INSERT INTO words (id, char, code, jyutping, initials, finals, length) VALUES (?, ?, ?, ?, ?, ?, ?)';
  const ins = await db.prepare(sql);
  const bindValues = hasTones
    ? [id, seed.char, seed.code, seed.jyutping, JSON.stringify(initials), JSON.stringify(finals), JSON.stringify(tones), [...seed.char].length]
    : [id, seed.char, seed.code, seed.jyutping, JSON.stringify(initials), JSON.stringify(finals), [...seed.char].length];
  await ins.bind(bindValues);
  await ins.step();
  await ins.free();
}

/** Port of scripts/patch_lou_dou_readings.py */
export async function patchLouDouReadings(db: DatabaseBackend): Promise<number> {
  const sel = await db.prepare(
    "SELECT id, char, code, jyutping FROM words WHERE char LIKE '%潦倒' AND length(char) >= 3",
  );
  await sel.bind([]);
  const updates: Array<{ id: number; jyutping: string; code: string; initials: string; finals: string; tones?: string }> =
    [];
  while (await sel.step()) {
    const row = await sel.getAsObject();
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
  await sel.free();
  const hasTones = updates.length > 0 ? await hasColumn(db, 'tones') : false;
  if (hasTones) {
    const upd = await db.prepare(
      'UPDATE words SET jyutping = ?, code = ?, initials = ?, finals = ?, tones = ? WHERE id = ?',
    );
    for (const u of updates) {
      const row = u as { id: number; jyutping: string; code: string; initials: string; finals: string; tones: string };
      await upd.bind([row.jyutping, row.code, row.initials, row.finals, row.tones, row.id]);
      await upd.step();
      await upd.reset();
    }
    await upd.free();
  }
  return updates.length;
}

async function ensureLiaoLouReadings(db: DatabaseBackend): Promise<void> {
  if (await charHasFinal(db, '潦', 'ou')) {
    return;
  }
  for (const seed of LIAO_EXTRA_READINGS) {
    await insertWordRow(db, seed);
  }
}

export async function ensureConnectiveCompoundRows(db: DatabaseBackend): Promise<void> {
  for (const seed of CONNECTIVE_SEEDS) {
    await insertWordRow(db, seed);
  }
}

/** First single-char reading in words table (for 音節拼接). */
async function firstSingleCharReading(
  db: DatabaseBackend,
  char: string,
): Promise<{ jyutping: string; code: string } | null> {
  const stmt = await db.prepare(
    `SELECT jyutping, code FROM words
     WHERE char = ?
       AND (length = 1 OR ((length IS NULL OR length = 0) AND length(char) = 1))
     LIMIT 5`,
  );
  await stmt.bind([char]);
  let best: { jyutping: string; code: string } | null = null;
  while (await stmt.step()) {
    const row = await stmt.getAsObject();
    const jyutping = String(row.jyutping ?? '').trim();
    const code = String(row.code ?? '').trim();
    if (jyutping) {
      best = { jyutping, code: code || '0' };
      break;
    }
  }
  await stmt.free();
  return best;
}

/**
 * Ensure multi-char row exists via syllable compose from single-char readings.
 * Returns false if any char lacks a reading (skip synthetic).
 */
export async function ensureComposedWordRow(
  db: DatabaseBackend,
  text: string,
): Promise<boolean> {
  const chars = [...text];
  if (chars.length < 2) return false;
  const exists = await db.prepare('SELECT 1 FROM words WHERE char = ? LIMIT 1');
  await exists.bind([text]);
  const found = await exists.step();
  await exists.free();
  if (found) return true;

  const parts: string[] = [];
  const codes: string[] = [];
  for (const ch of chars) {
    const r = await firstSingleCharReading(db, ch);
    if (!r) return false;
    parts.push(r.jyutping);
    codes.push(r.code || '0');
  }
  await insertWordRow(db, {
    char: text,
    jyutping: parts.join(' '),
    code: codes.join(''),
  });
  return true;
}

/** Call once after opening lexicon (browser + parity runners). */
export async function applyRuntimeDbPatches(db: DatabaseBackend): Promise<{ louDou: number }> {
  const louDou = await patchLouDouReadings(db);
  await ensureLiaoLouReadings(db);
  await ensureConnectiveCompoundRows(db);
  return { louDou };
}

/** ponytail: runnable self-check — bundled in guide-examples-self-check */
export async function dbPatchSelfCheck(db: DatabaseBackend): Promise<void> {
  await applyRuntimeDbPatches(db);
  if (!(await charHasFinal(db, '潦', 'ou'))) {
    throw new Error('dbPatchSelfCheck: 潦 missing ou final');
  }
  const stmt = await db.prepare('SELECT 1 FROM words WHERE char = ? LIMIT 1');
  await stmt.bind(['生與死']);
  const ok = await stmt.step();
  await stmt.free();
  if (!ok) {
    throw new Error('dbPatchSelfCheck: 生與死 missing');
  }
}
