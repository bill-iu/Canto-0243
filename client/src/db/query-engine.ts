/**
 * Query engine facade — re-exports client/src/db/query/* (Arch Phase B).
 */
export { QueryKind, RouteKind } from './query-kind.ts';
export {
  normalizeQuery,
  normalizeAndParse,
  parseQuery,
  parseHeteronymCodeQuery,
  parseDoubledSyllableSyntax,
  parseRelationSyntax,
  parseCodeRefMiddleRhymeQuery,
  parseTripleRhymeAnchorQuery,
  parseWildcardCodeAnchorQuery,
  tryParseBeforeMask,
  isRelationSyntaxQuery,
  parseAtTailQuery,
  parsePlusAnchorQuery,
  parsePrefixWildcardEqualsQuery,
  parsePrefixWildcardInitialQuery,
  parsePartialRhymeMaskQuery,
  parsePartialInitialMaskQuery,
  parseSerialPhonemeAnchorQuery,
  parseJyutpingAnchorQuery,
  parseRhymeAnchorQuery,
  isFramedEqualsQuery,
  isPingZeSerialQuery,
  normalizeQuerySyntax,
  JYUTPING_SYN_MODE_HINT,
  CODE_TAIL_MIDDLE,
  parserLogicSelfCheck,
  lookupLayoutSelfCheck,
  codePrefixedWholeWordEqualsEmptyHint,
  resolveFallback0243Mode,
} from './query/parse.ts';
export { dispatchParsed, executeListFilter } from './query/dispatch.ts';
export { dispatchSynMode } from './query/mode-dispatch.ts';
export { buildLookupLayout } from './query/lookup-layout.ts';
export { QueryEngine, queryEngine, searchWords, executeSearch } from './query/engine.ts';

export type {
  QueryMode,
  ParsedQuery,
  QueryResult,
  SearchContext,
  SearchResult,
  DigitCodeQuery,
  WordLookupQuery,
  JyutpingFragmentQuery,
  MaskQuery,
  RelationLookupQuery,
  UnmatchedQuery,
} from './query-types.ts';

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
export {
  getCandidatesForLength,
  LengthCodeCandidateSource,
  positionMatchSourcesSelfCheck,
  wordMatchesWidth,
} from './position-match/sources.ts';
