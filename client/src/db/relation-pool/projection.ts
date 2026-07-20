/** 近反義池投影 — thin entry (port of pool_projection; Phase C PR4). */
import type { Database } from './sqljs.ts';
import { queryRows } from './database-backend.ts';
import {
  matchesCodePositions,
  requiredCodesFromDigitString,
} from './position-match/filters/f1-slot-code.ts';
import {
  relationPoolSnapshotItems,
  type RelationPoolItem,
  type RelationPoolSnapshot,
} from './relation-pool-snapshot.ts';
import { buildRelationPool } from './relation-pool-builder.ts';

/** Seed-scoped LRU — repeat ~開心 / 近反義 mode hits without rebuild. */
const POOL_CACHE_MAX = 48;
const poolCache = new Map<string, RelationPoolSnapshot>();

function poolCacheKey(
  seed: string,
  options: { includeStatic?: boolean; includeDerivedAnt?: boolean },
): string {
  const st = options.includeStatic === false ? '0' : '1';
  const der = options.includeDerivedAnt === false ? '0' : '1';
  return `${seed.trim()}\0${st}\0${der}`;
}

export function invalidateRelationPoolCache(): void {
  poolCache.clear();
}

/**
 * Unified read entry — port of project_relation_pool.
 * PWA never injects word rows (Portable may allow_inject); policy is asymmetric by design.
 */
export async function projectRelationPool(
  db: Database,
  seedChar: string,
  options: { includeStatic?: boolean; includeDerivedAnt?: boolean } = {},
): Promise<RelationPoolSnapshot> {
  const key = poolCacheKey(seedChar, options);
  const hit = poolCache.get(key);
  if (hit) {
    // refresh LRU order
    poolCache.delete(key);
    poolCache.set(key, hit);
    return hit;
  }
  const snap = await buildRelationPool(db, seedChar, options);
  if (poolCache.size >= POOL_CACHE_MAX) {
    const oldest = poolCache.keys().next().value;
    if (oldest !== undefined) poolCache.delete(oldest);
  }
  poolCache.set(key, snap);
  return snap;
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
    const required = requiredCodesFromDigitString(codePrefix);
    if (seed.length !== required.length) {
      return [];
    }
    const rows = await queryRows(db, 'SELECT code FROM words WHERE char = ? LIMIT 20', [seed]);
    let seedOk = false;
    for (const row of rows) {
      const code = String((row as Record<string, unknown>).code ?? '');
      if (matchesCodePositions(code, required, mode)) {
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
