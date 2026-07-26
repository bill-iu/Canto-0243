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
  finalizeCanonicalMatchSpec,
  type CanonicalEqualsSpan,
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
  if (query.kind === QueryKind.EQUALS) return compileEquals(query);
  if (query.kind === QueryKind.PREFIX_WILDCARD_EQUALS) return compilePrefixWildcardEquals(query);
  if (query.kind === QueryKind.SERIAL_PHONEME) return compileSerialPhoneme(query);
  if (query.kind === QueryKind.PLUS_ANCHOR) return compilePlusAnchor(query);
  if (query.kind === QueryKind.LITERAL_REF) return compileLiteralRef(query);
  const legacy = buildMatchSpecForParsed(query);
  if (!legacy) {
    throw new Error(`MatchSpec compiler has no implementation for ${query.kind}`);
  }
  return canonicalizeLegacyMatchSpec(legacy);
}

const FRAMED_EQUALS_RE = /^(\d*)(\^|=)?([\p{Script=Han}]+)(=)?(\d*)$/u;

function equalsDraft(raw: string): {
  width: number;
  slots: Array<{ pos: number; kind: 'code_digit'; value: string }>;
  equals_span: CanonicalEqualsSpan;
} | null {
  const match = raw.match(FRAMED_EQUALS_RE);
  if (!match || !match[3]) return null;
  const target = match[3];
  const left = match[1] ?? '';
  const right = match[5] ?? '';
  const rightEqual = Boolean(match[4]);
  const innerMark = Boolean(match[2]);
  const targetLength = [...target].length;
  const width = left.length + right.length || targetLength;
  const fullCode = left + right;
  return {
    width,
    slots: [...fullCode].map((digit, pos) => ({ pos, kind: 'code_digit', value: digit })),
    equals_span: {
      ref_literal: target,
      ref_jyutping: null,
      start_pos: Math.max(0, left.length - targetLength),
      dimension: rightEqual ? 'final' : 'initial',
      phoneme_anchor_only: Boolean(left && (right || innerMark)),
      whole_word: Math.max(0, left.length - targetLength) === 0 && targetLength === width,
    },
  };
}

function compileEquals(query: EqualsQuery): CanonicalMatchSpec {
  const draft = equalsDraft(query.raw_q);
  if (!draft) throw new Error(`invalid equals MatchSpec query: ${query.raw_q}`);
  return finalizeCanonicalMatchSpec(draft);
}

function compilePrefixWildcardEquals(query: PrefixWildcardEqualsQuery): CanonicalMatchSpec {
  const draft = equalsDraft(query.inner_q);
  if (!draft) throw new Error(`invalid prefix wildcard equals query: ${query.raw_q}`);
  return finalizeCanonicalMatchSpec({
    ...draft,
    width: query.width,
    mask: '?'.repeat(query.width),
    equals_span: { ...draft.equals_span, start_pos: 1, phoneme_anchor_only: true, whole_word: false },
  });
}

function compileSerialPhoneme(query: SerialPhonemeAnchorQuery): CanonicalMatchSpec {
  const kind = query.constraint === 'final' ? 'final_anchor' : 'initial_anchor';
  return finalizeCanonicalMatchSpec({
    width: query.width,
    mask: query.mask.length === query.width ? query.mask : '?'.repeat(query.width),
    slots: [
      ...query.code_slots.map(([pos, value]) => ({ pos, kind: 'code_digit' as const, value })),
      ...query.anchors.map(([pos, value]) => ({ pos, kind: kind as 'final_anchor' | 'initial_anchor', value })),
    ],
  });
}

function compilePlusAnchor(query: PlusAnchorQuery): CanonicalMatchSpec {
  const slots = query.code_slots.map(([pos, value]) => ({ pos, kind: 'code_digit' as const, value }));
  if (query.constraint === 'literal') {
    slots.push({ pos: query.anchor_pos, kind: 'literal_char' as const, value: query.anchor });
  } else {
    slots.push({
      pos: query.anchor_pos,
      kind: query.constraint === 'final' ? 'final_anchor' as const : 'initial_anchor' as const,
      value: query.anchor,
    });
  }
  const mask = Array.from({ length: query.width }, () => '?');
  if (query.constraint === 'literal') mask[query.anchor_pos] = query.anchor;
  return finalizeCanonicalMatchSpec({ width: query.width, slots, mask: mask.join('') });
}

function compileLiteralRef(query: LiteralRefQuery): CanonicalMatchSpec {
  const slots = [...query.code_digits].map((value, pos) => ({ pos, kind: 'code_digit' as const, value }));
  slots.push({ pos: query.literal_pos, kind: 'literal_char' as const, value: query.literal_char });
  const mask = '?'.repeat(query.literal_pos) + query.literal_char
    + '?'.repeat(query.width - query.literal_pos - 1);
  return finalizeCanonicalMatchSpec({ width: query.width, slots, mask });
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
