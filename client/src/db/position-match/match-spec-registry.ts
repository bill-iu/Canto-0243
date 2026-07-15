/**
 * QueryKind → MatchSpec builders — port of app/services/query_match_spec_registry.py (MF-2)
 */
import { appendCodeDigitSlots, codeDigitStringFromSpec } from './filters/f1-slot-code.ts';
import { parseMaskQuery } from './mask-grammar.ts';
import {
  createMatchSpec,
  getEqualsSpan,
  type AnchorKind,
  type ConstraintKind,
  type MatchSpec,
  type SlotConstraint,
} from './spec.ts';
import { QueryKind } from '../query-kind.ts';
import { toMatchSpec as equalsToMatchSpec } from '../query/grammar/equals.ts';
import { toMatchSpec as serialToMatchSpec } from '../query/grammar/serial.ts';
import { toMatchSpec as rhymeToMatchSpec } from '../query/grammar/rhyme.ts';
import { toMatchSpec as plusToMatchSpec } from '../query/grammar/plus.ts';
import { toMatchSpec as relationToMatchSpec } from '../query/grammar/relation.ts';
import { toMatchSpec as pingZeToMatchSpec } from '../ping-zak.ts';
import type {
  JyutpingAnchorQuery,
  MaskQuery,
  ParsedQuery,
  WildcardCodeAnchorQuery,
} from '../query-types.ts';

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
  const spec = createMatchSpec(parsed.width);
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
    const spec = createMatchSpec(parsed.width);
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
  return equalsToMatchSpec(parsed);
}

function specSerial(parsed: ParsedQuery): MatchSpec | null {
  return serialToMatchSpec(parsed);
}

function specRhyme(parsed: ParsedQuery): MatchSpec | null {
  return rhymeToMatchSpec(parsed);
}

function specPlus(parsed: ParsedQuery): MatchSpec | null {
  return plusToMatchSpec(parsed);
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

function specJyutpingAnchor(parsed: ParsedQuery): MatchSpec | null {
  const q = parsed as JyutpingAnchorQuery;
  if (q.dual_phoneme) {
    const [initial, final] = buildJyutpingDualMatchSpecs(q);
    const carrier = createMatchSpec(q.width);
    applyJyutpingAnchorCodeSlots(carrier, q);
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

function specPingZeSerial(parsed: ParsedQuery): MatchSpec | null {
  return pingZeToMatchSpec(parsed, buildMatchSpecForParsed);
}

function specRelation(parsed: ParsedQuery): MatchSpec | null {
  return relationToMatchSpec(parsed);
}

export const MATCH_SPEC_BUILDERS: Partial<Record<QueryKind, MatchSpecBuilder>> = {
  [QueryKind.EQUALS]: specEquals,
  [QueryKind.PREFIX_WILDCARD_EQUALS]: specSerial,
  [QueryKind.PARTIAL_RHYME_MASK]: specRhyme,
  [QueryKind.PARTIAL_INITIAL_MASK]: specRhyme,
  [QueryKind.SERIAL_PHONEME]: specSerial,
  [QueryKind.PLUS_ANCHOR]: specPlus,
  [QueryKind.LITERAL_REF]: specPlus,
  [QueryKind.WILDCARD_CODE_ANCHOR]: specWildcardCodeAnchor,
  [QueryKind.CODE_REF_MIDDLE_RHYME]: specRhyme,
  [QueryKind.RHYME_ANCHOR]: specRhyme,
  [QueryKind.TRIPLE_RHYME_ANCHOR]: specRhyme,
  [QueryKind.JYUTPING_ANCHOR]: specJyutpingAnchor,
  [QueryKind.MASK]: specMask,
  [QueryKind.PING_ZE_SERIAL]: specPingZeSerial,
  [QueryKind.COMPOUND_SYN]: specRelation,
  [QueryKind.COMPOUND_CONNECT_SYN]: specRelation,
  [QueryKind.COMPOUND_DOUBLED_SYLLABLE]: specRelation,
  [QueryKind.COMPOUND_ANT]: specRelation,
  [QueryKind.COMPOUND_CONNECT_ANT]: specRelation,
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
  if ('code_prefix' in expected) {
    const got = codeDigitStringFromSpec(spec);
    if (got !== expected.code_prefix) {
      throw new Error(`match-spec registry: ${q} code_prefix ${got} != ${expected.code_prefix}`);
    }
  }
  if ('mask' in expected && spec.mask !== expected.mask) {
    throw new Error(`match-spec registry: ${q} mask`);
  }
  if ('compound_kind' in expected && spec.compound_kind !== expected.compound_kind) {
    throw new Error(`match-spec registry: ${q} compound_kind`);
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
