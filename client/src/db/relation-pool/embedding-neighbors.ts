import type { Database } from '../sqljs.ts';
import { queryRows } from '../database-backend.ts';
import type { RelationPoolItem } from './snapshot.ts';
import { finalScore } from './ranking.ts';
import {
  EMBEDDING_NBR_RELATION,
  EMBEDDING_NBR_SOURCE,
  getEmbeddingNbrIndex,
} from '../embedding-nbr.ts';

/** E1c: semantic_related from compact CSR bin (not word_relations rows). */
export async function fetchEmbeddingNbrItems(
  db: Database,
  query: string,
): Promise<RelationPoolItem[]> {
  const idx = getEmbeddingNbrIndex();
  if (!idx) return [];
  const q = query.trim();
  if (!q) return [];
  const headRows = await queryRows(
    db,
    'SELECT id FROM words WHERE char = ? ORDER BY id ASC LIMIT 1',
    [q],
  );
  if (!headRows.length) return [];
  const headId = Number((headRows[0] as { id: number }).id);
  const hits = idx.neighborsOf(headId);
  if (!hits.length) return [];
  const idList = hits.map((h) => h.id);
  const placeholders = idList.map(() => '?').join(',');
  const charRows = await queryRows(
    db,
    `SELECT id, char, jyutping, code FROM words WHERE id IN (${placeholders})`,
    idList,
  );
  const byId = new Map<number, { char: string; jyutping: string; code: string }>();
  for (const row of charRows) {
    byId.set(Number(row.id), {
      char: String(row.char ?? ''),
      jyutping: String(row.jyutping ?? ''),
      code: String(row.code ?? ''),
    });
  }
  const items: RelationPoolItem[] = [];
  for (const hit of hits) {
    const meta = byId.get(hit.id);
    if (!meta?.char || meta.char === q) continue;
    items.push({
      char: meta.char,
      relation: EMBEDDING_NBR_RELATION,
      source: EMBEDDING_NBR_SOURCE,
      score: hit.score,
      in_db: true,
      jyutping: meta.jyutping,
      code: meta.code,
      group_codes: [],
      _sort: finalScore(EMBEDDING_NBR_SOURCE, hit.score, true),
    });
  }
  return items;
}
