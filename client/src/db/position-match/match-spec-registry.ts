/**
 * QueryKind → MatchSpec builders — port of app/services/query_match_spec_registry.py (MF-2)
 */
import { buildEqualsMatchSpec } from './equals-spec.ts';
import { buildMaskFromSlots, parseMaskQuery } from './mask-grammar.ts';
import {
  attachEqualsSpan,
  createMatchSpec,
  getEqualsSpan,
  type AnchorKind,
  type CompoundKind,
  type ConstraintKind,
  type EqualsSpan,
  type MatchSpec,
  type SlotConstraint,
} from './spec.ts';
import { QueryKind } from '../query-kind.ts';
import type {
  CodeRefMiddleRhymeQuery,
  CompoundAntQuery,
  CompoundDoubledSyllableQuery,
  CompoundSynQuery,
  EqualsQuery,
  HybridCodeQuery,
  JyutpingAnchorQuery,
  LiteralRefQuery,
  MaskQuery,
  ParsedQuery,
  PartialInitialMaskQuery,
  PartialRhymeMaskQuery,
  PlusAnchorQuery,
  PrefixWildcardEqualsQuery,
  RhymeAnchorQuery,
  SerialPhonemeAnchorQuery,
  TripleRhymeAnchorQuery,
  WildcardCodeAnchorQuery,
} from '../query-engine.ts';

const HYBRID_CODE_RE = /^(\d+)([\u4e00-\u9fff]+)(\d*)$/;
const FILLWORD_CONNECTIVES = '與和或共同及跟而且並向';
const CONNECT_SYN_RE = new RegExp(`^(\\d*)~([${FILLWORD_CONNECTIVES}])~`);
const CONNECT_ANT_RE = new RegExp(`^(\\d*)!([${FILLWORD_CONNECTIVES}])!`);

export type MatchSpecBuilder = (parsed: ParsedQuery) => MatchSpec | null;

function slots(spec: MatchSpec): SlotConstraint[] {
  if (!spec.slots) {
    spec.slots = [];
  }
  return spec.slots;
}

function asKind(kind: string): ConstraintKind {
  return kind as ConstraintKind;
}

function applyJyutpingAnchorCodeSlots(spec: MatchSpec, parsed: JyutpingAnchorQuery): void {
  if (parsed.code_slots?.length) {
    for (const [pos, digit] of parsed.code_slots) {
      slots(spec).push({ pos, kind: 'code_digit', value: digit });
    }
  } else if (parsed.code_prefix && parsed.width === parsed.code_prefix.length) {
    for (let i = 0; i < parsed.code_prefix.length; i++) {
      slots(spec).push({ pos: i, kind: 'code_digit', value: parsed.code_prefix[i]! });
    }
  }
}

function buildJyutpingAnchorMatchSpec(parsed: JyutpingAnchorQuery): MatchSpec {
  const spec = createMatchSpec(parsed.width, { code_prefix: parsed.code_prefix });
  spec.mask = '?'.repeat(parsed.width);
  slots(spec).push({
    pos: parsed.anchor_pos,
    kind: parsed.anchor_kind as AnchorKind,
    value: parsed.anchor_value,
  });
  applyJyutpingAnchorCodeSlots(spec, parsed);
  return spec;
}

export function buildJyutpingDualMatchSpecs(
  parsed: JyutpingAnchorQuery,
): [MatchSpec, MatchSpec] {
  const base = (): MatchSpec => {
    const spec = createMatchSpec(parsed.width, { code_prefix: parsed.code_prefix });
    spec.mask = '?'.repeat(parsed.width);
    applyJyutpingAnchorCodeSlots(spec, parsed);
    return spec;
  };

  const initial = base();
  slots(initial).push({
    pos: parsed.anchor_pos,
    kind: 'initial_letters',
    value: parsed.dual_initial_value || parsed.anchor_value,
  });

  const final = base();
  slots(final).push({
    pos: parsed.anchor_pos,
    kind: 'rhyme_letters',
    value: parsed.anchor_value,
  });

  return [initial, final];
}

function specEquals(parsed: ParsedQuery): MatchSpec | null {
  return buildEqualsMatchSpec((parsed as EqualsQuery).raw_q);
}

function specPrefixWildcardEquals(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as PrefixWildcardEqualsQuery;
  const spec = buildEqualsMatchSpec(q.inner_q);
  if (!spec) {
    return createMatchSpec(0);
  }
  spec.width = q.width;
  const span = getEqualsSpan(spec);
  if (span) {
    attachEqualsSpan(spec, {
      ref_literal: span.ref_literal,
      start_pos: 1,
      dimension: span.dimension,
      phoneme_anchor_only: true,
      whole_word: false,
    });
  }
  spec.mask = '?'.repeat(q.width);
  if (!spec.extra) {
    spec.extra = {};
  }
  spec.extra.prefix_wildcard_equals = true;
  return spec;
}

