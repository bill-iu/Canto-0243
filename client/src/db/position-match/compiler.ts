/** Strict ParsedQuery → canonical MatchSpec compiler seam (migration shell). */
import { QueryKind } from '../query-kind.ts';
import { usesMatchSpec } from '../query-kind-registry.ts';
import type {
  CodeRefMiddleRhymeQuery,
  CompoundAntQuery,
  CompoundConnectAntQuery,
  CompoundConnectSynQuery,
  CompoundDoubledSyllableQuery,
  CompoundSynQuery,
  JyutpingAnchorQuery,
  LiteralRefQuery,
  MaskQuery,
  PartialInitialMaskQuery,
  PartialRhymeMaskQuery,
  PingZeSerialQuery,
  PlusAnchorQuery,
  PrefixWildcardEqualsQuery,
  RhymeAnchorQuery,
  SerialPhonemeAnchorQuery,
  TripleRhymeAnchorQuery,
  WildcardCodeAnchorQuery,
  ParsedQuery,
} from '../query-types.ts';
import type { EqualsQuery } from '../query/grammar/equals.ts';
import { buildMatchSpecForParsed } from './match-spec-registry.ts';
import {
  canonicalizeLegacyMatchSpec,
  type CanonicalMatchSpec,
} from './canonical.ts';

export type MatchSpecQuery =
  | EqualsQuery
  | PrefixWildcardEqualsQuery
  | PartialRhymeMaskQuery
  | PartialInitialMaskQuery
  | SerialPhonemeAnchorQuery
  | PlusAnchorQuery
  | LiteralRefQuery
  | WildcardCodeAnchorQuery
  | CodeRefMiddleRhymeQuery
  | RhymeAnchorQuery
  | TripleRhymeAnchorQuery
  | JyutpingAnchorQuery
  | MaskQuery
  | PingZeSerialQuery
  | CompoundSynQuery
  | CompoundConnectSynQuery
  | CompoundDoubledSyllableQuery
  | CompoundAntQuery
  | CompoundConnectAntQuery;

/** Narrow the general parser output at the query dispatch seam. */
export function requireMatchSpecQuery(parsed: ParsedQuery): MatchSpecQuery {
  if (!usesMatchSpec(parsed.kind)) {
    throw new Error(`query kind does not use MatchSpec: ${parsed.kind}`);
  }
  return parsed as MatchSpecQuery;
}

/**
 * Compile one eligible query to a complete semantic value.
 *
 * The registry call is intentionally temporary: it lets callers migrate to
 * this strict interface before the grammar builders move into this module.
 */
export function compileQuery(query: MatchSpecQuery): CanonicalMatchSpec {
  if (!usesMatchSpec(query.kind)) {
    throw new Error(`query kind does not use MatchSpec: ${query.kind}`);
  }
  const legacy = buildMatchSpecForParsed(query);
  if (!legacy) {
    throw new Error(`MatchSpec compiler has no implementation for ${query.kind}`);
  }
  return canonicalizeLegacyMatchSpec(legacy);
}

/** Strict convenience seam for callers that still hold general ParsedQuery. */
export function compileParsedQuery(parsed: ParsedQuery): CanonicalMatchSpec {
  return compileQuery(requireMatchSpecQuery(parsed));
}

/** Compile-time exhaustiveness anchor for the manifest-backed union. */
export const MATCH_SPEC_QUERY_KINDS: ReadonlySet<QueryKind> = new Set([
  QueryKind.EQUALS,
  QueryKind.PREFIX_WILDCARD_EQUALS,
  QueryKind.PARTIAL_RHYME_MASK,
  QueryKind.PARTIAL_INITIAL_MASK,
  QueryKind.SERIAL_PHONEME,
  QueryKind.PLUS_ANCHOR,
  QueryKind.LITERAL_REF,
  QueryKind.WILDCARD_CODE_ANCHOR,
  QueryKind.CODE_REF_MIDDLE_RHYME,
  QueryKind.RHYME_ANCHOR,
  QueryKind.TRIPLE_RHYME_ANCHOR,
  QueryKind.JYUTPING_ANCHOR,
  QueryKind.MASK,
  QueryKind.PING_ZE_SERIAL,
  QueryKind.COMPOUND_SYN,
  QueryKind.COMPOUND_CONNECT_SYN,
  QueryKind.COMPOUND_DOUBLED_SYLLABLE,
  QueryKind.COMPOUND_ANT,
  QueryKind.COMPOUND_CONNECT_ANT,
]);
