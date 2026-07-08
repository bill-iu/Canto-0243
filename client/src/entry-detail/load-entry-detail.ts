import { buildEntryDetailModel } from '../../../frontend/entry-detail-core.mjs';
import type { EntryDetailModel } from './types.ts';
import { getDatabase, isDatabaseInitialized } from '../db/init.ts';
import { queryRows } from '../db/database-backend.ts';
import { getEssayFrequency, initRankingData } from '../db/ranking.ts';
import { buildRelationPool } from '../db/relation-pool.ts';
import { relationPoolSnapshotItems } from '../db/relation-pool-snapshot.ts';

export type { EntryDetailModel } from './types.ts';

export async function loadEntryDetail(literal: string): Promise<EntryDetailModel | null> {
  const text = literal.trim();
  if (!text || !isDatabaseInitialized()) return null;

  const db = getDatabase();
  const rows = await queryRows(
    db,
    'SELECT char, jyutping, code, initials, finals, length, source_flags FROM words WHERE char = ?',
    [text],
  );

  if (!rows.length) return null;

  const pool = await buildRelationPool(db, text);
  const syns = relationPoolSnapshotItems(pool, 'syn')
    .filter((i) => i.in_db && i.char && i.char !== text)
    .map((i) => i.char!)
    .slice(0, 24);
  const ants = relationPoolSnapshotItems(pool, 'ant')
    .filter((i) => i.in_db && i.char && i.char !== text)
    .map((i) => i.char!)
    .slice(0, 24);

  const first = rows[0] as Record<string, unknown>;
  return buildEntryDetailModel({
    literal: text,
    length: Number(first.length) || [...text].length,
    corpusWeight: getEssayFrequency(text),
    readings: rows,
    syns,
    ants,
    signals: {},
  }) as EntryDetailModel;
}

/** ponytail: allow tests to inject ranking without full init */
export function __initRankingForDetail(data: Parameters<typeof initRankingData>[0]): void {
  initRankingData(data);
}