function specPartialRhymeMask(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as PartialRhymeMaskQuery;
  const spec = createMatchSpec(q.width, { mask: q.pattern });
  if (!spec.extra) {
    spec.extra = {};
  }
  spec.extra.partial_rhyme_mask = true;
  for (const [pos, ch] of q.anchors) {
    slots(spec).push({ pos, kind: 'final_anchor', value: ch });
  }
  return spec;
}

function specPartialInitialMask(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as PartialInitialMaskQuery;
  const spec = createMatchSpec(q.width, { mask: q.pattern });
  if (!spec.extra) {
    spec.extra = {};
  }
  spec.extra.partial_initial_mask = true;
  for (const [pos, ch] of q.anchors) {
    slots(spec).push({ pos, kind: 'initial_anchor', value: ch });
  }
  return spec;
}

function specSerialPhoneme(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as SerialPhonemeAnchorQuery;
  const spec = createMatchSpec(q.width);
  spec.mask = q.mask.length === q.width ? q.mask : '?'.repeat(q.width);
  for (const [pos, digit] of q.code_slots) {
    slots(spec).push({ pos, kind: 'code_digit', value: digit });
  }
  const kind = q.constraint === 'final' ? 'final_anchor' : 'initial_anchor';
  for (const [pos, anchor] of q.anchors) {
    slots(spec).push({ pos, kind, value: anchor });
  }
  return spec;
}

function specPlusAnchor(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as PlusAnchorQuery;
  const spec = createMatchSpec(q.width, { code_prefix: q.code_prefix });
  spec.mask = '?'.repeat(q.width);
  for (const [pos, d] of q.code_slots) {
    slots(spec).push({ pos, kind: 'code_digit', value: d });
  }
  if (q.constraint === 'literal') {
    slots(spec).push({ pos: q.anchor_pos, kind: 'literal_char', value: q.anchor });
    spec.mask = spec.mask.slice(0, q.anchor_pos) + q.anchor + spec.mask.slice(q.anchor_pos + 1);
    return spec;
  }
  if (q.constraint === 'final') {
    slots(spec).push({ pos: q.anchor_pos, kind: 'final_anchor', value: q.anchor });
    return spec;
  }
  if (q.constraint === 'initial') {
    slots(spec).push({ pos: q.anchor_pos, kind: 'initial_anchor', value: q.anchor });
  }
  return spec;
}

function specLiteralRef(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as LiteralRefQuery;
  const spec = createMatchSpec(q.width, { code_prefix: q.code_digits });
  slots(spec).push({ pos: q.width - 1, kind: 'literal_char', value: q.literal_char });
  spec.mask = '?'.repeat(q.width - 1) + q.literal_char;
  return spec;
}

function specWildcardCodeAnchor(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as WildcardCodeAnchorQuery;
  const spec = createMatchSpec(q.width);
  spec.mask = '?'.repeat(q.width);
  for (const slot of q.slots) {
    const kind = asKind(slot.kind);
    slots(spec).push({ pos: slot.pos, kind, value: slot.value });
    if (kind === 'literal_char' && slot.value) {
      spec.mask = spec.mask.slice(0, slot.pos) + slot.value + spec.mask.slice(slot.pos + 1);
    }
  }
  return spec;
}

function specCodeRefMiddleRhyme(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as CodeRefMiddleRhymeQuery;
  const spec = createMatchSpec(q.width);
  spec.mask = '?'.repeat(q.width);
  for (const slot of q.slots) {
    slots(spec).push({ pos: slot.pos, kind: asKind(slot.kind), value: slot.value });
  }
  return spec;
}

function specRhymeAnchor(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as RhymeAnchorQuery;
  const spec = createMatchSpec(q.width);
  const kind = q.constraint === 'final' ? 'final_anchor' : 'initial_anchor';
  slots(spec).push({ pos: q.anchor_pos, kind, value: q.anchor });
  spec.mask = buildMaskFromSlots(q.slots, q.width, q.anchor_pos);
  return spec;
}

function specTripleRhymeAnchor(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as TripleRhymeAnchorQuery;
  const spec = createMatchSpec(q.width);
  slots(spec).push({ pos: q.anchor_pos, kind: 'final_anchor', value: q.anchor });
  spec.mask = '?'.repeat(q.width);
  return spec;
}

