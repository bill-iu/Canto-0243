import {
  buildEntryDetailModel,
  buildEntryDetailModelFromPick,
} from '../../../frontend/entry-detail-core.mjs';
import type { EntryDetailModel } from './types.ts';
import { getDatabase, isDatabaseInitialized } from '../db/init.ts';
import { queryRows } from '../db/database-backend.ts';
import { getEssayFrequency, initRankingData } from '../db/ranking.ts';
import { projectRelationPool } from '../db/relation-pool-projection.ts';
import { relationPoolSnapshotItems } from '../db/relation-pool-snapshot.ts';
import { getCilinSynonyms, getStaticAntonyms, getStaticSynonyms } from '../db/thesaurus.ts';

export type { EntryDetailModel } from './types.ts';

export type EntryPickReading = {
  jyutping?: string;
  code?: string;
  initials?: unknown;
  finals?: unknown;
  source_flags?: number;
};

const WORDS_SQL =
  'SELECT char, jyutping, code, initials, finals, length, source_flags FROM words WHERE char = ?';

const DIRECT_REL_PROBE_SQL = `
  SELECT 1
  FROM words w1
  JOIN word_relations wr ON wr.word_id = w1.id
  WHERE w1.char = ? AND wr.relation_type IN ('syn','ant','semantic_related')
    AND wr.source NOT IN ('ant_syn_mirror', 'ant_cilin_exanded')
  LIMIT 1
`;

const fullCache = new Map<string, EntryDetailModel>();

function hasStaticDirectSources(text: string): boolean {
  const q = text.trim();
  if (!q) return false;
  return (
    getStaticSynonyms(q).length > 0 ||
    getStaticAntonyms(q).length > 0 ||
    getCilinSynonyms(q).length > 0
  );
}

/** Fast probe: skip ~2s projectRelationPool when no direct syn/ant sources exist. */
export async function hasDirectRelationSources(literal: string): Promise<boolean> {
  const text = literal.trim();
  if (!text || !isDatabaseInitialized()) return false;
  if (hasStaticDirectSources(text)) return true;
  const rows = await queryRows(getDatabase(), DIRECT_REL_PROBE_SQL, [text]);
  return rows.length > 0;
}

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
  const pool = await projectRelationPool(db, text);
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

/** Zero-latency model from search-result rows already in memory. */
export function instantEntryDetailModel(
  literal: string,
  readings: EntryPickReading[],
): EntryDetailModel | null {
  const text = literal.trim();
  if (!text || !readings.length) return null;
  return buildEntryDetailModelFromPick(text, readings, {
    corpusWeight: getEssayFrequency(text),
  }) as EntryDetailModel;
}

export function getCachedEntryDetail(literal: string): EntryDetailModel | null {
  return fullCache.get(literal.trim()) ?? null;
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

/** Merge DB fields (phonetic, sources, corpus) into an existing model. */
export async function enrichEntryDetailFromDb(model: EntryDetailModel): Promise<EntryDetailModel> {
  const text = model.literal.trim();
  if (!text || !isDatabaseInitialized()) return model;

  const cached = fullCache.get(text);
  if (cached) return cached;

  const rows = await fetchWordRows(text);
  const dbModel = coreFromRows(text, rows);
  if (!dbModel) return model;
  return { ...dbModel, syns: model.syns, ants: model.ants };
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