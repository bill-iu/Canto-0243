/**
 * 近反義池 facade — ranking / builder / projection (Phase C PR4).
 */
export type {
  RelationKind,
  RelationPoolItem,
  RelationPoolSnapshot,
} from './relation-pool-snapshot.ts';

export {
  finalScore,
  mergeRelationPools,
  sortAntPool,
  sortSynPool,
  morphemeCharsFromWordLists,
  RUNTIME_DERIVED_ANT_SOURCES,
} from './relation-pool-ranking.ts';

export { buildRelationPool } from './relation-pool-builder.ts';

export {
  projectRelationPool,
  relationPoolPage,
  relationLookupItems,
  relationPoolLogicSelfCheck,
} from './relation-pool-projection.ts';