function specJyutpingAnchor(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as JyutpingAnchorQuery;
  if (q.dual_phoneme) {
    const [initial, final] = buildJyutpingDualMatchSpecs(q);
    const carrier = createMatchSpec(q.width, { code_prefix: q.code_prefix });
    if (!carrier.extra) {
      carrier.extra = {};
    }
    carrier.extra.dual_phoneme = true;
    carrier.extra.dual_initial_spec = initial;
    carrier.extra.dual_final_spec = final;
    return carrier;
  }
  return buildJyutpingAnchorMatchSpec(q);
}

function specHybridCode(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as HybridCodeQuery;
  const hybridMatch = HYBRID_CODE_RE.exec(q.raw_q);
  if (!hybridMatch) {
    return createMatchSpec(0);
  }
  const numPrefix = hybridMatch[1]!;
  const refChars = hybridMatch[2]!;
  const numSuffix = hybridMatch[3] ?? '';
  const fullCode = numPrefix + numSuffix;
  return createMatchSpec(fullCode.length, {
    code_prefix: fullCode,
    hybrid_ref_chars: refChars,
    hybrid_ref_pos: Math.max(0, numPrefix.length - 1),
  });
}

function specMask(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as MaskQuery;
  const { literalPositions } = parseMaskQuery(q.raw_q);
  const spec = createMatchSpec(q.raw_q.length, { literal_priority: true, mask: q.raw_q });
  for (let i = 0; i < q.raw_q.length; i++) {
    const ch = q.raw_q[i]!;
    if (/\d/.test(ch)) {
      slots(spec).push({ pos: i, kind: 'code_digit', value: ch });
    }
  }
  if (!spec.extra) {
    spec.extra = {};
  }
  spec.extra.literal_positions = literalPositions;
  return spec;
}

function specCompoundDoubledSyllable(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as CompoundDoubledSyllableQuery;
  const spec = createMatchSpec(2, {
    code_prefix: q.code_prefix,
    compound_kind: 'doubled_syllable',
  });
  if (q.rhyme_char) {
    slots(spec).push({ pos: 1, kind: 'final_anchor', value: q.rhyme_char });
  }
  return spec;
}

function specCompoundSyn(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as CompoundSynQuery;
  const connect = CONNECT_SYN_RE.exec(q.raw_q);
  if (connect) {
    const spec = createMatchSpec(3, { code_prefix: q.code_prefix, compound_kind: 'syn' });
    if (!spec.extra) {
      spec.extra = {};
    }
    spec.extra.connective = connect[2];
    if (q.rhyme_char) {
      slots(spec).push({ pos: 2, kind: 'final_anchor', value: q.rhyme_char });
    }
    return spec;
  }
  const spec = createMatchSpec(2, { code_prefix: q.code_prefix, compound_kind: 'syn' });
  if (q.rhyme_char) {
    slots(spec).push({ pos: 1, kind: 'final_anchor', value: q.rhyme_char });
  }
  return spec;
}

function specCompoundAnt(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as CompoundAntQuery;
  const connect = CONNECT_ANT_RE.exec(q.raw_q);
  if (connect) {
    const spec = createMatchSpec(3, { code_prefix: q.code_prefix, compound_kind: 'ant' });
    if (!spec.extra) {
      spec.extra = {};
    }
    spec.extra.connective = connect[2];
    if (q.rhyme_char) {
      slots(spec).push({ pos: 2, kind: 'final_anchor', value: q.rhyme_char });
    }
    return spec;
  }
  const spec = createMatchSpec(2, { code_prefix: q.code_prefix, compound_kind: 'ant' });
  if (q.rhyme_char) {
    slots(spec).push({ pos: 1, kind: 'final_anchor', value: q.rhyme_char });
  }
  return spec;
}

export const MATCH_SPEC_BUILDERS: Partial<Record<QueryKind, MatchSpecBuilder>> = {
  [QueryKind.EQUALS]: specEquals,
  [QueryKind.PREFIX_WILDCARD_EQUALS]: specPrefixWildcardEquals,
  [QueryKind.PARTIAL_RHYME_MASK]: specPartialRhymeMask,
  [QueryKind.PARTIAL_INITIAL_MASK]: specPartialInitialMask,
  [QueryKind.SERIAL_PHONEME]: specSerialPhoneme,
  [QueryKind.PLUS_ANCHOR]: specPlusAnchor,
  [QueryKind.LITERAL_REF]: specLiteralRef,
  [QueryKind.WILDCARD_CODE_ANCHOR]: specWildcardCodeAnchor,
  [QueryKind.CODE_REF_MIDDLE_RHYME]: specCodeRefMiddleRhyme,
  [QueryKind.RHYME_ANCHOR]: specRhymeAnchor,
  [QueryKind.TRIPLE_RHYME_ANCHOR]: specTripleRhymeAnchor,
  [QueryKind.JYUTPING_ANCHOR]: specJyutpingAnchor,
  [QueryKind.HYBRID_CODE]: specHybridCode,
  [QueryKind.MASK]: specMask,
  [QueryKind.COMPOUND_SYN]: specCompoundSyn,
  [QueryKind.COMPOUND_DOUBLED_SYLLABLE]: specCompoundDoubledSyllable,
  [QueryKind.COMPOUND_ANT]: specCompoundAnt,
};

