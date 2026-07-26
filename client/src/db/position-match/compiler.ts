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
import {
  finalizeCanonicalMatchSpec,
  type CanonicalEqualsSpan,
  type CanonicalMatchSpecDraft,
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
 * Every MatchSpec query kind is compiled here; no mutable registry fallback
 * is allowed across this seam.
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
  if (query.kind === QueryKind.JYUTPING_ANCHOR) return compileJyutpingAnchor(query);
  if (query.kind === QueryKind.PING_ZE_SERIAL) return compilePingZeSerial(query);
  throw new Error('MatchSpec compiler has no implementation for this query kind');
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
  const slots: SlotConstraint[] = query.code_slots.map(([pos, value]) => ({ pos, kind: 'code_digit', value }));
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
  const slots: SlotConstraint[] = [...query.code_digits].map((value, pos) => ({ pos, kind: 'code_digit', value }));
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

function jyutpingCodeSlots(query: JyutpingAnchorQuery): SlotConstraint[] {
  if (query.code_slots?.length) {
    return query.code_slots.map(([pos, value]) => ({ pos, kind: 'code_digit', value }));
  }
  return query.code_prefix && query.width === query.code_prefix.length
    ? codePrefixSlots(query.code_prefix)
    : [];
}

function compileJyutpingAnchor(query: JyutpingAnchorQuery): CanonicalMatchSpec {
  const codeSlots = jyutpingCodeSlots(query);
  if (query.dual_phoneme) {
    const initial = finalizeCanonicalMatchSpec({
      width: query.width,
      slots: [...codeSlots, {
        pos: query.anchor_pos,
        kind: 'initial_letters',
        value: query.dual_initial_value || query.anchor_value,
      }],
    });
    const final = finalizeCanonicalMatchSpec({
      width: query.width,
      slots: [...codeSlots, {
        pos: query.anchor_pos,
        kind: 'rhyme_letters',
        value: query.anchor_value,
      }],
    });
    return finalizeCanonicalMatchSpec({
      width: query.width,
      slots: codeSlots,
      phoneme_alternatives: { initial, final },
    });
  }
  return finalizeCanonicalMatchSpec({
    width: query.width,
    slots: [...codeSlots, {
      pos: query.anchor_pos,
      kind: query.anchor_kind,
      value: query.anchor_value,
    }],
  });
}

function draftFromCanonical(spec: CanonicalMatchSpec): CanonicalMatchSpecDraft {
  const slots: SlotConstraint[] = spec.slots.map((slot) => ({
    pos: slot.pos,
    kind: slot.kind,
    value: slot.value == null || typeof slot.value === 'string'
      ? slot.value
      : new Set(slot.value),
  }));
  return {
    width: spec.width,
    mask: spec.mask,
    slots,
    equals_span: spec.equals_span,
    compound_kind: spec.compound?.kind,
    connective: spec.compound?.connective,
    ranking: spec.ranking,
    candidate_scope: spec.candidate_scope,
    code_mode: spec.code_mode,
    phoneme_alternatives: spec.phoneme_alternatives,
  };
}

function compilePingZeSerial(query: PingZeSerialQuery): CanonicalMatchSpec {
  if (query.base) {
    const base = compileParsedQuery(query.base);
    const codeDigitPositions = new Set(
      base.slots.filter((slot) => slot.kind === 'code_digit').map((slot) => slot.pos),
    );
    const fixedPositions = new Set(
      base.slots
        .filter((slot) => slot.kind !== 'code_digit' && slot.kind !== 'tone_class' && !codeDigitPositions.has(slot.pos))
        .map((slot) => slot.pos),
    );
    const codePositions = [...Array(base.width).keys()].filter((pos) => !fixedPositions.has(pos));
    const slots: SlotConstraint[] = base.slots.filter((slot) => slot.kind !== 'tone_class').map((slot) => ({
      pos: slot.pos,
      kind: slot.kind,
      value: slot.value == null || typeof slot.value === 'string'
        ? slot.value
        : new Set(slot.value),
    }));
    const mask = [...base.mask];
    [...query.raw_q].filter((token) => /[PZ?0-9]/.test(token)).forEach((token, index) => {
      if (token !== 'P' && token !== 'Z') return;
      const pos = codePositions[index];
      if (pos == null) return;
      for (let i = slots.length - 1; i >= 0; i -= 1) {
        if (slots[i]!.pos === pos && slots[i]!.kind === 'code_digit') slots.splice(i, 1);
      }
      mask[pos] = '?';
      slots.push({ pos, kind: 'tone_class', value: token === 'P' ? 'ping' : 'ze' });
    });
    return finalizeCanonicalMatchSpec({ ...draftFromCanonical(base), slots, mask: mask.join(''), code_mode: query.pzmode });
  }
  const width = query.raw_q.length + (query.anchor ? 1 : 0);
  const slots: SlotConstraint[] = [];
  [...query.raw_q].forEach((token, pos) => {
    if (token === 'P' || token === 'Z') slots.push({ pos, kind: 'tone_class', value: token === 'P' ? 'ping' : 'ze' });
    else if (/\d/.test(token)) slots.push({ pos, kind: 'code_digit', value: token });
  });
  if (query.anchor) slots.push({ pos: query.raw_q.length, kind: 'final_anchor', value: query.anchor });
  return finalizeCanonicalMatchSpec({ width, mask: '?'.repeat(width), slots, code_mode: query.pzmode });
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
