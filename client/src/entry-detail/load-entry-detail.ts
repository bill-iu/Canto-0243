import { buildEntryDetailModel } from '../../../frontend/entry-detail-core.mjs';
import type { EntryDetailModel } from './types.ts';
import { getDatabase, isDatabaseInitialized } from '../db/init.ts';
import { queryRows } from '../db/database-backend.ts';
import { getEssayFrequency, initRankingData } from '../db/ranking.ts';
import { buildRelationPool } from '../db/relation-pool.ts';
import { relationPoolSnapshotItems } from '../db/relation-pool-snapshot.ts';

export type { EntryDetailModel } from './types.ts';

const WORDS_SQL =
  'SELECT char, jyutping, code, initials, finals, length, source_flags FROM words WHERE char = ?';

const fullCache = new Map<string, EntryDetailModel>();

function coreFromRows(text: string, rows: Record<string, unknown>[]): EntryDetailModel | null {
  if (!rows.length) return null;
  const first = rows[0]!;
  return buildEntryDetailModel({
    literal: text,
    length: Number(first.length) || [...text].length,
    corpusWeight: getEssayFrequency(text),
    readings: rows,
    syns: [],
    ants: [],
    signals: {},
  }) as EntryDetailModel;
}

async function fetchWordRows(text: string): Promise<Record<string, unknown>[]> {
  const db = getDatabase();
  return queryRows(db, WORDS_SQL, [text]);
}

async function fetchRelations(text: string): Promise<{ syns: string[]; ants: string[] }> {
  const db = getDatabase();
  const pool = await buildRelationPool(db, text);
  const syns = relationPoolSnapshotItems(pool, 'syn')
    .filter((i) => i.in_db && i.char && i.char !== text)
    .map((i) => i.char!)
    .slice(0, 24);
  const ants = relationPoolSnapshotItems(pool, 'ant')
    .filter((i) => i.in_db && i.char && i.char !== text)
    .map((i) => i.char!)
    .slice(0, 24);
  return { syns, ants };
}

/** Fast path: words row only (~10ms). */
export async function loadEntryDetailCore(literal: string): Promise<EntryDetailModel | null> {
  const text = literal.trim();
  if (!text || !isDatabaseInitialized()) return null;

  const cached = fullCache.get(text);
  if (cached) return cached;

  const rows = await fetchWordRows(text);
  return coreFromRows(text, rows);
}

/** Slow path: near/antonym pool (~2s). */
export async function loadEntryDetailRelations(
  literal: string,
): Promise<{ syns: string[]; ants: string[] }> {
  const text = literal.trim();
  if (!text || !isDatabaseInitialized()) return { syns: [], ants: [] };

  const cached = fullCache.get(text);
  if (cached) return { syns: cached.syns, ants: cached.ants };

  return fetchRelations(text);
}

export async function enrichEntryDetailRelations(model: EntryDetailModel): Promise<EntryDetailModel> {
  const text = model.literal.trim();
  const cached = fullCache.get(text);
  if (cached) return cached;

  const { syns, ants } = await loadEntryDetailRelations(text);
  const full = { ...model, syns, ants };
  fullCache.set(text, full);
  return full;
}

export async function loadEntryDetail(literal: string): Promise<EntryDetailModel | null> {
  const core = await loadEntryDetailCore(literal);
  if (!core) return null;
  if (core.syns.length || core.ants.length) return core;
  return enrichEntryDetailRelations(core);
}

/** ponytail: allow tests to inject ranking without full init */
export function __initRankingForDetail(data: Parameters<typeof initRankingData>[0]): void {
  initRankingData(data);
}

/** ponytail: test isolation */
export function __clearEntryDetailCache(): void {
  fullCache.clear();
}