/** Port of build_match_spec_for_parsed */
export function buildMatchSpecForParsed(parsed: ParsedQuery): MatchSpec | null {
  const builder = MATCH_SPEC_BUILDERS[parsed.kind];
  if (!builder) {
    return null;
  }
  return builder(parsed);
}

/** Alias — port of normalize_to_match_spec */
export function normalizeToMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  return buildMatchSpecForParsed(parsed);
}

function anchorSlots(spec: MatchSpec): SlotConstraint[] {
  return (spec.slots ?? []).filter((s) => s.kind.endsWith('_anchor'));
}

function jyutpingSlotKinds(spec: MatchSpec): Set<string> {
  return new Set((spec.slots ?? []).map((s) => s.kind));
}

/** ponytail: parity with tests/smoke/test_query_registry.MATCH_SPEC_REPRESENTATIVE_CASES */
export function validateRepresentativeMatchSpec(
  q: string,
  spec: MatchSpec | null,
  expected: Record<string, unknown>,
): void {
  if (!spec) {
    throw new Error(`match-spec registry: no spec for ${q}`);
  }
  if (typeof expected.width === 'number' && spec.width !== expected.width) {
    throw new Error(`match-spec registry: ${q} width ${spec.width} != ${expected.width}`);
  }
  if ('ref_literal' in expected) {
    const span = getEqualsSpan(spec);
    if (!span || span.ref_literal !== expected.ref_literal) {
      throw new Error(`match-spec registry: ${q} ref_literal`);
    }
  }
  if (expected.whole_word) {
    const span = getEqualsSpan(spec);
    if (!span?.whole_word) {
      throw new Error(`match-spec registry: ${q} whole_word`);
    }
  }
  if (expected.prefix_wildcard) {
    if (!spec.extra?.prefix_wildcard_equals) {
      throw new Error(`match-spec registry: ${q} prefix_wildcard`);
    }
  }
  if ('code_prefix' in expected && spec.code_prefix !== expected.code_prefix) {
    throw new Error(`match-spec registry: ${q} code_prefix`);
  }
  if ('mask' in expected && spec.mask !== expected.mask) {
    throw new Error(`match-spec registry: ${q} mask`);
  }
  if ('compound_kind' in expected && spec.compound_kind !== expected.compound_kind) {
    throw new Error(`match-spec registry: ${q} compound_kind`);
  }
  if ('hybrid_ref' in expected && spec.hybrid_ref_chars !== expected.hybrid_ref) {
    throw new Error(`match-spec registry: ${q} hybrid_ref`);
  }
  if (expected.literal_priority && !spec.literal_priority) {
    throw new Error(`match-spec registry: ${q} literal_priority`);
  }
  if ('anchor' in expected) {
    const anchors = anchorSlots(spec);
    if (!anchors.some((s) => s.value === expected.anchor)) {
      throw new Error(`match-spec registry: ${q} anchor`);
    }
  }
  if ('anchor_count' in expected) {
    if (anchorSlots(spec).length !== expected.anchor_count) {
      throw new Error(`match-spec registry: ${q} anchor_count`);
    }
  }
  if (expected.jyutping_slot) {
    const kinds = jyutpingSlotKinds(spec);
    if (!kinds.has('rhyme_letters') && !kinds.has('syllable_letters') && !kinds.has('initial_letters')) {
      if (!spec.extra?.dual_phoneme) {
        throw new Error(`match-spec registry: ${q} jyutping_slot`);
      }
    }
  }
  if (expected.dual_phoneme && !spec.extra?.dual_phoneme) {
    throw new Error(`match-spec registry: ${q} dual_phoneme`);
  }
  if (expected.partial_rhyme_mask && !spec.extra?.partial_rhyme_mask) {
    throw new Error(`match-spec registry: ${q} partial_rhyme_mask`);
  }
  if (expected.partial_initial_mask && !spec.extra?.partial_initial_mask) {
    throw new Error(`match-spec registry: ${q} partial_initial_mask`);
  }
}
