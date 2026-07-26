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
import type { ConstraintKind, SlotConstraint } from './spec.ts';
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
  if (query.kind === QueryKind.PARTIAL_RHYME_MASK) return compilePartialMask(query, 'final_anchor');
  if (query.kind === QueryKind.PARTIAL_INITIAL_MASK) return compilePartialMask(query, 'initial_anchor');
  if (query.kind === QueryKind.CODE_REF_MIDDLE_RHYME) return compileCodeRefMiddleRhyme(query);
  if (query.kind === QueryKind.RHYME_ANCHOR) return compileRhymeAnchor(query);
  if (query.kind === QueryKind.TRIPLE_RHYME_ANCHOR) return compileTripleRhymeAnchor(query);
  if (query.kind === QueryKind.MASK) return compileMask(query);
  if (query.kind === QueryKind.WILDCARD_CODE_ANCHOR) return compileWildcardCodeAnchor(query);
  if (query.kind === QueryKind.COMPOUND_SYN) return compileCompound(query, 'syn');
  if (query.kind === QueryKind.COMPOUND_ANT) return compileCompound(query, 'ant');
  if (query.kind === QueryKind.COMPOUND_CONNECT_SYN) return compileCompound(query, 'syn');
  if (query.kind === QueryKind.COMPOUND_CONNECT_ANT) return compileCompound(query, 'ant');
  if (query.kind === QueryKind.COMPOUND_DOUBLED_SYLLABLE) return compileDoubledSyllable(query);
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

function compilePartialMask(
  query: PartialRhymeMaskQuery | PartialInitialMaskQuery,
  kind: 'final_anchor' | 'initial_anchor',
): CanonicalMatchSpec {
  return finalizeCanonicalMatchSpec({
    width: query.width,
    mask: query.pattern,
    slots: query.anchors.map(([pos, value]) => ({ pos, kind, value })),
  });
}

function compileCodeRefMiddleRhyme(query: CodeRefMiddleRhymeQuery): CanonicalMatchSpec {
  return finalizeCanonicalMatchSpec({
    width: query.width,
    mask: '?'.repeat(query.width),
    slots: query.slots.map((slot) => ({
      pos: slot.pos,
      kind: slot.kind as ConstraintKind,
      value: slot.value,
    })),
  });
}

function compileRhymeAnchor(query: RhymeAnchorQuery): CanonicalMatchSpec {
  const mask = Array(query.width).fill('?') as string[];
  if (query.anchor_pos === 0) {
    for (let i = 0; i < query.slots.length; i += 1) mask[i + 1] = query.slots[i]!;
  } else {
    for (let i = 0; i < query.slots.length; i += 1) mask[i] = query.slots[i]!;
  }
  return finalizeCanonicalMatchSpec({
    width: query.width,
    mask: mask.join(''),
    slots: [{
      pos: query.anchor_pos,
      kind: query.constraint === 'final' ? 'final_anchor' : 'initial_anchor',
      value: query.anchor,
    }],
  });
}

function compileTripleRhymeAnchor(query: TripleRhymeAnchorQuery): CanonicalMatchSpec {
  return finalizeCanonicalMatchSpec({
    width: query.width,
    mask: '?'.repeat(query.width),
    slots: [{ pos: query.anchor_pos, kind: 'final_anchor', value: query.anchor }],
  });
}

function compileMask(query: MaskQuery): CanonicalMatchSpec {
  const slots: SlotConstraint[] = [];
  for (let pos = 0; pos < query.raw_q.length; pos += 1) {
    const value = query.raw_q[pos]!;
    if (/\d/.test(value)) slots.push({ pos, kind: 'code_digit', value });
  }
  return finalizeCanonicalMatchSpec({
    width: query.raw_q.length,
    mask: query.raw_q,
    slots,
    ranking: 'literal_priority',
  });
}

function codePrefixSlots(prefix: string | undefined): SlotConstraint[] {
  return prefix
    ? [...prefix].map((value, pos) => ({ pos, kind: 'code_digit', value }))
    : [];
}

function compileWildcardCodeAnchor(query: WildcardCodeAnchorQuery): CanonicalMatchSpec {
  const mask = Array(query.width).fill('?') as string[];
  const slots = query.slots.map((slot) => ({
    pos: slot.pos,
    kind: slot.kind as ConstraintKind,
    value: slot.value,
  }));
  for (const slot of slots) {
    if (slot.kind === 'literal_char' && typeof slot.value === 'string') mask[slot.pos] = slot.value;
  }
  return finalizeCanonicalMatchSpec({ width: query.width, mask: mask.join(''), slots });
}

function compileCompound(
  query: CompoundSynQuery | CompoundAntQuery | CompoundConnectSynQuery | CompoundConnectAntQuery,
  kind: 'syn' | 'ant',
): CanonicalMatchSpec {
  const width = query.kind === QueryKind.COMPOUND_CONNECT_SYN || query.kind === QueryKind.COMPOUND_CONNECT_ANT ? 3 : 2;
  const slots = codePrefixSlots(query.code_prefix);
  if (query.rhyme_char) {
    slots.push({
      pos: width - 1,
      kind: 'final_anchor',
      value: query.rhyme_char,
    });
  }
  return finalizeCanonicalMatchSpec({
    width,
    slots,
    compound_kind: query.kind === QueryKind.COMPOUND_CONNECT_SYN || query.kind === QueryKind.COMPOUND_CONNECT_ANT
      ? kind
      : kind,
    connective: 'connective' in query ? query.connective : null,
  });
}

function compileDoubledSyllable(query: CompoundDoubledSyllableQuery): CanonicalMatchSpec {
  const slots = codePrefixSlots(query.code_prefix);
  if (query.rhyme_char) {
    slots.push({ pos: query.width - 1, kind: 'final_anchor', value: query.rhyme_char });
  }
  return finalizeCanonicalMatchSpec({
    width: query.width,
    slots,
    compound_kind: 'doubled_syllable',
  });
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
