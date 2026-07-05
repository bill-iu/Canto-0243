/** 近反義池快照: fixed relation results, not tied to DB or static indexes. */

export const DEFAULT_RELATION_POOL_PAGE_SIZE = 160;

export type RelationKind = 'syn' | 'ant' | 'semantic_related';

export type RelationPoolItem = {
  char: string;
  relation: RelationKind;
  source: string;
  score: number | null;
  in_db: boolean;
  jyutping: string;
  code: string;
  group_codes: string[];
  _sort: number;
};

export type RelationPoolSnapshot = {
  query: string;
  syns: RelationPoolItem[];
  ants: RelationPoolItem[];
  semantic: RelationPoolItem[];
  page: (limit: number, offset: number) => RelationPoolItem[];
  chars: (kind: 'syn' | 'ant') => string[];
};

function safePageBounds(limit: number, offset: number): { limit: number; offset: number } {
  return {
    limit: limit < 0 ? DEFAULT_RELATION_POOL_PAGE_SIZE : limit,
    offset: Math.max(0, offset),
  };
}

export function relationPoolSnapshotPage(
  snapshot: Pick<RelationPoolSnapshot, 'syns' | 'ants' | 'semantic'>,
  limit: number,
  offset: number,
): RelationPoolItem[] {
  const bounds = safePageBounds(limit, offset);
  return [...snapshot.syns, ...snapshot.ants, ...snapshot.semantic].slice(
    bounds.offset,
    bounds.offset + bounds.limit,
  );
}

export function relationPoolSnapshotChars(
  snapshot: Pick<RelationPoolSnapshot, 'syns' | 'ants'>,
  kind: 'syn' | 'ant',
): string[] {
  const rows = kind === 'syn' ? snapshot.syns : snapshot.ants;
  return rows.map((item) => item.char).filter(Boolean);
}

export function relationPoolSnapshotItems(
  snapshot: Pick<RelationPoolSnapshot, 'syns' | 'ants' | 'semantic'>,
  kind: 'syn' | 'ant' | 'all',
): RelationPoolItem[] {
  if (kind === 'syn') {
    return snapshot.syns;
  }
  if (kind === 'ant') {
    return snapshot.ants;
  }
  return [...snapshot.syns, ...snapshot.ants, ...snapshot.semantic];
}

export function createRelationPoolSnapshot(
  query: string,
  syns: RelationPoolItem[],
  ants: RelationPoolItem[],
  semantic: RelationPoolItem[],
): RelationPoolSnapshot {
  const snapshot = {
    query,
    syns,
    ants,
    semantic,
    page(limit: number, offset: number): RelationPoolItem[] {
      return relationPoolSnapshotPage(snapshot, limit, offset);
    },
    chars(kind: 'syn' | 'ant'): string[] {
      return relationPoolSnapshotChars(snapshot, kind);
    },
  };
  return snapshot;
}
