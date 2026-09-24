/** Migration/test compatibility only. New execution callers use query-engine.ts. */
export type {
  MatchSpec,
  EqualsSpan,
  EqualsDimension,
  SlotConstraint,
  ConstraintKind,
  CompoundKind,
  CandidateSource,
  MaskFamilySearchResult,
} from './position-match/spec.ts';

export {
  attachEqualsSpan,
  createMatchSpec,
  getEqualsSpan,
  positionMatchSpecSelfCheck,
} from './position-match/spec.ts';
export { buildEqualsMatchSpec } from './position-match/equals-spec.ts';
export {
  buildMaskFromSlots,
  isWildcardChar,
  parseMaskQuery,
} from './position-match/mask-grammar.ts';
export {
  buildJyutpingDualMatchSpecs,
  buildMatchSpecForParsed,
  MATCH_SPEC_BUILDERS,
  normalizeToMatchSpec,
} from './position-match/match-spec-registry.ts';
export { executeMatchSpec } from './position-match/engine.ts';
export { canonicalMatchSpecToLegacy, canonicalizeLegacyMatchSpec } from './position-match/canonical.ts';
