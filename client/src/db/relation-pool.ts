/**
 * 近反義池 facade — ranking + 近反義池投影 read entry (P2 #4).
 * Runtime callers use projectRelationPool only; builder is internal.
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

export {
  projectRelationPool,
  relationPoolPage,
  relationLookupItems,
  relationPoolLogicSelfCheck,
  invalidateRelationPoolCache,
} from './relation-pool-projection.ts';

export {
  getLexiconMembership,
  invalidateLexiconMembership,
  isLexiconMembershipReady,
} from './lexicon-membership.ts';
