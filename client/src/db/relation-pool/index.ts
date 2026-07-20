/** 近反義池 deep package (C7) — public surface is projection only (ADR-0050). */
export {
  invalidateRelationPoolCache,
  projectRelationPool,
  relationLookupItems,
  relationPoolPage,
} from './projection.ts';
export {
  DEFAULT_RELATION_POOL_PAGE_SIZE,
  createRelationPoolSnapshot,
  relationPoolSnapshotItems,
  type RelationKind,
  type RelationPoolItem,
  type RelationPoolSnapshot,
} from './snapshot.ts';
