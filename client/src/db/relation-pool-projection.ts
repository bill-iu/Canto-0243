/** 近反義池投影 — thin entry (port of pool_projection; Phase C PR4). */
import type { Database } from './sqljs.ts';
import { queryRows } from './database-backend.ts';
import { getCodeVariants } from './code-variants.ts';
import {
  relationPoolSnapshotItems,
  type RelationPoolItem,
  type RelationPoolSnapshot,
} from './relation-pool-snapshot.ts';
import { buildRelationPool } from './relation-pool-builder.ts';

/** Unified read entry — mirrors project_relation_pool (no inject on PWA). */
export async function projectRelationPool(
  db: Database,
  seedChar: string,
  options: { includeStatic?: boolean; includeDerivedAnt?: boolean } = {},
): Promise<RelationPoolSnapshot> {
  return buildRelationPool(db, seedChar, options);
}

/** Port of pool_projection.relation_pool_page — flat syns+ants+semantic slice */
export function relationPoolPage(
  db: Database,
  seed: string,
  limit: number,
  offset: number,
): Promise<RelationPoolItem[]> {
  return projectRelationPool(db, seed).then((pool) => pool.page(limit, offset));
}

export async function relationLookupItems(
  db: Database,
  seed: string,
  relationKind: 'syn' | 'ant',
  mode: string,
  codePrefix: string | undefined,
  limit: number,
  offset: number,
): Promise<RelationPoolItem[]> {
  const pool = await projectRelationPool(db, seed);
  const allItems = relationPoolSnapshotItems(pool, relationKind);

  const seen = new Set<string>();
  let unique = allItems.filter((item) => {
    if (!item.char || seen.has(item.char)) {
      return false;
    }
    seen.add(item.char);
    return item.in_db;
  });

  if (codePrefix) {
    if (seed.length !== codePrefix.length) {
      return [];
    }
    const variants = new Set(getCodeVariants(codePrefix, mode === 'm2' || mode === '02493' ? 'm2' : 'm1'));
    const rows = await queryRows(db, 'SELECT code FROM words WHERE char = ? LIMIT 20', [seed]);
    let seedOk = false;
    for (const row of rows) {
      const code = String((row as Record<string, unknown>).code ?? '');
      if (variants.has(code)) {
        seedOk = true;
        break;
      }
    }
    if (!seedOk) {
      return [];
    }
  }

  unique.sort((a, b) => (a._sort ?? 99) - (b._sort ?? 99));
  return unique.slice(offset, offset + limit);
}

/** ponytail: runnable self-check — `npx tsx client/scripts/relation-pool-self-check.ts` */
export async function relationPoolLogicSelfCheck(db: Database): Promise<void> {
  const pool = await projectRelationPool(db, '開心');
  const chars = pool.syns.filter((i) => i.in_db).map((i) => i.char);
  if (!chars.includes('快樂') || !chars.includes('愉快')) {
    throw new Error(`relationPoolLogicSelfCheck: syns ${chars.join(',')}`);
  }
}
