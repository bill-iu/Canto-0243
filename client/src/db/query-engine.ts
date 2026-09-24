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
  HeteronymCodeQuery,
  JyutpingAnchorQuery,
  WordLookupQuery,
  JyutpingFragmentQuery,
  MaskQuery,
  RelationLookupQuery,
  UnmatchedQuery,
} from './query-types.ts';

export { executeCanonicalMatchSpecPage } from './position-match/engine.ts';
export {
  canonicalMatchSpecToJson,
  finalizeCanonicalMatchSpec,
} from './position-match/canonical.ts';
export { compileParsedQuery, compileQuery, requireMatchSpecQuery } from './position-match/compiler.ts';
export {
  getCandidatesForLength,
  LengthCodeCandidateSource,
  positionMatchSourcesSelfCheck,
} from './position-match/sources.ts';
export type { CanonicalMatchSpec } from './position-match/canonical.ts';
